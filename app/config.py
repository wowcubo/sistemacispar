from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    google_service_account_file: str = "credentials/service_account.json"
    google_drive_root_folder_id: str = ""

    app_name: str = "CISPAR - Sistema de Rotinas SISBI"
    app_url: str = "http://localhost:8000"
    debug: bool = False

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
