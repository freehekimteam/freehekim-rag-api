"""
Embedding generation module for HakanCloud RAG
Supports OpenAI text-embedding-3-small (1536 dimensions)
"""
import logging
from typing import List, Union
from openai import OpenAI
from config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# Initialize OpenAI client
_openai_client = None

def _get_openai_client() -> OpenAI:
    """Lazy initialization of OpenAI client"""
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        _openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info(f"✅ OpenAI client initialized with model: {settings.openai_embedding_model}")
    return _openai_client


def embed(text: str) -> List[float]:
    """
    Generate embedding for a single text using OpenAI.

    Args:
        text: Input text to embed

    Returns:
        1536-dimensional embedding vector

    Raises:
        ValueError: If OpenAI API key not configured
        Exception: If embedding generation fails
    """
    if settings.embed_provider == "openai":
        try:
            client = _get_openai_client()
            response = client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text (length: {len(text)} chars)")
            return embedding

        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    elif settings.embed_provider == "bge-m3":
        # TODO: Implement BGE-M3 local model fallback
        logger.warning("BGE-M3 provider not yet implemented, using OpenAI")
        settings.embed_provider = "openai"
        return embed(text)

    else:
        raise ValueError(f"Unknown embed_provider: {settings.embed_provider}")


def embed_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (batch processing).

    Args:
        texts: List of texts to embed
        batch_size: Maximum texts per API call (OpenAI limit: 2048)

    Returns:
        List of 1536-dimensional embedding vectors
    """
    if settings.embed_provider == "openai":
        try:
            client = _get_openai_client()

            # Process in batches to respect API limits
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                response = client.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=batch,
                    encoding_format="float"
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.info(f"✅ Processed batch {i // batch_size + 1}: {len(batch)} texts")

            return all_embeddings

        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise

    else:
        # Fallback to single embed for other providers
        return [embed(text) for text in texts]


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings for current provider"""
    if settings.embed_provider == "openai":
        # text-embedding-3-small = 1536 dims
        # text-embedding-3-large = 3072 dims
        if "large" in settings.openai_embedding_model:
            return 3072
        return 1536
    return 1536  # default
