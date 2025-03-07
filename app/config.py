from functools import lru_cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openapi_url: str = ""
    environment: str = "development"

    database_url_async: str = ""

    redis_url: str = ""

    jwt_algorithm: str = "RS256"
    jwt_public_key: str = ""
    jwt_private_key: str = ""

    web_app_url: str = "http://localhost:3000"

    resend_api_key: str = ""
    sender_email: EmailStr = ""

    cookie_domain: str = "localhost"

    verification_email_expiry_minutes: int = 30
    session_expiry_days: int = 7

    model_config = SettingsConfigDict(
        env_file=(".env"),
        env_file_encoding="utf-8",
    )


# settings = Settings()


@lru_cache
def get_settings():
    return Settings()
