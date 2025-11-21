"""
Core configuration system with environment-based settings.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ============== APPLICATION ==============
    APP_NAME: str = "Enterprise AI Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ============== SERVER ==============
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # ============== SNOWFLAKE (OLAP) ==============
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: str
    SNOWFLAKE_DATABASE: str
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_WAREHOUSE: str
    SNOWFLAKE_ROLE: str
    SNOWFLAKE_POOL_SIZE: int = 20
    SNOWFLAKE_MAX_OVERFLOW: int = 10

    @property
    def snowflake_url(self) -> str:
        """Construct Snowflake SQLAlchemy URL"""
        return (
            f"snowflake://{self.SNOWFLAKE_USER}:{self.SNOWFLAKE_PASSWORD}"
            f"@{self.SNOWFLAKE_ACCOUNT}/{self.SNOWFLAKE_DATABASE}/{self.SNOWFLAKE_SCHEMA}"
            f"?warehouse={self.SNOWFLAKE_WAREHOUSE}&role={self.SNOWFLAKE_ROLE}"
        )

    # ============== CHECKPOINTING ==============
    CHECKPOINT_BACKEND: Literal["memory", "redis", "postgres"] = "memory"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ============== LLM PROVIDER ==============
    LLM_API_URL: str
    LLM_OAUTH_TOKEN_URL: str
    LLM_CLIENT_ID: str
    LLM_CLIENT_SECRET: str
    LLM_MODEL: str = "gpt-4"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 30

    # ============== S3 STORAGE ==============
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION: str = "us-east-1"

    # ============== COPILOTKIT ==============
    COPILOTKIT_ENABLED: bool = True
    COPILOTKIT_STREAMING: bool = True

    # ============== STREAMING ==============
    ENABLE_STREAMING: bool = True
    STREAM_TIMEOUT: int = 300

    # ============== PROMPTS ==============
    PROMPTS_DIR: str = "./prompts"

    # ============== AUTHENTICATION ==============
    AUTH_USERID_HEADER: str = "X-User-ID"
    AUTH_EMAIL_HEADER: str = "X-User-Email"
    AUTH_ROLE_HEADER: str = "X-User-Role"

    # ============== LANGSMITH ==============
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "enterprise-ai-agent"

    # ============== CORS ==============
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
