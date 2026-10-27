import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Map langdetect codes to our internal codes
LANG_MAP = {
    "es": "es", "en": "en", "fr": "fr", "de": "de",
    "it": "it", "pt": "pt", "ca": "ca", "eu": "eu",
    "nl": "nl", "pl": "pl", "ru": "ru", "ar": "ar",
    "zh-cn": "zh", "zh-tw": "zh", "ja": "ja", "ko": "ko",
    "uk": "uk", "tr": "tr", "sv": "sv", "no": "no", "da": "da",
}


def detect_language(text: str) -> Optional[str]:
    """Detect language of text; returns ISO 639-1 code or None."""
    if not text or len(text.strip()) < 20:
        return None
    try:
        from langdetect import detect, LangDetectException
        code = detect(text)
        return LANG_MAP.get(code, code)
    except Exception as e:
        logger.debug("Language detection failed: %s", e)
        return None
