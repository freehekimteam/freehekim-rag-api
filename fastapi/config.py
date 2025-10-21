"""
FreeHekim Configuration

Application settings loaded from environment variables with validation.
Supports both .env files and environment variables.
"""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation.

    All settings can be overridden via environment variables.
    Example: QDRANT_HOST=localhost
    """

    # Environment
    env: Literal["staging", "production", "development"] = Field(
        default="staging",
        description="Application environment"
    )

    # Qdrant Configuration
    qdrant_host: str = Field(
        default="localhost",
        description="Qdrant server hostname",
        min_length=1
    )
    qdrant_port: int = Field(
        default=6333,
        description="Qdrant port (443 for HTTPS, 6333 for HTTP)",
        ge=1,
        le=65535
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
        description="Qdrant API key (required for production)"
    )

    # Embedding Provider
    embed_provider: Literal["openai", "bge-m3"] = Field(
        default="openai",
        description="Embedding generation provider"
    )

    # OpenAI Configuration
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model (1536 or 3072 dimensions)"
    )

    # LLM Configuration
    llm_model: str = Field(
        default="gpt-4",
        description="LLM model for answer generation (e.g., gpt-4o, gpt-4)"
    )
    llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature (0-2)"
    )
    llm_max_tokens: int = Field(
        default=800,
        ge=1,
        le=8192,
        description="Max tokens for generated answer"
    )

    # API Configuration
    api_port: int = Field(
        default=8080,
        description="API server port",
        ge=1024,
        le=65535
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_json: bool = Field(
        default=False,
        description="Enable JSON logging format"
    )

    # Qdrant client behavior
    qdrant_timeout: float = Field(
        default=10.0,
        ge=0.1,
        description="Qdrant client timeout in seconds"
    )

    # RAG pipeline tuning
    search_topk: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Top-K results to retrieve per collection"
    )
    pipeline_max_context_chunks: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max number of context chunks to feed LLM"
    )
    pipeline_max_source_display: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max number of sources to include in response"
    )
    pipeline_max_source_text_length: int = Field(
        default=200,
        ge=50,
        le=2000,
        description="Max characters per source preview"
    )

    # Basic protections
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Requests allowed per client IP per minute"
    )
    max_body_size_bytes: int = Field(
        default=1048576,
        ge=1024,
        le=10485760,
        description="Maximum request body size in bytes"
    )

    # Response caching
    enable_cache: bool = Field(
        default=True,
        description="Enable simple in-memory response cache"
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=10,
        le=86400,
        description="TTL for in-memory cache (seconds)"
    )

    # Simple API key protection for /rag/query
    require_api_key: bool = Field(
        default=False,
        description="Require X-Api-Key header for protected endpoints"
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="API key value for X-Api-Key header (set when require_api_key=true)"
    )

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )

    @classmethod
    def validate_qdrant_key(cls, v: str | None, info) -> str | None:
        """Runtime-overrideable validator for Qdrant key (used by tests)."""
        env = info.data.get("env", "staging")
        if env == "production" and not v:
            raise ValueError("QDRANT_API_KEY is required in production environment")
        return v

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def _validator_qdrant_api_key(cls, v: str | None, info) -> str | None:
        # Delegate to (patchable) validate_qdrant_key, support patched plain functions
        func = getattr(cls, "validate_qdrant_key")
        try:
            return func(v, info)
        except TypeError:
            return func(cls, v, info)

    @classmethod
    def validate_openai_key(cls, v: str | None, info) -> str | None:
        """Runtime-overrideable validator for OpenAI key (used by tests)."""
        provider = info.data.get("embed_provider", "openai")
        if provider == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        return v

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _validator_openai_api_key(cls, v: str | None, info) -> str | None:
        # Delegate to (patchable) validate_openai_key, support patched plain functions
        func = getattr(cls, "validate_openai_key")
        try:
            return func(v, info)
        except TypeError:
            return func(cls, v, info)

    def get_qdrant_api_key(self) -> str | None:
        """Get plain text Qdrant API key"""
        return self.qdrant_api_key.get_secret_value() if self.qdrant_api_key else None

    def get_openai_api_key(self) -> str | None:
        """Get plain text OpenAI API key"""
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None

    def get_api_key(self) -> str | None:
        """Get plain text API key for request authentication"""
        return self.api_key.get_secret_value() if self.api_key else None

    @property
    def use_https(self) -> bool:
        """Determine if HTTPS should be used for Qdrant connection"""
        return self.qdrant_port == 443

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.env == "development"
