from .client_qdrant import search, INTERNAL, EXTERNAL
from .embeddings import embed

def retrieve_answer(q: str):
    v = embed(q)
    a = search(v, 3, INTERNAL)
    b = search(v, 3, EXTERNAL)
    # TODO: reciprocal-rank fusion + LLM call
    return {
        "q": q,
        "internal_hits": len(a),
        "external_hits": len(b),
    }
