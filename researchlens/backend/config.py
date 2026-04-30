from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Database – defaults to SQLite for local dev; set DATABASE_URL in .env for PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./researchlens.db"

    # Redis – leave empty to use in-memory dict cache
    REDIS_URL: str = ""

    # Google Gemini API key — used to refine research questions & evidence summaries.
    # Get a FREE key at: https://aistudio.google.com/app/apikey
    # Leave empty to disable LLM refinement (template-based questions will be used instead).
    GEMINI_API_KEY: str = "Add Your API Key Here"

    # NLP model
    EMBEDDING_MODEL: str = "allenai/specter2_base"

    # File upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20
    MAX_FILES: int = 50

    # Analysis defaults (can be overridden via Settings page)
    MIN_CLUSTER_SIZE: int = 3
    YEAR_RANGE_START: int = 2000
    YEAR_RANGE_END: int = 2024
    WEIGHT_STRUCT: float = 0.40
    WEIGHT_SEM: float = 0.35
    WEIGHT_TEMP: float = 0.25

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
