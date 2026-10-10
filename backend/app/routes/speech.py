"""NexusAI Talent OS — Speech Routes (STT + TTS)"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from app.schemas.schemas import TranscribeResponse, TTSRequest, TTSResponse

router = APIRouter()

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) < 300: raise HTTPException(400, "Audio too short or empty")
    from app.services.speech_service import transcribe_audio
    transcript, language, duration = await transcribe_audio(content, file.filename or "audio.webm")
    return TranscribeResponse(transcript=transcript, language=language, duration_seconds=duration)

@router.post("/tts", response_model=TTSResponse)
async def tts(body: TTSRequest, request: Request):
    from app.services.speech_service import synthesize_speech_b64
    org_id = getattr(request.state, "org_id", None)
    audio = await synthesize_speech_b64(body.text, body.voice, org_id)
    return TTSResponse(audio=audio)

@router.post("/tts/stream")
async def tts_stream(body: TTSRequest, request: Request):
    from app.services.speech_service import synthesize_speech
    org_id = getattr(request.state, "org_id", None)
    audio_bytes = await synthesize_speech(body.text, body.voice, org_id)
    return Response(content=audio_bytes, media_type="audio/mpeg")
