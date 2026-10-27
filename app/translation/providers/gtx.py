"""
Unofficial Google Translate provider using the public gtx endpoint.

No API key required. Uses `translate.googleapis.com/translate_a/single?client=gtx`,
the same endpoint available in all browser-based translation tools.

Limitations:
- Unofficial; could change without notice
- Max ~5000 chars per request (we cap at 500 to stay safe)
- No hard daily limit, but respect 1 req/s to avoid IP bans
"""
import asyncio
import json
import logging
import urllib.parse
import urllib.request
from typing import Optional

from app.translation.providers.base import BaseTranslator

logger = logging.getLogger(__name__)

_BASE_URL = "https://translate.googleapis.com/translate_a/single"
_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _sync_translate_gtx(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    encoded = urllib.parse.quote(text)
    url = f"{_BASE_URL}?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={encoded}"
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    # Response: [[[segment, original, ...], ...], ...]
    segments = data[0]
    result = "".join(seg[0] for seg in segments if seg and seg[0])
    result = result.strip()
    if not result or result.lower() == text.lower():
        return None
    return result


class GtxTranslator(BaseTranslator):
    """Google Translate via the unofficial gtx endpoint (no API key needed)."""

    @property
    def name(self) -> str:
        return "gtx"

    @property
    def available(self) -> bool:
        return True

    async def translate(self, text: str, source_lang: str, target_lang: str = "es") -> Optional[str]:
        if not text or not text.strip():
            return None
        if source_lang == target_lang:
            return text
        text = text[:500]
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _sync_translate_gtx, text, source_lang, target_lang
            )
            return result
        except Exception as e:
            logger.warning("GTX translation error: %s", e)
            return None
