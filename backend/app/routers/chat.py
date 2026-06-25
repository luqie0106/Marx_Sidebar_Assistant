"""
Chat router – two endpoints, both return unified JSON:
  { "reply": str, "audio_base64": str }

  POST /api/chat_text   – plain text in, JSON out
  POST /api/chat_voice  – audio file in, JSON out (Whisper STT → LLM → TTS)
"""

import asyncio
import os
import tempfile
from pathlib import Path

import whisper
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..services import chat_response

# ── macOS SSL fix ─────────────────────────────────────────────────────────────
# Python 3.13 on macOS ships without system CA certificates in its bundle.
# Whisper downloads model weights via HTTPS, so we point it at certifi's bundle.
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass  # certifi not installed — SSL will use system defaults

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


# ── /api/tts ──────────────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: str


@router.post("/tts", response_model=TTSResponse)
async def tts_endpoint(body: TTSRequest):
    """Synthesize arbitrary text to MP3 and return as base64.
    Used by the frontend 'speak' button on each Marx reply bubble."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    from ..services import tts_synthesize
    import base64

    audio_bytes = await tts_synthesize(body.text)
    return TTSResponse(audio_base64=base64.b64encode(audio_bytes).decode("utf-8"))

