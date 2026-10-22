from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "SwiftParcel"
    ENV: str = "local"
    DEBUG: bool = True

    DATABASE_URL: str = Field(..., description="Async SQLAlchemy DB URL")

    JWT_SECRET_KEY: str = Field(..., min_length=16)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    SSLC_STORE_ID: str = ""
    SSLC_STORE_PASSWORD: str = ""
    SSLC_IS_SANDBOX: bool = True
    BACKEND_URL: str = "http://localhost:8000" # Frontend theke asole ei url ta change hobe

    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()