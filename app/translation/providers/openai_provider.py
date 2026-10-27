import logging
from typing import Optional
from app.translation.providers.base import BaseTranslator
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAITranslator(BaseTranslator):
    def __init__(self):
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    def _get_client(self):
        if not self._client:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                raise RuntimeError("openai package not installed")
        return self._client

    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        if not self.available:
            return None
        try:
            client = self._get_client()
            prompt = (
                f"Translate the following text from {source_lang} to Spanish (es). "
                f"Preserve names, figures, dates, titles, institutions, and technical terms. "
                f"Return only the translation, no explanation.\n\n{text}"
            )
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("OpenAI translation failed: %s", e)
            return None
