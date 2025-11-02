"""
FreeHekim RAG Pipeline

Retrieval-Augmented Generation with reciprocal-rank fusion.
Combines vector search with GPT-4 to generate contextual answers
from medical knowledge base.
"""

import hashlib
import logging
import time
from typing import Any

try:  # Compatibility across openai versions
    from openai import OpenAI, OpenAIError  # type: ignore  # nosemgrep
except Exception:
    from openai import OpenAI  # type: ignore  # nosemgrep

    try:
        from openai import APIError as OpenAIError  # type: ignore  # nosemgrep
    except Exception:  # Last resort
        OpenAIError = Exception  # type: ignore
from qdrant_client.models import ScoredPoint

from config import Settings

from .client_qdrant import EXTERNAL, INTERNAL, search
from .embeddings import EmbeddingError, embed

logger = logging.getLogger(__name__)
settings = Settings()

# Constants
RRF_K = 60  # Reciprocal-Rank Fusion constant

# Medical disclaimer in Turkish
MEDICAL_DISCLAIMER = (
    "⚠️ Bu bilgi tıbbi tavsiye değildir. " "Sağlık kararlarınız için mutlaka hekiminize danışın."
)

# Global OpenAI client for LLM generation
_llm_client: OpenAI | None = None
_response_cache: dict[str, tuple[float, dict[str, Any]]] = {}

# Prometheus metrics for RAG pipeline
try:
    from prometheus_client import Counter, Histogram

    RAG_TOTAL_SECONDS = Histogram(
        "rag_total_seconds",
        "Total RAG pipeline duration in seconds",
        buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
    )
    RAG_EMBED_SECONDS = Histogram(
        "rag_embed_seconds",
        "Embedding duration in seconds",
        buckets=(0.01, 0.02, 0.05, 0.1, 0.2, 0.5),
    )
    RAG_SEARCH_SECONDS = Histogram(
        "rag_search_seconds",
        "Vector search duration in seconds",
        labelnames=("collection",),
        buckets=(0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1),
    )
    RAG_GENERATE_SECONDS = Histogram(
        "rag_generate_seconds",
        "LLM generation duration in seconds",
        buckets=(0.1, 0.2, 0.5, 1, 2, 5),
    )
    RAG_ERRORS_TOTAL = Counter("rag_errors_total", "Total RAG errors", labelnames=("type",))
    RAG_TOKENS_TOTAL = Counter(
        "rag_tokens_total",
        "Total OpenAI tokens used",
        labelnames=("model",),
    )
except Exception:  # Metrics are optional
    RAG_TOTAL_SECONDS = None
    RAG_EMBED_SECONDS = None
    RAG_SEARCH_SECONDS = None
    RAG_GENERATE_SECONDS = None
    RAG_ERRORS_TOTAL = None
    RAG_TOKENS_TOTAL = None


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
        logger.info(f"✅ OpenAI LLM client initialized with model: {settings.llm_model}")

    return _llm_client


def reciprocal_rank_fusion(
    internal_results: list[ScoredPoint], external_results: list[ScoredPoint], k: int = RRF_K
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
            scores[point_id] = {"result": result, "score": 0.0, "source": "internal"}
        scores[point_id]["score"] += rrf_score

    # Score external results
    for rank, result in enumerate(external_results, start=1):
        point_id = str(result.id)
        rrf_score = 1.0 / (k + rank)

        if point_id not in scores:
            scores[point_id] = {"result": result, "score": 0.0, "source": "external"}
        else:
            # Document appears in both collections
            scores[point_id]["source"] = "both"
        scores[point_id]["score"] += rrf_score

    # Sort by fused score (descending)
    sorted_results = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

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
            "model": settings.llm_model,
            "warning": "No context available",
        }

    try:
        client = _get_llm_client()

        # Build context from top chunks (limit to configured max)
        context_parts = []
        for i, chunk in enumerate(context_chunks[: settings.pipeline_max_context_chunks], start=1):
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
        logger.debug(f"Calling {settings.llm_model} with {len(context_chunks)} context chunks")

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens,
                )
                break
            except OpenAIError:
                if attempt < 2:
                    import time as _t

                    _t.sleep(0.2 * (2**attempt))
                    continue
                raise

        answer = response.choices[0].message.content
        tokens_used = getattr(response.usage, "total_tokens", 0)

        # Ensure disclaimer is present (fallback if model didn't include it)
        if MEDICAL_DISCLAIMER not in answer:
            logger.warning("Medical disclaimer not in answer, appending it")
            answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"

        logger.info(f"✅ Generated answer: {tokens_used} tokens, {len(answer)} chars")
        if "RAG_TOKENS_TOTAL" in globals() and RAG_TOKENS_TOTAL:
            try:
                RAG_TOKENS_TOTAL.labels(model=settings.llm_model).inc(tokens_used)
            except Exception:
                logger.debug("Prometheus token metric update failed; continuing", exc_info=True)

        return {"answer": answer, "tokens_used": tokens_used, "model": settings.llm_model}

    except OpenAIError as e:
        logger.error(f"OpenAI LLM error: {e}")
        return {
            "answer": (
                "Üzgünüm, şu anda cevap oluşturamıyorum. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"OpenAI error: {e!s}",
            "tokens_used": 0,
            "model": settings.llm_model,
        }
    except Exception as e:
        logger.error(f"Unexpected error during answer generation: {e}", exc_info=True)
        raise RAGError(f"Failed to generate answer: {e}") from e


def retrieve_answer(q: str, top_k: int | None = None) -> dict[str, Any]:
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
            "error": "Question cannot be empty",
        }

    try:
        top_k = top_k or settings.search_topk

        # Step 1: Embed query
        logger.info(f"🔍 RAG Query: {q[:100]}{'...' if len(q) > 100 else ''}")
        t0 = time.perf_counter()
        # Cache check (before embedding)
        cache_key = None
        if settings.enable_cache:
            key_raw = f"q={q}|topk={top_k}|model={settings.llm_model}"
            cache_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
            item = _response_cache.get(cache_key)
            if item and (time.monotonic() - item[0] <= settings.cache_ttl_seconds):
                logger.info("⚡ Cache hit for query")
                return item[1]
        query_vector = embed(q)
        t1 = time.perf_counter()
        if RAG_EMBED_SECONDS:
            RAG_EMBED_SECONDS.observe(t1 - t0)

        # Step 2: Search both collections in parallel (thread pool)
        from concurrent.futures import ThreadPoolExecutor

        t2 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_internal = executor.submit(search, query_vector, top_k, INTERNAL)
            future_external = executor.submit(search, query_vector, top_k, EXTERNAL)
            internal_results = future_internal.result()
            external_results = future_external.result()
        t3 = time.perf_counter()
        if RAG_SEARCH_SECONDS:
            RAG_SEARCH_SECONDS.labels(collection="internal").observe((t3 - t2) / 2)
            RAG_SEARCH_SECONDS.labels(collection="external").observe((t3 - t2) / 2)

        logger.info(
            f"📊 Retrieved: {len(internal_results)} internal, " f"{len(external_results)} external"
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
                    "model": settings.llm_model,
                },
            }

        # Step 4: Extract context chunks
        context_chunks = []
        for result, score, source in fused_results[:top_k]:
            context_chunks.append(
                {
                    "text": result.payload.get("text", ""),
                    "source": source,
                    "score": score,
                    "metadata": result.payload.get("metadata", {}),
                }
            )

        logger.info(f"📚 Using {len(context_chunks)} context chunks for answer generation")

        # Step 5: Generate answer with LLM
        t4 = time.perf_counter()
        generation_result = generate_answer(q, context_chunks)
        t5 = time.perf_counter()
        if RAG_GENERATE_SECONDS:
            RAG_GENERATE_SECONDS.observe(t5 - t4)

        # Step 6: Format response
        response = {
            "question": q,
            "answer": generation_result.get("answer", ""),
            "sources": [
                {
                    "text": (
                        chunk["text"][: settings.pipeline_max_source_text_length] + "..."
                        if len(chunk["text"]) > settings.pipeline_max_source_text_length
                        else chunk["text"]
                    ),
                    "source": chunk["source"],
                    "score": round(chunk["score"], 4),
                }
                for chunk in context_chunks[: settings.pipeline_max_source_display]
            ],
            "metadata": {
                "internal_hits": len(internal_results),
                "external_hits": len(external_results),
                "fused_results": len(fused_results),
                "tokens_used": generation_result.get("tokens_used", 0),
                "model": generation_result.get("model", settings.llm_model),
            },
        }

        # Add error field if present in generation
        if "error" in generation_result:
            response["error"] = generation_result["error"]

        logger.info("✅ RAG pipeline completed successfully")
        if RAG_TOTAL_SECONDS:
            RAG_TOTAL_SECONDS.observe(t5 - t0)
        # Save to cache
        if settings.enable_cache and cache_key:
            try:
                _response_cache[cache_key] = (time.monotonic(), response)
            except Exception:
                logger.debug("Cache save failed; ignoring and continuing", exc_info=True)
        return response

    except EmbeddingError as e:
        logger.error(f"Embedding error in RAG pipeline: {e}")
        if RAG_ERRORS_TOTAL:
            RAG_ERRORS_TOTAL.labels(type="embedding").inc()
        return {
            "question": q,
            "answer": (
                "Sorunuzu işlerken bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Embedding error: {e!s}",
            "sources": [],
            "metadata": {"error_type": "embedding"},
        }
    except ConnectionError as e:
        logger.error(f"Qdrant connection error in RAG pipeline: {e}")
        if RAG_ERRORS_TOTAL:
            RAG_ERRORS_TOTAL.labels(type="database").inc()
        return {
            "question": q,
            "answer": (
                "Veritabanı bağlantısı kurulamadı. Lütfen daha sonra tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Database error: {e!s}",
            "sources": [],
            "metadata": {"error_type": "database"},
        }
    except RAGError as e:
        logger.error(f"RAG pipeline error: {e}")
        if RAG_ERRORS_TOTAL:
            RAG_ERRORS_TOTAL.labels(type="rag").inc()
        return {
            "question": q,
            "answer": (
                "Cevap oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": str(e),
            "sources": [],
            "metadata": {"error_type": "rag"},
        }
    except Exception as e:
        logger.error(f"Unexpected error in RAG pipeline: {e}", exc_info=True)
        if RAG_ERRORS_TOTAL:
            RAG_ERRORS_TOTAL.labels(type="unexpected").inc()
        return {
            "question": q,
            "answer": (
                "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin.\n\n"
                f"{MEDICAL_DISCLAIMER}"
            ),
            "error": f"Unexpected error: {e!s}",
            "sources": [],
            "metadata": {"error_type": "unexpected"},
        }


def cache_stats() -> dict[str, Any]:
    """Return simple cache statistics."""
    try:
        return {
            "enabled": settings.enable_cache,
            "size": len(_response_cache),
            "ttl_seconds": settings.cache_ttl_seconds,
        }
    except Exception:
        return {"enabled": False, "size": 0, "ttl_seconds": 0}


def flush_cache() -> int:
    """Flush in-memory response cache; returns number of entries removed."""
    try:
        n = len(_response_cache)
        _response_cache.clear()
        logger.info(f"🧹 Cache flushed: {n} entries removed")
        return n
    except Exception:
        return 0
