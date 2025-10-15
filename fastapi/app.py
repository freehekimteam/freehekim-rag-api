from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from config import Settings
from rag.pipeline import retrieve_answer

app = FastAPI(title="HakanCloud RAG API")
settings = Settings()

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.env}

@app.get("/ready")
def ready():
    """
    Readiness probe - checks if API can serve traffic
    Returns 200 if Qdrant is reachable, 503 otherwise
    """
    from rag.client_qdrant import _qdrant
    from fastapi.responses import JSONResponse

    try:
        # Try to get collections from Qdrant
        collections = _qdrant.get_collections()
        collection_names = [col.name for col in collections.collections]

        return {
            "ready": True,
            "qdrant": {
                "connected": True,
                "collections": collection_names,
                "count": len(collection_names)
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "qdrant": {
                    "connected": False,
                    "error": str(e)
                }
            }
        )

@app.post("/rag/query")
def rag_query(payload: dict):
    question = payload.get("q", "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "missing 'q'"})
    return retrieve_answer(question)
