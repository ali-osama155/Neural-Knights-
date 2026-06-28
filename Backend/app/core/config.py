from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Neural Knights"

    # Security
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ALGORITHM: str = "HS256"          # <-- ADD THIS
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./recruitai.db"
    DEBUG: bool = True

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # OpenAI
    OPENAI_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()