"""
FreeHekim RAG Module

Retrieval-Augmented Generation pipeline for medical content search and Q&A.
Combines vector search (Qdrant) with large language models (OpenAI GPT-4).
"""

from .client_qdrant import EXTERNAL, INTERNAL, search
from .embeddings import embed, embed_batch, get_embedding_dimension
from .pipeline import generate_answer, reciprocal_rank_fusion, retrieve_answer

__all__ = [
    "EXTERNAL",
    "INTERNAL",
    "embed",
    "embed_batch",
    "generate_answer",
    "get_embedding_dimension",
    "reciprocal_rank_fusion",
    "retrieve_answer",
    "search",
]

__version__ = "1.0.0"
