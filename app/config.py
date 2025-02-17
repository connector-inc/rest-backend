from functools import lru_cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openapi_url: str = ""

    database_url: str = ""
    database_url_async: str = ""

    redis_url: str = ""

    jwt_secret_key: str = ""

    web_app_url: str = "http://localhost:3000"

    resend_api_key: str = ""
    sender_email: EmailStr = ""

    cookie_domain: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=(".env"),
        env_file_encoding="utf-8",
    )


# settings = Settings()


@lru_cache
def get_settings():
    return Settings()
