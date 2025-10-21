"""
FreeHekim RAG Module

Retrieval-Augmented Generation pipeline for medical content search and Q&A.
Combines vector search (Qdrant) with large language models (OpenAI GPT-4).
"""

from .client_qdrant import EXTERNAL, INTERNAL, search
from .embeddings import embed, embed_batch, get_embedding_dimension
from .pipeline import generate_answer, reciprocal_rank_fusion, retrieve_answer

__all__ = [
    # Qdrant client
    "search",
    "INTERNAL",
    "EXTERNAL",
    # Embeddings
    "embed",
    "embed_batch",
    "get_embedding_dimension",
    # Pipeline
    "retrieve_answer",
    "generate_answer",
    "reciprocal_rank_fusion",
]

__version__ = "1.0.0"
