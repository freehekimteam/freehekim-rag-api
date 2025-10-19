"""
Embedding generation module for FreeHekim RAG
Supports OpenAI text-embedding-3-small (1536 dimensions)
"""

import logging
from typing import Literal

try:  # Compatibility with openai>=1.0.0
    from openai import OpenAI, OpenAIError  # type: ignore
except Exception:  # Fallback for newer versions where OpenAIError may be renamed
    from openai import OpenAI  # type: ignore
    try:
        from openai import APIError as OpenAIError  # type: ignore
    except Exception:  # Last resort
        OpenAIError = Exception  # type: ignore

from config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# Global OpenAI client instance
_openai_client: OpenAI | None = None


class EmbeddingError(Exception):
    """Custom exception for embedding generation errors"""
    pass


def _get_openai_client() -> OpenAI:
    """
    Get or create OpenAI client instance (singleton pattern).

    Returns:
        OpenAI: Configured OpenAI client

    Raises:
        ValueError: If OpenAI API key not configured
    """
    global _openai_client

    if _openai_client is None:
        api_key = settings.get_openai_api_key()
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")

        _openai_client = OpenAI(api_key=api_key)
        logger.info(f"✅ OpenAI client initialized with model: {settings.openai_embedding_model}")

    return _openai_client


def embed(text: str) -> list[float]:
    """
    Generate embedding for a single text using OpenAI.

    Args:
        text: Input text to embed (will be stripped)

    Returns:
        1536-dimensional embedding vector

    Raises:
        ValueError: If text is empty or OpenAI API key not configured
        EmbeddingError: If embedding generation fails
    """
    # Validate input
    text = text.strip()
    if not text:
        raise ValueError("Cannot embed empty text")

    if len(text) > 8000:  # OpenAI limit is ~8k tokens
        logger.warning(f"Text too long ({len(text)} chars), truncating to 8000 chars")
        text = text[:8000]

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

        except OpenAIError as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}")
            raise EmbeddingError(f"Unexpected embedding error: {e}") from e

    elif settings.embed_provider == "bge-m3":
        # TODO: Implement BGE-M3 local model fallback
        logger.warning("BGE-M3 provider not yet implemented, falling back to OpenAI")
        # Temporarily switch to OpenAI
        original_provider = settings.embed_provider
        settings.embed_provider = "openai"
        try:
            return embed(text)
        finally:
            settings.embed_provider = original_provider

    else:
        raise ValueError(f"Unknown embed_provider: {settings.embed_provider}")


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Generate embeddings for multiple texts (batch processing).

    Args:
        texts: List of texts to embed
        batch_size: Maximum texts per API call (OpenAI limit: 2048, default: 100)

    Returns:
        List of 1536-dimensional embedding vectors

    Raises:
        ValueError: If texts list is empty or batch_size invalid
        EmbeddingError: If batch embedding fails
    """
    if not texts:
        raise ValueError("Cannot embed empty list of texts")

    if batch_size < 1 or batch_size > 2048:
        raise ValueError(f"batch_size must be between 1 and 2048, got {batch_size}")

    # Filter empty texts and log warning
    original_count = len(texts)
    texts = [t.strip() for t in texts if t.strip()]
    if len(texts) < original_count:
        logger.warning(f"Filtered out {original_count - len(texts)} empty texts")

    if not texts:
        raise ValueError("All texts are empty after filtering")

    if settings.embed_provider == "openai":
        try:
            client = _get_openai_client()

            # Process in batches to respect API limits
            all_embeddings: list[list[float]] = []
            total_batches = (len(texts) + batch_size - 1) // batch_size

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_num = i // batch_size + 1

                logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch)} texts")

                response = client.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=batch,
                    encoding_format="float"
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.info(f"✅ Completed batch {batch_num}/{total_batches}")

            return all_embeddings

        except OpenAIError as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during batch embedding: {e}")
            raise EmbeddingError(f"Unexpected batch embedding error: {e}") from e

    else:
        # Fallback to single embed for other providers
        logger.info(f"Using single-embed fallback for {len(texts)} texts")
        return [embed(text) for text in texts]


def get_embedding_dimension() -> Literal[1536, 3072]:
    """
    Get the dimension of embeddings for current provider.

    Returns:
        1536 for text-embedding-3-small, 3072 for text-embedding-3-large
    """
    if settings.embed_provider == "openai":
        # text-embedding-3-small = 1536 dims
        # text-embedding-3-large = 3072 dims
        if "large" in settings.openai_embedding_model.lower():
            return 3072
        return 1536
    return 1536  # default
