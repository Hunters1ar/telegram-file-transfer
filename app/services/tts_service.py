"""
tts_service.py — Text-to-Speech via Deepgram Flux TTS on OpenRouter.

Responsibilities
----------------
* text → raw MP3 bytes   (no Telegram knowledge, no aiogram imports)
* Key rotation: tries each key in the shared OR pool on 429 / 5xx
* Enforces MAX_TTS_CHARS to prevent runaway requests
* Exposes a single clean TTSError for callers to handle
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_TTS_CHARS = 4_000
TTS_API_URL = "https://openrouter.ai/api/v1/audio/speech"

# ── Shared OpenRouter key pool (same list as ai_service uses) ─────────────────
_OR_KEYS: list[str] = [
    k for k in [
        settings.openrouter_api_key,
        settings.openrouter_api_key1,
        settings.openrouter_api_key2,
        settings.openrouter_api_key3,
        settings.openrouter_api_key4,
        settings.openrouter_api_key5,
        settings.openrouter_api_key6,
    ] if k
]

if not _OR_KEYS:
    logger.warning("TTSService: no OpenRouter API keys configured — TTS will be unavailable.")


# ── Intent detector ───────────────────────────────────────────────────────────

class TTSIntentKind(Enum):
    NONE = auto()
    DIRECT_TTS = auto()   # text is provided by the user
    AI_TTS = auto()       # AI should generate the text first


@dataclass(frozen=True)
class TTSIntent:
    kind: TTSIntentKind
    text: Optional[str] = None   # only set when kind == DIRECT_TTS


# Phrases that extract verbatim text following a trigger prefix
_DIRECT_TRIGGERS: list[str] = [
    "make this into audio:",
    "make this into audio :",
    "convert this to voice:",
    "convert this to voice :",
    "read this aloud:",
    "read this aloud :",
    "read this:",
    "read this :",
    "read aloud:",
    "read aloud :",
    "speak this:",
    "speak this :",
    "tts:",
    "tts :",
]

# Full-phrase patterns that request the AI to speak (no user text supplied)
_AI_TTS_PHRASES: list[str] = [
    "say something",
    "say hello",
    "say hi",
    "say a joke",
    "say something funny",
    "say something interesting",
    "tell me a joke out loud",
    "tell me something out loud",
    "speak to me",
    "speak something",
    "give me a voice message",
    "give me a voice note",
    "voice message",
    "voice note",
    "talk to me",
    "say it out loud",
    "respond with audio",
    "respond with voice",
    "answer with voice",
    "answer in audio",
    "send me a voice",
    "send a voice",
]


def detect_tts_intent(text: str) -> TTSIntent:
    """
    Returns a TTSIntent describing what the bot should do.

    Rules (evaluated in order):
      1. /tts <body>              → DIRECT_TTS(body)
      2. <direct trigger> <body>  → DIRECT_TTS(body)
      3. Exact conversational TTS phrase → AI_TTS
      4. Anything else            → NONE
    """
    stripped = text.strip()
    lower = stripped.lower()

    # ── Rule 1: /tts command ──────────────────────────────────────────────────
    if lower.startswith("/tts"):
        body = stripped[4:].strip()
        if body:
            return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=body)
        # /tts with no text → treat as AI_TTS (ask AI to say something)
        return TTSIntent(kind=TTSIntentKind.AI_TTS)

    # ── Rule 2: Direct-extract triggers ──────────────────────────────────────
    for trigger in _DIRECT_TRIGGERS:
        if lower.startswith(trigger):
            body = stripped[len(trigger):].strip()
            if body:
                return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=body)

    # ── Rule 3: Conversational TTS phrases (full-string match only) ───────────
    # We compare against the full lowercased message to avoid false positives
    # like "what did you say about the upload system?"
    for phrase in _AI_TTS_PHRASES:
        if lower == phrase or lower.startswith(phrase + " ") or lower.startswith(phrase + "!") or lower.startswith(phrase + "?") or lower.startswith(phrase + "."):
            return TTSIntent(kind=TTSIntentKind.AI_TTS)

    return TTSIntent(kind=TTSIntentKind.NONE)


# ── Error ─────────────────────────────────────────────────────────────────────

class TTSError(Exception):
    """Raised when TTS synthesis fails after exhausting all keys."""
    pass


# ── Service ───────────────────────────────────────────────────────────────────

class TTSService:
    """
    Converts text to MP3 bytes via Deepgram Flux TTS on OpenRouter.

    Usage:
        audio_bytes = await tts_service.synthesize("Hello world!")
    """

    def __init__(
        self,
        model: str | None = None,
        voice: str | None = None,
        max_chars: int = MAX_TTS_CHARS,
    ) -> None:
        self.model = model or settings.tts_model
        self.voice = voice or settings.tts_voice
        self.max_chars = max_chars

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize *text* and return raw MP3 bytes.

        Raises
        ------
        TTSError
            When TTS is disabled, no keys are available, or all keys fail.
        ValueError
            When *text* is empty or exceeds MAX_TTS_CHARS.
        """
        if not settings.tts_enabled:
            raise TTSError("TTS is currently disabled.")

        if not _OR_KEYS:
            raise TTSError("No OpenRouter API keys configured for TTS.")

        text = text.strip()
        if not text:
            raise ValueError("TTS text must not be empty.")

        if len(text) > self.max_chars:
            raise ValueError(
                f"Text is too long for TTS ({len(text)} chars). "
                f"Maximum is {self.max_chars} characters."
            )

        payload = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "mp3",
        }

        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=60.0) as client:
            for idx, api_key in enumerate(_OR_KEYS):
                try:
                    response = await client.post(
                        TTS_API_URL,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        logger.info(
                            "TTS synthesized %d chars via OR key %d (%s, %s).",
                            len(text), idx + 1, self.model, self.voice,
                        )
                        return response.content

                    # 429 / 5xx → try next key
                    last_error = TTSError(
                        f"OR key {idx + 1} returned HTTP {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    logger.warning(str(last_error))

                except httpx.RequestError as exc:
                    last_error = exc
                    logger.warning("TTS request error on OR key %d: %s", idx + 1, exc)

        raise TTSError(
            f"TTS failed: all {len(_OR_KEYS)} OpenRouter key(s) exhausted. "
            f"Last error: {last_error}"
        )


# Module-level singleton — import and use directly
tts_service = TTSService()
