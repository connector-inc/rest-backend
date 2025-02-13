from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openapi_url: str = ""
    root_path: str = "/api"
    database_url: str = ""
    database_url_async: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
