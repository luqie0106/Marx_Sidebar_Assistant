"""
LLM (DeepSeek) + TTS (edge-tts) service layer.
Returns a unified dict: { "reply": str, "audio_base64": str }
"""

import base64
import os
import re
import tempfile
from pathlib import Path

import edge_tts
from openai import AsyncOpenAI

try:
    from ..prompts import MARX_SYSTEM_PROMPT          # when run via FastAPI (backend/ package)
except ImportError:
    from app.prompts import MARX_SYSTEM_PROMPT        # when run via test_cli.py (backend/ on sys.path)

# ── DeepSeek client ───────────────────────────────────────────────────────────
_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "sk-placeholder"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
TTS_VOICE  = os.getenv("TTS_VOICE",  "zh-CN-YunxiNeural")   # male, suits Marx


# ── LLM ──────────────────────────────────────────────────────────────────────
async def llm_reply(user_text: str) -> str:
    """Send user_text to DeepSeek with Marx system prompt, return reply string."""
    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": MARX_SYSTEM_PROMPT},
            {"role": "user",   "content": user_text},
        ],
        max_tokens=400,
        temperature=0.85,
    )
    return response.choices[0].message.content.strip()


# ── TTS helpers ───────────────────────────────────────────────────────────────
_BRACKET_RE = re.compile(
    r'[\(\uff08][^\)\uff09]{0,30}[\)\uff09]'   # (text) or （text）, max 30 chars
    r'|[\[\u3010][^\]\u3011]{0,30}[\]\u3011]'   # [text] or 【text】
    r'|\u300a[^》]{0,30}\u300b'                # 《text》 (book titles – skip if brief)
)


def _strip_stage_directions(text: str) -> str:
    """Remove short parenthetical / bracketed stage directions from TTS input.

    Examples stripped:
      （冷笑） → ""
      (laughs) → ""
      [停顿] → ""
    Longer bracketed content (> 30 chars) is kept to avoid removing meaningful text.
    Multiple adjacent spaces are collapsed after removal.
    """
    cleaned = _BRACKET_RE.sub('', text)
    # Collapse extra whitespace left behind
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned).strip()
    return cleaned


# ── TTS ───────────────────────────────────────────────────────────────────────
async def tts_synthesize(text: str) -> bytes:
    """Synthesize text to MP3 bytes via edge-tts.
    Strips parenthetical stage directions (e.g. （冷笑）, (laughs)) before synthesis.
    """
    clean = _strip_stage_directions(text)
    if not clean.strip():
        clean = text   # fallback: use original if stripping removed everything

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    communicate = edge_tts.Communicate(clean, TTS_VOICE)
    await communicate.save(tmp_path)

    audio_bytes = Path(tmp_path).read_bytes()
    Path(tmp_path).unlink(missing_ok=True)
    return audio_bytes


# ── Unified pipeline ──────────────────────────────────────────────────────────
async def chat_response(user_text: str) -> dict:
    """
    Full pipeline: text → LLM → TTS → base64.
    Returns {"reply": str, "audio_base64": str}.
    """
    reply      = await llm_reply(user_text)
    audio_bytes = await tts_synthesize(reply)
    audio_b64   = base64.b64encode(audio_bytes).decode("utf-8")
    return {"reply": reply, "audio_base64": audio_b64}
