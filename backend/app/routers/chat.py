"""
Chat router – two endpoints, both return unified JSON:
  { "reply": str, "audio_base64": str }

  POST /api/chat_text   – plain text in, JSON out
  POST /api/chat_voice  – audio file in, JSON out (Whisper STT → LLM → TTS)
"""

import asyncio
import tempfile
from pathlib import Path

import whisper
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..services import chat_response

router = APIRouter(tags=["chat"])

# Whisper model is loaded lazily on first voice request (avoids blocking startup/imports)
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


# ── Shared response schema ────────────────────────────────────────────────────
class ChatResponse(BaseModel):
    reply:        str
    audio_base64: str


# ── /api/chat_text ────────────────────────────────────────────────────────────
class TextRequest(BaseModel):
    message: str


@router.post("/chat_text", response_model=ChatResponse)
async def chat_text(body: TextRequest):
    """Receive plain text; return Marx-style reply + base64-encoded MP3."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    result = await chat_response(body.message)
    return ChatResponse(**result)


# ── /api/chat_voice ───────────────────────────────────────────────────────────
class VoiceResponse(ChatResponse):
    transcript: str


@router.post("/chat_voice", response_model=VoiceResponse)
async def chat_voice(audio: UploadFile = File(...)):
    """
    Pipeline: audio upload → Whisper STT → LLM → edge-tts
    Returns JSON with transcript, reply text, and base64-encoded MP3.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Persist to temp file for Whisper (it requires a file path, not a buffer)
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: _get_whisper_model().transcribe(tmp_path, language="zh")
        )
        transcript: str = result["text"].strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    chat_result = await chat_response(transcript)
    return VoiceResponse(transcript=transcript, **chat_result)
