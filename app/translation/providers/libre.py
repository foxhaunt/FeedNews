import logging
from typing import Optional
import aiohttp
from app.translation.providers.base import BaseTranslator
from app.config import settings

logger = logging.getLogger(__name__)

# Public LibreTranslate instances (fallback list)
PUBLIC_INSTANCES = [
    "https://libretranslate.com",
    "https://translate.argosopentech.com",
    "https://translate.terraprint.co",
]


class LibreTranslator(BaseTranslator):
    def __init__(self):
        self._base_url = settings.LIBRETRANSLATE_URL
        self._api_key = settings.LIBRETRANSLATE_API_KEY

    @property
    def name(self) -> str:
        return "libretranslate"

    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        if not text or not text.strip():
            return None
        if source_lang == target_lang:
            return text

        # Try configured instance first, then public fallbacks
        instances = [self._base_url] + [u for u in PUBLIC_INSTANCES if u != self._base_url]

        for base_url in instances:
            try:
                result = await self._call(base_url, text, source_lang, target_lang)
                if result:
                    return result
            except Exception as e:
                logger.debug("LibreTranslate %s failed: %s", base_url, e)

        return None

    async def _call(self, base_url: str, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if self._api_key:
            payload["api_key"] = self._api_key

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{base_url}/translate",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("translatedText")
