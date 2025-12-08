"""Core configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # EVE SSO
    eve_client_id: str
    eve_client_secret: str
    eve_callback_url: str

    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["*"]

    # Discord (Optional)
    discord_webhook_url: str = ""

    # War Room
    war_data_retention_days: int = 30
    war_doctrine_min_fleet_size: int = 10
    war_heatmap_min_kills: int = 5
    war_everef_base_url: str = "https://data.everef.net/killmails"

    # Market Hunter
    hunter_min_roi: float = 15.0
    hunter_min_profit: int = 500000
    hunter_top_candidates: int = 20
    hunter_default_me: int = 10

    # ESI
    esi_base_url: str = "https://esi.evetech.net/latest"
    esi_user_agent: str = "EVE-Co-Pilot/1.2.0"
    esi_timeout: int = 30

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
