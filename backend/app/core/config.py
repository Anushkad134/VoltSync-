from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./voltsync.db"
    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM_NUMBER: str = ""
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"
    CREWAI_MODEL_API_KEY: str = ""
    PRIMARY_LLM_MODEL: str = "openai/gpt-oss-120b"
    PRIMARY_LLM_API_KEY: str = ""
    FALLBACK_LLM_MODEL: str = "qwen/qwen3.8-27b"
    FALLBACK_LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    APP_ENV: str = "development"
    AGENT_DECISION_TIMEOUT_SECONDS: int = 30
    RANDOM_SEED: int = 42
    SIMULATION_DAYS: int = 7
    INTERVAL_MINUTES: int = 15
    SESSIONS_PER_STATION_PER_DAY: int = 5
    PROGRESS_NOTIFICATION_INTERVAL_MINUTES: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()
