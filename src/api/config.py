from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Payment API"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str

    payment_api_key: str
    webhook_secret: str
    api_key_header: str = "X-API-Key"

    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
