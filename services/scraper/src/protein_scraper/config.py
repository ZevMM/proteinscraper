"""Runtime configuration, loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Look for .env at the repo root first, then the service dir. Real env vars
    # (e.g. in CI) always win over .env files.
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql://protein:protein@localhost:5432/protein"
    anthropic_api_key: str = ""
    scraper_user_agent: str = "ProteinScraperBot/0.1 (+https://example.com)"
    scraper_requests_per_second: float = 1.0
    scraper_cache_dir: str = ".cache"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
