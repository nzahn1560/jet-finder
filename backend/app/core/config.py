from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Jet Finder Platform"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///../database/jetfinder.db"
    frontend_origin: str = "http://localhost:5173"
    admin_email: str = "admin@example.com"
    admin_password: str = "Passw0rd!"
    force_password_reset: bool = True

    class Config:
        env_file = Path(__file__).resolve().parents[3] / ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()

