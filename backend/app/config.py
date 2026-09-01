"""Konfigurasi aplikasi, dibaca dari env / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://arena:arena@localhost:5432/arena"
    admin_username: str = "admin"
    admin_password: str = "ganti_sesuatu_yang_kuat"
    secret_key: str = "ganti_sesuatu_yang_panjang_dan_acak"

    grok_api_key: str = ""
    mistral_api_key: str = ""
    deepseek_api_key: str = ""

    grok_model: str = "grok-2-1212"
    mistral_model: str = "mistral-ocr-latest"
    deepseek_model: str = "deepseek-chat"

    crawl_days_back: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
