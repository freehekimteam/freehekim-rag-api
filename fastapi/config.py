from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "staging"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    embed_provider: str = "openai"  # or bge-m3
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"  # 1536 dimensions

    class Config:
        # Read from environment variables (set by docker-compose env_file)
        # Also supports local .env file if present
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
