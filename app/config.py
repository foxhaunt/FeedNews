from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Feed News"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./feed_news.db"
    DATABASE_URL_SYNC: str = "sqlite:///./feed_news.db"

    # Scheduler
    INGESTION_INTERVAL_MINUTES: int = 15
    PROCESSING_INTERVAL_MINUTES: int = 5

    # Translation
    # Providers: mymemory (free, no key needed), libre, openai, anthropic, none
    # mymemory = MyMemory via deep-translator; anonymous limit: 10 000 words/day
    #   → set MYMEMORY_EMAIL=tu@email.com to raise limit to 50 000 words/day
    # libre    = LibreTranslate; set LIBRETRANSLATE_URL + LIBRETRANSLATE_API_KEY
    # openai   = OpenAI GPT; requires OPENAI_API_KEY (paid)
    # anthropic= Anthropic Claude; requires ANTHROPIC_API_KEY (paid)
    TRANSLATION_PROVIDER: str = "mymemory"
    MYMEMORY_EMAIL: str = ""          # optional; raises daily limit
    LIBRETRANSLATE_URL: str = "https://libretranslate.com"
    LIBRETRANSLATE_API_KEY: str = ""

    # LLM (optional, for summaries)
    LLM_PROVIDER: str = "none"  # none, openai, anthropic
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"

    # Limits
    MAX_ARTICLES_PER_SOURCE: int = 50
    MAX_CONTENT_LENGTH_KB: int = 512
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_CONCURRENT_FETCHES: int = 10

    # Admin
    ADMIN_TOKEN: str = "admin-token-change-me"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
