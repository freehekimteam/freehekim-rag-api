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
    # later: check Qdrant connectivity
    return {"ready": True}

@app.post("/rag/query")
def rag_query(payload: dict):
    question = payload.get("q", "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "missing 'q'"})
    return retrieve_answer(question)
