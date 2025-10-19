"""
Qdrant Vector Database Client

Manages connection and search operations for FreeHekim vector collections.
"""

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint

from config import Settings

logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Collection names
INTERNAL = "freehekim_internal"  # Internal FreeHekim articles
EXTERNAL = "freehekim_external"  # External medical knowledge

# Global Qdrant client instance
_qdrant: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Get or create Qdrant client instance (singleton pattern).

    Returns:
        QdrantClient: Configured Qdrant client

    Raises:
        ConnectionError: If Qdrant connection fails
    """
    global _qdrant

    if _qdrant is None:
        try:
            logger.info(
                f"Connecting to Qdrant: {settings.qdrant_host}:{settings.qdrant_port} "
                f"(HTTPS: {settings.use_https})"
            )

            _qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.get_qdrant_api_key(),
                https=settings.use_https,
                timeout=10.0  # Connection timeout
            )

            # Verify connection
            _qdrant.get_collections()
            logger.info("✅ Qdrant connection established")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Qdrant connection failed: {e}") from e

    return _qdrant


def search(
    vector: list[float],
    topk: int = 5,
    collection: str = INTERNAL,
    score_threshold: float | None = None
) -> list[ScoredPoint]:
    """
    Search for similar vectors in Qdrant collection.

    Args:
        vector: Query embedding vector (1536 dimensions for OpenAI)
        topk: Number of results to return (default: 5)
        collection: Collection name (INTERNAL or EXTERNAL)
        score_threshold: Minimum similarity score (optional)

    Returns:
        List of ScoredPoint objects with similar documents

    Raises:
        ValueError: If collection name is invalid
        ConnectionError: If Qdrant is unreachable
    """
    if collection not in [INTERNAL, EXTERNAL]:
        raise ValueError(
            f"Invalid collection: {collection}. Must be '{INTERNAL}' or '{EXTERNAL}'"
        )

    if topk < 1 or topk > 100:
        raise ValueError(f"topk must be between 1 and 100, got {topk}")

    try:
        client = get_qdrant_client()

        search_params = {
            "collection_name": collection,
            "query_vector": vector,
            "limit": topk
        }

        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold

        results = client.search(**search_params)

        logger.debug(
            f"Search completed: {len(results)} results from {collection} "
            f"(requested: {topk})"
        )

        return results

    except Exception as e:
        logger.error(f"Qdrant search error in {collection}: {e}")
        raise ConnectionError(f"Failed to search Qdrant: {e}") from e


def collection_exists(collection_name: str) -> bool:
    """
    Check if a collection exists in Qdrant.

    Args:
        collection_name: Name of the collection to check

    Returns:
        True if collection exists, False otherwise
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        return collection_name in [col.name for col in collections.collections]
    except Exception as e:
        logger.error(f"Error checking collection existence: {e}")
        return False


def get_collection_info(collection_name: str) -> dict[str, Any]:
    """
    Get information about a collection.

    Args:
        collection_name: Name of the collection

    Returns:
        Dictionary with collection metadata

    Raises:
        ValueError: If collection doesn't exist
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name)

        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        raise ValueError(f"Collection '{collection_name}' not found or unreachable") from e


# Note: Do NOT initialize the client at import-time to avoid startup failures
_qdrant = None  # Will be created on first use via get_qdrant_client()
