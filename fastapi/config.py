from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "staging"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    embed_provider: str = "openai"  # or bge-m3

    class Config:
        env_file = "/app/.env"
