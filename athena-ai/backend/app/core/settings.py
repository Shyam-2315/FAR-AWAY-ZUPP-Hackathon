from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    athena_env: str = Field(default="development", alias="ATHENA_ENV")
    athena_log_level: str = Field(default="INFO", alias="ATHENA_LOG_LEVEL")

    # Legacy single-value CORS variable kept for backwards compatibility.
    backend_cors_origins_raw: str = Field(
        default="http://localhost:3000",
        alias="BACKEND_CORS_ORIGINS",
    )
    # New comma-separated variable for frontend origins (Vite, Next, CRA, etc.).
    # Both variables are merged — set either or both.
    frontend_origins_raw: str = Field(
        default=(
            "http://localhost:3000,http://localhost:5173,http://localhost:8080,"
            "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8080"
        ),
        alias="FRONTEND_ORIGINS",
    )

    database_url: str = Field(
        default="postgresql+psycopg://athena:athena_dev_password@localhost:5433/athena",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    langgraph_checkpoint_uri: str = Field(default="", alias="LANGGRAPH_CHECKPOINT_URI")

    # JWT / Auth
    jwt_secret_key: str = Field(
        default="CHANGE_ME_use_a_32+_char_random_secret_in_production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    @staticmethod
    def _parse_origins(raw: str) -> list[str]:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def backend_cors_origins(self) -> list[str]:
        """Merged, deduplicated list of all allowed CORS origins.

        Combines BACKEND_CORS_ORIGINS and FRONTEND_ORIGINS so that either
        variable alone is sufficient for local development, and both can be
        set independently in staging/production.
        """
        seen: set[str] = set()
        result: list[str] = []
        for origin in (
            self._parse_origins(self.backend_cors_origins_raw)
            + self._parse_origins(self.frontend_origins_raw)
        ):
            if origin not in seen:
                seen.add(origin)
                result.append(origin)
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
