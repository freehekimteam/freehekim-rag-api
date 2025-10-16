"""
HakanCloud RAG Pipeline

Retrieval-Augmented Generation with reciprocal-rank fusion.
Combines vector search with GPT-4 to generate contextual answers
from medical knowledge base.
"""

import logging
from typing import Any

from openai import OpenAI, OpenAIError
from qdrant_client.models import ScoredPoint

from config import Settings

from .client_qdrant import EXTERNAL, INTERNAL, search
from .embeddings import EmbeddingError, embed

logger = logging.getLogger(__name__)
settings = Settings()

# Constants
RRF_K = 60  # Reciprocal-Rank Fusion constant
DEFAULT_TOP_K = 5  # Default number of results to retrieve
MAX_CONTEXT_CHUNKS = 5  # Maximum context chunks for LLM
MAX_SOURCE_DISPLAY = 3  # Maximum sources to include in response
MAX_SOURCE_TEXT_LENGTH = 200  # Maximum source text preview length
GPT_MODEL = "gpt-4"  # LLM model for answer generation
GPT_TEMPERATURE = 0.3  # Low temperature for factual responses
GPT_MAX_TOKENS = 800  # Maximum tokens in generated answer

# Medical disclaimer in Turkish
MEDICAL_DISCLAIMER = (
    "⚠️ Bu bilgi tıbbi tavsiye değildir. "
    "Sağlık kararlarınız için mutlaka hekiminize danışın."
)

# Global OpenAI client for LLM generation
_llm_client: OpenAI | None = None


class RAGError(Exception):
    """Custom exception for RAG pipeline errors"""
    pass


def _get_llm_client() -> OpenAI:
    """
    Get or create OpenAI client for LLM generation (singleton pattern).

    Returns:
        OpenAI: Configured OpenAI client

    Raises:
        ValueError: If OpenAI API key not configured
    """
    global _llm_client

    if _llm_client is None:
        api_key = settings.get_openai_api_key()
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        _llm_client = OpenAI(api_key=api_key)
        logger.info(f"✅ OpenAI LLM client initialized with model: {GPT_MODEL}")

    return _llm_client


def reciprocal_rank_fusion(
    internal_results: list[ScoredPoint],
    external_results: list[ScoredPoint],
    k: int = RRF_K
) -> list[tuple[ScoredPoint, float, str]]:
    """
    Combine results from multiple sources using Reciprocal Rank Fusion.

    RRF formula: score(doc) = Σ 1/(k + rank_i)
    where k=60 is a typical constant value.

    This algorithm combines rankings from multiple retrieval systems
    without requiring calibrated scores.

    Args:
        internal_results: Search results from internal FreeHekim collection
        external_results: Search results from external medical knowledge
        k: RRF constant (default 60, higher values = less emphasis on rank)

    Returns:
        List of (result, fused_score, source) tuples sorted by fused score descending
        Source can be: 'internal', 'external', or 'both'

    Example:
        >>> internal = [doc1, doc2]  # doc1 ranked #1, doc2 ranked #2
        >>> external = [doc2, doc3]  # doc2 ranked #1, doc3 ranked #2
        >>> fused = reciprocal_rank_fusion(internal, external)
        >>> # doc2 will have highest score (appeared in both rankings)
    """
    scores: dict[str, dict[str, Any]] = {}

    # Score internal results
    for rank, result in enumerate(internal_results, start=1):
        point_id = str(result.id)
        rrf_score = 1.0 / (k + rank)

        if point_id not in scores:
            scores[point_id] = {
                "result": result,
                "score": 0.0,
                "source": "internal"
            }
        scores[point_id]["score"] += rrf_score

    # Score external results
    for rank, result in enumerate(external_results, start=1):
        point_id = str(result.id)
        rrf_score = 1.0 / (k + rank)

        if point_id not in scores:
            scores[point_id] = {
                "result": result,
                "score": 0.0,
                "source": "external"
            }
        else:
            # Document appears in both collections
            scores[point_id]["source"] = "both"
        scores[point_id]["score"] += rrf_score

    # Sort by fused score (descending)
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    logger.debug(
        f"RRF merged {len(internal_results)} internal + {len(external_results)} external "
        f"= {len(sorted_results)} unique results"
    )

    return [(r["result"], r["score"], r["source"]) for r in sorted_results]


def generate_answer(question: str, context_chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate answer using GPT-4 with retrieved context.

    Args:
        question: User's question in Turkish
        context_chunks: Retrieved text chunks with metadata from Qdrant

    Returns:
        Dictionary with:
        - answer: Generated answer with medical disclaimer
        - tokens_used: Total tokens consumed
        - model: Model used for generation
        - error: Error message if generation failed (optional)

    Raises:
        RAGError: If answer generation fails critically
    """
    if not context_chunks:
        logger.warning("No context chunks provided for answer generation")
        return {
            "answer": (
                "Üzgünüm, bu soruyla ilgili bilgi bulamadım. "
                "Lütfen sorunuzu farklı şekilde ifade etmeyi deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "tokens_used": 0,
            "model": GPT_MODEL,
            "warning": "No context available"
        }

    try:
        client = _get_llm_client()

        # Build context from top chunks (limit to MAX_CONTEXT_CHUNKS)
        context_parts = []
        for i, chunk in enumerate(context_chunks[:MAX_CONTEXT_CHUNKS], start=1):
            text = chunk.get("text", "")
            # Truncate long texts for context window efficiency
            if len(text) > 500:
                text = text[:500] + "..."
            context_parts.append(f"[Kaynak {i}]: {text}")

        context_text = "\n\n".join(context_parts)

        # System prompt with medical guidelines
        system_prompt = f"""Sen FreeHekim'in AI asistanısın. Sağlık konularında bilgilendirme yapıyorsun.

ÖNEMLİ KURALLAR:
1. Verilen KAYNAK bilgilerini kullanarak cevap ver
2. Kaynak göster: [Kaynak 1], [Kaynak 2] şeklinde
3. MUTLAKA tıbbi sorumluluk reddi ekle
4. Teşhis veya tedavi önerme, sadece bilgilendir
5. Türkçe ve anlaşılır cevap ver
6. Bilmiyorsan veya kaynaklarda yoksa belirt

SORUMLULUK REDDİ (MUTLAKA EKLE):
{MEDICAL_DISCLAIMER}
"""

        # User prompt
        user_prompt = f"""SORU: {question}

KAYNAK BİLGİLER:
{context_text}

Yukarıdaki kaynaklara dayanarak soruyu cevapla. Kaynak numaralarını belirt ve tıbbi sorumluluk reddi ekle."""

        # Call GPT-4
        logger.debug(f"Calling {GPT_MODEL} with {len(context_chunks)} context chunks")

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=GPT_TEMPERATURE,
            max_tokens=GPT_MAX_TOKENS
        )

        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Ensure disclaimer is present (fallback if model didn't include it)
        if MEDICAL_DISCLAIMER not in answer:
            logger.warning("Medical disclaimer not in answer, appending it")
            answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"

        logger.info(f"✅ Generated answer: {tokens_used} tokens, {len(answer)} chars")

        return {
            "answer": answer,
            "tokens_used": tokens_used,
            "model": GPT_MODEL
        }

    except OpenAIError as e:
        logger.error(f"OpenAI LLM error: {e}")
        return {
            "answer": (
                "Üzgünüm, şu anda cevap oluşturamıyorum. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"OpenAI error: {str(e)}",
            "tokens_used": 0,
            "model": GPT_MODEL
        }
    except Exception as e:
        logger.error(f"Unexpected error during answer generation: {e}", exc_info=True)
        raise RAGError(f"Failed to generate answer: {e}") from e


def retrieve_answer(q: str, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    """
    Main RAG pipeline: Retrieve + Rank + Generate.

    This is the primary entry point for the RAG system.

    **Pipeline Steps:**
    1. Embed query using OpenAI embeddings
    2. Search internal (FreeHekim) and external collections in parallel
    3. Merge results using Reciprocal-Rank Fusion
    4. Extract top-k context chunks
    5. Generate answer with GPT-4
    6. Format and return response

    Args:
        q: User question (will be trimmed)
        top_k: Number of chunks to retrieve per collection (default: 5)

    Returns:
        Dictionary with:
        - question: Original question
        - answer: Generated answer with medical disclaimer
        - sources: Top source documents used (up to 3)
        - metadata: Pipeline statistics (hits, tokens, model)
        - error: Error message if pipeline failed (optional)

    Example:
        >>> result = retrieve_answer("Diyabet belirtileri nelerdir?")
        >>> print(result["answer"])
        >>> print(f"Used {result['metadata']['tokens_used']} tokens")
    """
    q = q.strip()

    if not q:
        return {
            "question": "",
            "answer": f"Lütfen bir soru girin.\n\n{MEDICAL_DISCLAIMER}",
            "sources": [],
            "metadata": {"error": "Empty question"},
            "error": "Question cannot be empty"
        }

    try:
        # Step 1: Embed query
        logger.info(f"🔍 RAG Query: {q[:100]}{'...' if len(q) > 100 else ''}")
        query_vector = embed(q)

        # Step 2: Search both collections in parallel
        internal_results = search(query_vector, top_k, INTERNAL)
        external_results = search(query_vector, top_k, EXTERNAL)

        logger.info(
            f"📊 Retrieved: {len(internal_results)} internal, "
            f"{len(external_results)} external"
        )

        # Step 3: Reciprocal-rank fusion
        fused_results = reciprocal_rank_fusion(internal_results, external_results)

        if not fused_results:
            logger.warning("No results from vector search")
            return {
                "question": q,
                "answer": (
                    "Bu soruyla ilgili bilgi bulamadım. "
                    "Lütfen sorunuzu farklı şekilde ifade etmeyi deneyin.\n\n"
                    f"{MEDICAL_DISCLAIMER}"
                ),
                "sources": [],
                "metadata": {
                    "internal_hits": len(internal_results),
                    "external_hits": len(external_results),
                    "fused_results": 0,
                    "tokens_used": 0,
                    "model": GPT_MODEL
                }
            }

        # Step 4: Extract context chunks
        context_chunks = []
        for result, score, source in fused_results[:top_k]:
            context_chunks.append({
                "text": result.payload.get("text", ""),
                "source": source,
                "score": score,
                "metadata": result.payload.get("metadata", {})
            })

        logger.info(f"📚 Using {len(context_chunks)} context chunks for answer generation")

        # Step 5: Generate answer with LLM
        generation_result = generate_answer(q, context_chunks)

        # Step 6: Format response
        response = {
            "question": q,
            "answer": generation_result.get("answer", ""),
            "sources": [
                {
                    "text": (
                        chunk["text"][:MAX_SOURCE_TEXT_LENGTH] + "..."
                        if len(chunk["text"]) > MAX_SOURCE_TEXT_LENGTH
                        else chunk["text"]
                    ),
                    "source": chunk["source"],
                    "score": round(chunk["score"], 4)
                }
                for chunk in context_chunks[:MAX_SOURCE_DISPLAY]
            ],
            "metadata": {
                "internal_hits": len(internal_results),
                "external_hits": len(external_results),
                "fused_results": len(fused_results),
                "tokens_used": generation_result.get("tokens_used", 0),
                "model": generation_result.get("model", GPT_MODEL)
            }
        }

        # Add error field if present in generation
        if "error" in generation_result:
            response["error"] = generation_result["error"]

        logger.info(f"✅ RAG pipeline completed successfully")
        return response

    except EmbeddingError as e:
        logger.error(f"Embedding error in RAG pipeline: {e}")
        return {
            "question": q,
            "answer": (
                "Sorunuzu işlerken bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Embedding error: {str(e)}",
            "sources": [],
            "metadata": {"error_type": "embedding"}
        }
    except ConnectionError as e:
        logger.error(f"Qdrant connection error in RAG pipeline: {e}")
        return {
            "question": q,
            "answer": (
                "Veritabanı bağlantısı kurulamadı. Lütfen daha sonra tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Database error: {str(e)}",
            "sources": [],
            "metadata": {"error_type": "database"}
        }
    except RAGError as e:
        logger.error(f"RAG pipeline error: {e}")
        return {
            "question": q,
            "answer": (
                "Cevap oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": str(e),
            "sources": [],
            "metadata": {"error_type": "rag"}
        }
    except Exception as e:
        logger.error(f"Unexpected error in RAG pipeline: {e}", exc_info=True)
        return {
            "question": q,
            "answer": (
                "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Unexpected error: {str(e)}",
            "sources": [],
            "metadata": {"error_type": "unexpected"}
        }
