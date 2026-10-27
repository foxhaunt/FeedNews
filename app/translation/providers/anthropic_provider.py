import logging
from typing import Optional
from app.translation.providers.base import BaseTranslator
from app.config import settings

logger = logging.getLogger(__name__)


class AnthropicTranslator(BaseTranslator):
    def __init__(self):
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def _get_client(self):
        if not self._client:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            except ImportError:
                raise RuntimeError("anthropic package not installed")
        return self._client

    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        if not self.available:
            return None
        try:
            client = self._get_client()
            prompt = (
                f"Translate the following text from {source_lang} to Spanish. "
                f"Preserve names, figures, dates, titles, institutions, and technical terms. "
                f"Return only the translation.\n\n{text}"
            )
            message = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            logger.error("Anthropic translation failed: %s", e)
            return None
