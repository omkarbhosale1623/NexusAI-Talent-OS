"""
Speech Service — STT + TTS with pre-warming, Redis caching, fallback chain.
OpenAI TTS primary → ElevenLabs fallback.
faster-whisper STT (pre-warmed at startup).
"""
import asyncio
import base64
import hashlib
import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# ── Whisper model singleton ────────────────────────────────────────────────
_whisper_model = None
_whisper_lock = asyncio.Lock()


async def prewarm_whisper():
    """Pre-load Whisper at startup — never block the first request."""
    global _whisper_model
    try:
        logger.info(f"Pre-warming Whisper ({settings.WHISPER_MODEL_SIZE})…")
        from faster_whisper import WhisperModel
        loop = asyncio.get_event_loop()
        _whisper_model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            ),
        )
        logger.info("Whisper pre-warm complete")
    except Exception as exc:
        logger.error(f"Whisper pre-warm failed: {exc}")


async def prewarm_tts_cache():
    """Pre-cache common greeting phrases at startup."""
    greetings = [
        "Hello! Welcome to your AI interview. I'll be guiding you through a series of questions today. Let's begin.",
        "Thank you for completing the interview. Your responses have been recorded and will be reviewed shortly.",
        "Could you elaborate on that? Please provide more specific details or examples.",
    ]
    for text in greetings:
        try:
            await synthesize_speech(text)
        except Exception as exc:
            logger.warning(f"TTS pre-warm failed for greeting: {exc}")


async def get_whisper_model():
    """Get the pre-warmed Whisper model, loading it if necessary."""
    global _whisper_model
    if _whisper_model is None:
        async with _whisper_lock:
            if _whisper_model is None:
                await prewarm_whisper()
    return _whisper_model


# ── STT ───────────────────────────────────────────────────────────────────

async def transcribe_audio(
    audio_bytes: bytes,
    original_filename: str = "audio.webm",
) -> Tuple[str, Optional[str], Optional[float]]:
    """
    Transcribe audio bytes using faster-whisper.
    Returns: (transcript, language, duration_seconds)
    """
    # Convert to WAV 16kHz mono via ffmpeg (whisper works best on this)
    wav_bytes = await convert_to_wav(audio_bytes, original_filename)

    if len(wav_bytes) < 300:
        logger.warning("Audio too short — likely silence/noise, skipping transcription")
        return "", None, None

    model = await get_whisper_model()
    loop = asyncio.get_event_loop()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        def _transcribe():
            segments, info = model.transcribe(
                tmp_path,
                language=settings.WHISPER_LANGUAGE if settings.WHISPER_LANGUAGE != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text, info.language, info.duration

        transcript, language, duration = await loop.run_in_executor(None, _transcribe)
        logger.info(f"STT: {len(transcript.split())} words, lang={language}, dur={duration:.1f}s")
        return transcript, language, duration

    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def convert_to_wav(audio_bytes: bytes, filename: str) -> bytes:
    """Convert any audio format to WAV 16kHz mono using ffmpeg."""
    suffix = Path(filename).suffix.lower() or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as inp:
        inp.write(audio_bytes)
        inp_path = inp.name

    out_path = inp_path + "_out.wav"

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", inp_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode != 0:
            logger.error("ffmpeg conversion failed, using raw bytes")
            return audio_bytes

        async with aiofiles.open(out_path, "rb") as f:
            return await f.read()

    finally:
        Path(inp_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)


# ── TTS ───────────────────────────────────────────────────────────────────

async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    org_id: Optional[str] = None,
) -> bytes:
    """
    Convert text to speech MP3.
    OpenAI TTS primary → ElevenLabs fallback.
    Redis-cached per (text_hash, voice).
    Returns raw MP3 bytes.
    """
    effective_voice = voice or settings.OPENAI_TTS_VOICE
    cache_key = _tts_cache_key(text, effective_voice)

    # ── Redis cache check ─────────────────────────────────────────────────
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return base64.b64decode(cached)
    except Exception as exc:
        logger.warning(f"Redis TTS cache read failed: {exc}")

    # ── Synthesize ────────────────────────────────────────────────────────
    audio_bytes = await _try_openai_tts(text, effective_voice)
    if audio_bytes is None:
        audio_bytes = await _try_elevenlabs_tts(text)
    if audio_bytes is None:
        raise RuntimeError("All TTS providers failed — cannot synthesize speech")

    # ── Store in Redis ────────────────────────────────────────────────────
    try:
        await redis_client.setex(
            cache_key,
            settings.TTS_CACHE_TTL,
            base64.b64encode(audio_bytes),
        )
    except Exception as exc:
        logger.warning(f"Redis TTS cache write failed: {exc}")

    return audio_bytes


async def synthesize_speech_b64(
    text: str,
    voice: Optional[str] = None,
    org_id: Optional[str] = None,
) -> str:
    """Returns base64-encoded MP3 (for embedding in JSON responses)."""
    audio_bytes = await synthesize_speech(text, voice, org_id)
    return base64.b64encode(audio_bytes).decode()


def _tts_cache_key(text: str, voice: str) -> str:
    digest = hashlib.md5(f"{voice}:{text}".encode()).hexdigest()
    return f"tts:{digest}"


async def _try_openai_tts(text: str, voice: str) -> Optional[bytes]:
    """OpenAI tts-1 (primary)."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.audio.speech.create(
            model=settings.OPENAI_TTS_MODEL,
            voice=voice,
            input=text,
            response_format="mp3",
        )
        return response.content
    except Exception as exc:
        logger.warning(f"OpenAI TTS failed: {exc}")
        return None


async def _try_elevenlabs_tts(text: str) -> Optional[bytes]:
    """ElevenLabs (fallback)."""
    if not settings.ELEVENLABS_API_KEY:
        return None
    try:
        import httpx
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"
        payload = {
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL_ID,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.content
    except Exception as exc:
        logger.warning(f"ElevenLabs TTS failed: {exc}")
        return None


async def precache_next_question_tts(text: str, voice: Optional[str] = None):
    """Fire-and-forget background pre-caching."""
    try:
        await synthesize_speech(text, voice)
        logger.debug(f"Pre-cached TTS for: {text[:50]}…")
    except Exception as exc:
        logger.warning(f"TTS pre-cache failed: {exc}")
