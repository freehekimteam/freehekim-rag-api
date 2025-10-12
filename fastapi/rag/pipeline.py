"""
HakanCloud RAG Pipeline
Retrieval-Augmented Generation with reciprocal-rank fusion
"""
import logging
from typing import List, Dict, Any
from openai import OpenAI
from .client_qdrant import search, INTERNAL, EXTERNAL
from .embeddings import embed
from config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# OpenAI client for LLM generation
_llm_client = None

def _get_llm_client() -> OpenAI:
    """Lazy initialization of OpenAI client for LLM"""
    global _llm_client
    if _llm_client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        _llm_client = OpenAI(api_key=settings.openai_api_key)
    return _llm_client


def reciprocal_rank_fusion(
    internal_results: List[Any],
    external_results: List[Any],
    k: int = 60
) -> List[tuple[Any, float, str]]:
    """
    Combine results from multiple sources using Reciprocal Rank Fusion.

    RRF formula: score(doc) = Σ 1/(k + rank_i)
    where k=60 is a constant (typical value)

    Args:
        internal_results: Search results from internal collection
        external_results: Search results from external collection
        k: RRF constant (default 60)

    Returns:
        List of (result, score, source) tuples sorted by fused score
    """
    scores = {}

    # Score internal results
    for rank, result in enumerate(internal_results, start=1):
        point_id = result.id
        rrf_score = 1.0 / (k + rank)
        if point_id not in scores:
            scores[point_id] = {
                'result': result,
                'score': 0.0,
                'source': 'internal'
            }
        scores[point_id]['score'] += rrf_score

    # Score external results
    for rank, result in enumerate(external_results, start=1):
        point_id = result.id
        rrf_score = 1.0 / (k + rank)
        if point_id not in scores:
            scores[point_id] = {
                'result': result,
                'score': 0.0,
                'source': 'external'
            }
        else:
            scores[point_id]['source'] = 'both'
        scores[point_id]['score'] += rrf_score

    # Sort by fused score
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x['score'],
        reverse=True
    )

    return [(r['result'], r['score'], r['source']) for r in sorted_results]


def generate_answer(question: str, context_chunks: List[Dict]) -> Dict[str, Any]:
    """
    Generate answer using GPT with retrieved context.

    Args:
        question: User's question
        context_chunks: Retrieved text chunks from Qdrant

    Returns:
        Dict with answer and metadata
    """
    try:
        client = _get_llm_client()

        # Build context from chunks
        context_text = "\n\n".join([
            f"[Kaynak {i+1}]: {chunk['text'][:500]}..."
            for i, chunk in enumerate(context_chunks[:5])  # Top 5 chunks
        ])

        # System prompt with medical disclaimer
        system_prompt = """Sen FreeHekim'in AI asistanısın. Sağlık konularında bilgilendirme yapıyorsun.

ÖNEMLİ KURALLARI:
1. Verilen KAYNAK bilgilerini kullanarak cevap ver
2. Kaynak göster: [Kaynak 1], [Kaynak 2] şeklinde
3. MUTLAKA tıbbi sorumluluk reddi ekle
4. Teşhis veya tedavi önerme, sadece bilgilendir
5. Türkçe ve anlaşılır cevap ver

SORUMLULUK REDDİ ŞABLONU:
"⚠️ Bu bilgi tıbbi tavsiye değildir. Sağlık kararlarınız için mutlaka hekiminize danışın."
"""

        # User prompt
        user_prompt = f"""SORU: {question}

KAYNAK BİLGİLER:
{context_text}

Yukarıdaki kaynaklara dayanarak soruyu cevapla. Kaynak numaralarını belirt ve tıbbi sorumluluk reddi ekle."""

        # Call GPT-4
        response = client.chat.completions.create(
            model="gpt-4",  # or gpt-4-turbo, gpt-3.5-turbo for cost savings
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Low temperature for factual responses
            max_tokens=800
        )

        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        logger.info(f"✅ Generated answer (tokens: {tokens_used})")

        return {
            "answer": answer,
            "tokens_used": tokens_used,
            "model": "gpt-4"
        }

    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        return {
            "answer": "Üzgünüm, şu anda cevap oluşturamıyorum. Lütfen tekrar deneyin.",
            "error": str(e)
        }


def retrieve_answer(q: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Main RAG pipeline: Retrieve + Rank + Generate

    Args:
        q: User question
        top_k: Number of chunks to retrieve from each collection

    Returns:
        Dict with answer, sources, and metadata
    """
    try:
        # Step 1: Embed query
        logger.info(f"🔍 Processing query: {q}")
        query_vector = embed(q)

        # Step 2: Search both collections
        internal_results = search(query_vector, top_k, INTERNAL)
        external_results = search(query_vector, top_k, EXTERNAL)

        logger.info(f"📊 Retrieved: {len(internal_results)} internal, {len(external_results)} external")

        # Step 3: Reciprocal-rank fusion
        fused_results = reciprocal_rank_fusion(internal_results, external_results)

        # Step 4: Extract context chunks
        context_chunks = []
        for result, score, source in fused_results[:top_k]:
            context_chunks.append({
                "text": result.payload.get("text", ""),
                "source": source,
                "score": score,
                "metadata": result.payload.get("metadata", {})
            })

        # Step 5: Generate answer with LLM
        generation_result = generate_answer(q, context_chunks)

        # Step 6: Format response
        return {
            "question": q,
            "answer": generation_result.get("answer"),
            "sources": [
                {
                    "text": chunk["text"][:200] + "...",
                    "source": chunk["source"],
                    "score": round(chunk["score"], 4)
                }
                for chunk in context_chunks[:3]  # Top 3 sources
            ],
            "metadata": {
                "internal_hits": len(internal_results),
                "external_hits": len(external_results),
                "fused_results": len(fused_results),
                "tokens_used": generation_result.get("tokens_used", 0),
                "model": generation_result.get("model", "unknown")
            }
        }

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        return {
            "question": q,
            "answer": "Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            "error": str(e),
            "sources": []
        }
