"""NexusAI Talent OS — Prosody / speech-emotion / confidence scoring.

Two paths:
  (a) PROSODY_MODEL == "wav2vec2" AND librosa+torch+transformers importable
      → acoustic feature extraction (pitch/energy/tempo) mapped to emotion.
  (b) heuristic text path (always available, never crashes).

All heavy deps are imported lazily inside functions inside try/except.
"""
from __future__ import annotations
import math
import re
from app.core.config import settings

_FILLERS = ("um", "uh", "er", "ah", "like", "you know", "i think",
            "maybe", "not sure", "sort of", "kind of", "i guess", "i mean")
_HEDGES = ("maybe", "perhaps", "possibly", "i think", "i guess", "not sure",
           "probably", "might", "could be", "i suppose", "sort of", "kind of")
_POSITIVE = ("excited", "love", "great", "confident", "passionate", "enjoy",
             "definitely", "absolutely", "proud", "thrilled", "happy")
_NEGATIVE = ("worried", "nervous", "afraid", "difficult", "struggle", "hard",
             "anxious", "unsure", "confused", "stressed")

_WORD_RE = re.compile(r"[a-zA-Z']+")
_SENT_RE = re.compile(r"[.!?]+")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def text_confidence(transcript: str, duration_s: float | None) -> dict:
    """Pure-text heuristic confidence/emotion estimator."""
    tokens = _tokens(transcript)
    wc = len(tokens)
    text_l = (transcript or "").lower()

    # speech rate
    if duration_s and duration_s > 0 and wc:
        wpm = wc / (duration_s / 60.0)
    else:
        wpm = 0.0

    # filler / hedging ratios (count phrase occurrences too)
    filler_hits = sum(text_l.count(f) for f in _FILLERS)
    hedge_hits = sum(text_l.count(h) for h in _HEDGES)
    filler_ratio = _clamp(filler_hits / wc) if wc else 0.0
    hedge_ratio = _clamp(hedge_hits / wc) if wc else 0.0

    # sentence completeness
    sentences = [s for s in _SENT_RE.split(transcript or "") if s.strip()]
    completeness = _clamp(len(sentences) / max(1, wc / 12.0)) if wc else 0.0
    ends_clean = 1.0 if (transcript or "").strip().endswith((".", "!", "?")) else 0.5

    pos = sum(text_l.count(w) for w in _POSITIVE)
    neg = sum(text_l.count(w) for w in _NEGATIVE)

    # confidence: rewarded by length & completeness, penalized by fillers/hedging
    length_factor = _clamp(wc / 60.0)
    confidence = _clamp(
        0.5
        + 0.25 * length_factor
        + 0.15 * completeness * ends_clean
        - 0.6 * filler_ratio
        - 0.4 * hedge_ratio
        + 0.05 * _clamp(pos / 3.0)
        - 0.05 * _clamp(neg / 3.0)
    )

    # arousal: speech rate + positive/negative intensity
    rate_norm = _clamp((wpm - 90.0) / 100.0) if wpm else 0.4
    arousal = _clamp(0.35 + 0.4 * rate_norm + 0.1 * _clamp((pos + neg) / 4.0))
    # valence: positive vs negative lexicon
    valence = _clamp(0.5 + 0.12 * pos - 0.12 * neg)

    emotion = _map_emotion(confidence, arousal, valence, filler_ratio, hedge_ratio)

    signals: list[str] = []
    if filler_ratio > 0.06:
        signals.append(f"high_filler_ratio:{filler_ratio:.2f}")
    if hedge_ratio > 0.05:
        signals.append(f"hedging:{hedge_ratio:.2f}")
    if wpm and wpm < 90:
        signals.append("slow_speech")
    if wpm and wpm > 180:
        signals.append("fast_speech")
    if wc < 15:
        signals.append("short_answer")
    if ends_clean < 1.0:
        signals.append("incomplete_ending")

    return {
        "emotion": emotion,
        "confidence": round(confidence, 3),
        "arousal": round(arousal, 3),
        "valence": round(valence, 3),
        "speech_rate_wpm": round(wpm, 1),
        "pause_ratio": 0.0,
        "pitch_variability": 0.0,
        "signals": signals,
        "method": "heuristic",
        "word_count": wc,
    }


def _map_emotion(confidence: float, arousal: float, valence: float,
                 filler_ratio: float, hedge_ratio: float) -> str:
    if filler_ratio > 0.1 or hedge_ratio > 0.1 or confidence < 0.35:
        return "hesitant" if hedge_ratio >= filler_ratio else "nervous"
    if confidence < 0.5:
        return "nervous"
    if valence > 0.6 and arousal > 0.6:
        return "enthusiastic"
    if confidence >= 0.65:
        return "confident"
    return "calm"


def _analyze_wav2vec2(audio_bytes: bytes, transcript: str,
                      duration_s: float | None) -> dict | None:
    """Acoustic path. Returns None if deps unavailable so caller falls back."""
    try:
        import io
        import numpy as np  # noqa: F401
        import librosa
    except ImportError:
        return None
    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        if y is None or len(y) == 0:
            return None
        dur = duration_s or (len(y) / sr)

        # pitch via pyin
        try:
            f0, voiced, _ = librosa.pyin(
                y, fmin=float(librosa.note_to_hz("C2")),
                fmax=float(librosa.note_to_hz("C7")), sr=sr)
            import numpy as np
            f0v = f0[~np.isnan(f0)] if f0 is not None else np.array([])
            pitch_var = float(np.std(f0v)) if f0v.size else 0.0
            pitch_mean = float(np.mean(f0v)) if f0v.size else 0.0
        except Exception:
            pitch_var, pitch_mean = 0.0, 0.0

        import numpy as np
        rms = librosa.feature.rms(y=y)[0]
        energy = float(np.mean(rms)) if rms.size else 0.0
        try:
            tempo = float(librosa.beat.tempo(y=y, sr=sr)[0])
        except Exception:
            tempo = 0.0

        # pause ratio from low-energy frames
        thr = energy * 0.3
        pause_ratio = float(np.mean(rms < thr)) if rms.size else 0.0

        # normalize features
        pitch_var_n = _clamp(pitch_var / 80.0)
        energy_n = _clamp(energy / 0.1)

        confidence = _clamp(0.4 + 0.4 * energy_n + 0.2 * (1 - pause_ratio)
                            - 0.2 * abs(pitch_var_n - 0.5))
        arousal = _clamp(0.3 + 0.4 * energy_n + 0.3 * pitch_var_n)
        valence = _clamp(0.5 + 0.2 * (energy_n - pause_ratio))

        # blend with text heuristic for speech rate / fillers
        txt = text_confidence(transcript, dur)
        confidence = round(_clamp(0.6 * confidence + 0.4 * txt["confidence"]), 3)
        emotion = _map_emotion(confidence, arousal, valence, 0.0, 0.0)

        signals = list(txt["signals"])
        if pause_ratio > 0.4:
            signals.append("long_pauses")
        if pitch_var < 10:
            signals.append("monotone")

        return {
            "emotion": emotion,
            "confidence": confidence,
            "arousal": round(arousal, 3),
            "valence": round(valence, 3),
            "speech_rate_wpm": txt["speech_rate_wpm"] or round(tempo, 1),
            "pause_ratio": round(pause_ratio, 3),
            "pitch_variability": round(pitch_var, 2),
            "pitch_mean_hz": round(pitch_mean, 1),
            "energy": round(energy, 4),
            "signals": signals,
            "method": "wav2vec2",
            "word_count": txt["word_count"],
        }
    except Exception:
        return None


async def analyze_prosody(audio_bytes: bytes | None, transcript: str,
                          duration_s: float | None = None) -> dict:
    """Main entrypoint. Acoustic path when configured + audio + deps; else text."""
    if (audio_bytes and settings.PROSODY_MODEL == "wav2vec2"):
        result = _analyze_wav2vec2(audio_bytes, transcript or "", duration_s)
        if result is not None:
            return result
    return text_confidence(transcript or "", duration_s)
