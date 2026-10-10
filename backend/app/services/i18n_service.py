"""NexusAI Talent OS — i18n / multi-language support.

Static bundles for core UI/interview strings (en/es/fr/hi; others fall back to
en) plus an LLM-backed dynamic translator for arbitrary text. MVP: no caching.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# locale -> key -> string. en is the canonical/fallback bundle.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Welcome",
        "interview_intro": "Welcome to your interview. Take your time and answer naturally.",
        "question_prefix": "Question",
        "next_question": "Next question",
        "thank_you": "Thank you for your time.",
        "schedule_title": "Schedule your interview",
        "apply_now": "Apply now",
        "submit": "Submit",
        "start": "Start",
        "finish": "Finish",
        "loading": "Loading...",
        "error_generic": "Something went wrong. Please try again.",
        "your_answer": "Your answer",
        "recording": "Recording",
        "paused": "Paused",
        "candidate": "Candidate",
        "job": "Job",
        "interview_completed": "Your interview is complete.",
        "good_luck": "Good luck!",
        "please_wait": "Please wait...",
        "consent_notice": "This interview may be recorded for evaluation purposes.",
    },
    "es": {
        "welcome": "Bienvenido",
        "interview_intro": "Bienvenido a su entrevista. Tómese su tiempo y responda con naturalidad.",
        "question_prefix": "Pregunta",
        "next_question": "Siguiente pregunta",
        "thank_you": "Gracias por su tiempo.",
        "schedule_title": "Programe su entrevista",
        "apply_now": "Postularse ahora",
        "submit": "Enviar",
        "start": "Comenzar",
        "finish": "Finalizar",
        "loading": "Cargando...",
        "error_generic": "Algo salió mal. Inténtelo de nuevo.",
        "your_answer": "Su respuesta",
        "recording": "Grabando",
        "paused": "Pausado",
        "candidate": "Candidato",
        "job": "Puesto",
        "interview_completed": "Su entrevista ha finalizado.",
        "good_luck": "¡Buena suerte!",
        "please_wait": "Por favor espere...",
        "consent_notice": "Esta entrevista puede ser grabada con fines de evaluación.",
    },
    "fr": {
        "welcome": "Bienvenue",
        "interview_intro": "Bienvenue à votre entretien. Prenez votre temps et répondez naturellement.",
        "question_prefix": "Question",
        "next_question": "Question suivante",
        "thank_you": "Merci de votre temps.",
        "schedule_title": "Planifiez votre entretien",
        "apply_now": "Postuler maintenant",
        "submit": "Envoyer",
        "start": "Commencer",
        "finish": "Terminer",
        "loading": "Chargement...",
        "error_generic": "Une erreur s'est produite. Veuillez réessayer.",
        "your_answer": "Votre réponse",
        "recording": "Enregistrement",
        "paused": "En pause",
        "candidate": "Candidat",
        "job": "Poste",
        "interview_completed": "Votre entretien est terminé.",
        "good_luck": "Bonne chance !",
        "please_wait": "Veuillez patienter...",
        "consent_notice": "Cet entretien peut être enregistré à des fins d'évaluation.",
    },
    "hi": {
        "welcome": "स्वागत है",
        "interview_intro": "आपके साक्षात्कार में आपका स्वागत है। अपना समय लें और स्वाभाविक रूप से उत्तर दें।",
        "question_prefix": "प्रश्न",
        "next_question": "अगला प्रश्न",
        "thank_you": "आपके समय के लिए धन्यवाद।",
        "schedule_title": "अपना साक्षात्कार निर्धारित करें",
        "apply_now": "अभी आवेदन करें",
        "submit": "जमा करें",
        "start": "शुरू करें",
        "finish": "समाप्त करें",
        "loading": "लोड हो रहा है...",
        "error_generic": "कुछ गलत हो गया। कृपया पुनः प्रयास करें।",
        "your_answer": "आपका उत्तर",
        "recording": "रिकॉर्डिंग",
        "paused": "रुका हुआ",
        "candidate": "उम्मीदवार",
        "job": "नौकरी",
        "interview_completed": "आपका साक्षात्कार पूर्ण हो गया है।",
        "good_luck": "शुभकामनाएँ!",
        "please_wait": "कृपया प्रतीक्षा करें...",
        "consent_notice": "मूल्यांकन उद्देश्यों के लिए इस साक्षात्कार को रिकॉर्ड किया जा सकता है।",
    },
}

_FALLBACK = "en"


def _resolve(locale: Optional[str]) -> str:
    loc = (locale or settings.DEFAULT_LOCALE or _FALLBACK).lower()
    return loc if loc in TRANSLATIONS else _FALLBACK


def t(key: str, locale: Optional[str] = None) -> str:
    """Translate a known key; fall back to en, then to the key itself."""
    loc = _resolve(locale)
    bundle = TRANSLATIONS.get(loc, {})
    if key in bundle:
        return bundle[key]
    return TRANSLATIONS[_FALLBACK].get(key, key)


def get_bundle(locale: Optional[str]) -> dict:
    """Full key->string bundle for a locale (en merged with the locale)."""
    loc = _resolve(locale)
    merged = dict(TRANSLATIONS[_FALLBACK])
    merged.update(TRANSLATIONS.get(loc, {}))
    return {"locale": loc, "default": settings.DEFAULT_LOCALE, "strings": merged}


def supported() -> list:
    """Configured supported locales (superset of the static bundles)."""
    return list(settings.SUPPORTED_LOCALES)


async def translate_text(text: str, target_locale: str) -> dict:
    """LLM-translate arbitrary text to target_locale. No caching (MVP)."""
    target = (target_locale or settings.DEFAULT_LOCALE or _FALLBACK).lower()
    if not text:
        return {"ok": True, "text": text, "locale": target}
    try:
        from app.services.llm_service import LLMService

        llm = LLMService()
        prompt = (
            f"Translate the following text to the language with locale code "
            f"'{target}'. Preserve meaning, tone and any formatting. "
            f"Return ONLY the translated text, no preamble.\n\n{text}"
        )
        content, _, _ = await llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )
        translated = (content or "").strip()
        if not translated:
            return {"ok": False, "text": text, "locale": target}
        return {"ok": True, "text": translated, "locale": target}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"translate_text failed (target={target}): {exc}")
        return {"ok": False, "text": text, "locale": target}
