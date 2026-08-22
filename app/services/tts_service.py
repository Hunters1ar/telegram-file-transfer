"""
tts_service.py — Text-to-Speech via Deepgram Flux TTS on OpenRouter.

Responsibilities
----------------
* text -> raw MP3 bytes   (no Telegram knowledge, no aiogram imports)
* Strips emojis/stickers before speaking — e.g. "Hello! 😄" is sent as "Hello!"
* Key rotation: tries each key in the shared OR pool on 429 / 5xx
* Enforces MAX_TTS_CHARS to prevent runaway requests
* Exposes a single clean TTSError for callers to handle
"""

from __future__ import annotations

import logging
import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Emoji / non-speakable character stripper ──────────────────────────────────

_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # misc symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
    "\U00002600-\U000027BF"  # misc symbols (☀️ ✨ etc.)
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U000024C2-\U0001F251"  # enclosed chars
    "]+",
    flags=re.UNICODE,
)


def _strip_tts_artifacts(text: str) -> str:
    """
    Remove emojis, stickers, and other non-speakable Unicode characters
    from *text* before it is sent to the TTS API.

    Example: "Hello! 😄👋" → "Hello!"
    """
    text = _EMOJI_RE.sub("", text)
    # Collapse any leftover multiple spaces created by emoji removal
    text = re.sub(r" {2,}", " ", text).strip()
    return text


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

# Vague "say" suffixes that mean "AI decides what to say" rather than a literal text
_SAY_AI_SUFFIXES: set[str] = {
    "something", "something funny", "something interesting", "something cool",
    "something nice", "something clever", "something sweet", "something random",
    "anything", "whatever", "a joke", "a story", "a poem",
    "hello", "hi", "hey", "yo",
    # Personal info — AI must look these up and speak the real values
    "my username", "my name", "my full name", "my first name", "my last name",
    "my id", "my user id", "my telegram id",
    "my language", "my affection", "my level",
}

# Vague "speak" suffixes that mean AI_TTS
_SPEAK_AI_SUFFIXES: set[str] = {
    "to me", "something", "anything", "please", "now",
    "my username", "my name", "my id",
}


def detect_tts_intent(text: str) -> TTSIntent:
    """
    Returns a TTSIntent describing what the bot should do.

    Rules (evaluated in order):
      1. /tts <body>              -> DIRECT_TTS(body)
      2. /tts alone               -> NONE  (bot handles via FSM state)
      3. <direct trigger> <body>  -> DIRECT_TTS(body)
      4. say <vague>              -> AI_TTS
      5. say <specific text>      -> DIRECT_TTS(specific text)
      6. speak <vague>            -> AI_TTS
      7. speak <specific text>    -> DIRECT_TTS(specific text)
      8. Exact conversational TTS phrase -> AI_TTS
      9. Anything else            -> NONE
    """
    stripped = text.strip()
    lower = stripped.lower()

    # -- Rule 1 & 2: /tts command ----------------------------------------------
    if lower.startswith("/tts"):
        body = stripped[4:].strip()
        if body:
            return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=body)
        return TTSIntent(kind=TTSIntentKind.NONE)   # FSM handles /tts alone

    # -- Rule 3: Direct-extract triggers ---------------------------------------
    for trigger in _DIRECT_TRIGGERS:
        if lower.startswith(trigger):
            body = stripped[len(trigger):].strip()
            if body:
                return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=body)

    # -- Rules 4 & 5: "say <text>" ---------------------------------------------
    # Must start the whole message (avoids "what did you say about X?")
    if lower.startswith("say "):
        remainder = stripped[4:].strip()
        remainder_lower = remainder.lower().rstrip("!?.")
        if remainder_lower in _SAY_AI_SUFFIXES:
            return TTSIntent(kind=TTSIntentKind.AI_TTS)
        if remainder:
            return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=remainder)

    # -- Rules 6 & 7: "speak <text>" ------------------------------------------
    if lower.startswith("speak "):
        remainder = stripped[6:].strip()
        remainder_lower = remainder.lower().rstrip("!?.")
        if remainder_lower in _SPEAK_AI_SUFFIXES:
            return TTSIntent(kind=TTSIntentKind.AI_TTS)
        if remainder:
            return TTSIntent(kind=TTSIntentKind.DIRECT_TTS, text=remainder)

    # -- Rule 8: Exact conversational TTS phrases ------------------------------
    for phrase in _AI_TTS_PHRASES:
        if (lower == phrase
                or lower.startswith(phrase + " ")
                or lower.startswith(phrase + "!")
                or lower.startswith(phrase + "?")
                or lower.startswith(phrase + ".")):
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

    async def synthesize(self, text: str, lang: str = "en") -> bytes:
        """
        Synthesize *text* and return raw MP3 bytes.
        Automatically routes to Fish Audio for non-English scripts.
        """
        if not settings.tts_enabled:
            raise TTSError("TTS is currently disabled.")

        if not _OR_KEYS:
            raise TTSError("No OpenRouter API keys configured for TTS.")

        text = text.strip()
        text = _strip_tts_artifacts(text)
        if not text:
            raise ValueError("TTS text must not be empty.")

        if len(text) > self.max_chars:
            raise ValueError(
                f"Text is too long for TTS ({len(text)} chars). "
                f"Maximum is {self.max_chars} characters."
            )

        # Detect non-English scripts (Cyrillic, Hangul, CJK, etc.)
        # Russian/Uzbek (Cyrillic), Korean (Hangul), Chinese/Japanese (CJK)
        has_cyrillic = bool(re.search(r'[\u0400-\u04FF]', text))
        has_cjk = bool(re.search(r'[\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u309F\u30A0-\u30FF]', text))
        has_hangul = bool(re.search(r'[\uAC00-\uD7AF\u1100-\u11FF]', text))

        target_model = self.model
        target_voice = self.voice

        # Route to Fish Audio if non-English language requested or non-Latin script detected
        if lang not in ("en", "") or has_cyrillic or has_cjk or has_hangul:
            target_model = "fish-audio/s2.1-pro-free:free"
            target_voice = None # Fish Audio is auto-multilingual

        payload = {
            "model": target_model,
            "input": text,
            "response_format": "mp3",
        }
        if target_voice:
            payload["voice"] = target_voice

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
                            len(text), idx + 1, target_model, target_voice,
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
