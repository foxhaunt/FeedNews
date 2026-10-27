"""MyMemory translation provider via deep-translator.

Free tier: 10 000 words/day (anonymous), 50 000 words/day with a free API key.
No credit card required.  Set MYMEMORY_API_KEY=<email> in .env to raise the limit.

deep-translator uses a synchronous requests call internally; we run it in an
executor so it doesn't block the asyncio event loop.
"""
import asyncio
import logging
from typing import Optional

from app.translation.providers.base import BaseTranslator
from app.config import settings

logger = logging.getLogger(__name__)

# Maps ISO-639-1 codes to MyMemory lang-pair codes
_LANG_MAP = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "pt": "pt-BR",
    "it": "it-IT",
    "ar": "ar-AR",
    "ru": "ru-RU",
    "zh": "zh-CN",
    "es": "es-ES",
}


def _lang(code: str) -> str:
    return _LANG_MAP.get(code, f"{code}-{code.upper()}")


class MyMemoryTranslator(BaseTranslator):
    """Wraps deep_translator.MyMemoryTranslator for async use."""

    @property
    def name(self) -> str:
        return "mymemory"

    @property
    def available(self) -> bool:
        try:
            import deep_translator  # noqa
            return True
        except ImportError:
            return False

    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        if not text or not text.strip():
            return None
        if source_lang == target_lang:
            return text
        # MyMemory max request is 500 chars; split if needed
        text = text[:500]
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._sync_translate, text, source_lang, target_lang
            )
            return result
        except Exception as e:
            logger.warning("MyMemory translation error: %s", e)
            return None

    def _sync_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        from deep_translator import MyMemoryTranslator
        src = _lang(source_lang)
        tgt = _lang(target_lang)
        email = settings.MYMEMORY_EMAIL or None
        kwargs = {"source": src, "target": tgt}
        if email:
            kwargs["email"] = email
        t = MyMemoryTranslator(**kwargs)
        result = t.translate(text)
        if not result:
            return None
        # MyMemory returns quota-exceeded messages or echoes the input
        if result.upper().startswith("INVALID") or result.strip() == text.strip():
            return None
        return result
