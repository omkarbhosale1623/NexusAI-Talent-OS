"""
NexusAI Talent OS — Resume & JD Text Extraction Utility
Extracts raw text from PDF/DOCX, parses with LLM. Results stored on
Application.parsed_resume (resume) or Job.requirements (JD) by the caller.
Redis-cached by content hash to avoid re-parsing identical files.
"""
import hashlib
import io
import json
import logging
from typing import Optional

from app.core.redis_client import redis_client
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
CACHE_TTL = 604800  # 7 days


class ResumeTextExtractor:
    """Stateless utility: bytes in -> structured dict out. No DB writes."""

    def __init__(self):
        self.llm = LLMService()

    async def extract_and_parse(self, content: bytes, filename: str) -> dict:
        file_hash = hashlib.sha256(content).hexdigest()
        cached = await self._get_cached(file_hash)
        if cached:
            return cached

        raw_text = self._extract_text(content, filename)
        parsed = await self.llm.parse_resume(raw_text) if raw_text else {}
        await self._set_cached(file_hash, parsed)
        return parsed

    def _extract_text(self, content: bytes, filename: str) -> str:
        fname = filename.lower()
        if fname.endswith(".pdf"):
            return self._extract_pdf(content)
        if fname.endswith((".docx", ".doc")):
            return self._extract_docx(content)
        return content.decode("utf-8", errors="ignore")

    def _extract_pdf(self, content: bytes) -> str:
        try:
            from pdfminer.high_level import extract_text as pdf_text
            return pdf_text(io.BytesIO(content)) or ""
        except Exception as exc:
            logger.warning(f"pdfminer failed: {exc}, trying pypdf")
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                return "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as exc2:
                logger.error(f"PDF extraction failed: {exc2}")
                return ""

    def _extract_docx(self, content: bytes) -> str:
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error(f"DOCX extraction failed: {exc}")
            return ""

    async def _get_cached(self, file_hash: str) -> Optional[dict]:
        try:
            cached = await redis_client.get(f"resume_parsed:{file_hash[:16]}")
            return json.loads(cached) if cached else None
        except Exception:
            return None

    async def _set_cached(self, file_hash: str, parsed: dict):
        try:
            await redis_client.setex(f"resume_parsed:{file_hash[:16]}", CACHE_TTL, json.dumps(parsed))
        except Exception:
            pass


class JDTextParser:
    """Parses raw job description text into structured requirements."""

    def __init__(self):
        self.llm = LLMService()

    async def parse(self, raw_text: str) -> dict:
        text_hash = hashlib.sha256(raw_text.encode()).hexdigest()
        cache_key = f"jd_parsed:{text_hash[:16]}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        parsed = await self.llm.parse_jd(raw_text)
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(parsed))
        except Exception:
            pass
        return parsed
