"""
FreeHekim RAG API

FastAPI application providing Retrieval-Augmented Generation endpoints
for medical content search and question-answering.
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator

from config import Settings
from rag.pipeline import retrieve_answer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Align logger level with settings
try:
    logging.getLogger().setLevel(getattr(logging, settings.log_level, logging.INFO))
except Exception:
    pass

# FastAPI app with metadata
app = FastAPI(
    title="FreeHekim RAG API",
    description="Retrieval-Augmented Generation API for FreeHekim medical content",
    version="1.0.0",
    docs_url="/docs" if settings.env != "production" else None,  # Disable in prod
    redoc_url="/redoc" if settings.env != "production" else None,
)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ============================================================================
# Global Exception Handlers (consistent error shape)
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 400 with a consistent error field for validation issues."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid request",
            "details": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure HTTPExceptions also return an error field instead of detail."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP error",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler to avoid leaking internals and keep shape consistent."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error. Please try again later.",
        },
    )


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status", examples=["ok"])
    env: str = Field(..., description="Environment", examples=["staging", "production"])


class ReadinessResponse(BaseModel):
    """Readiness check response model"""
    ready: bool = Field(..., description="Service readiness status")
    qdrant: dict[str, Any] = Field(..., description="Qdrant connection status")


class RAGQueryRequest(BaseModel):
    """RAG query request model"""
    q: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="User question (3-500 characters)",
        examples=["Diyabet belirtileri nelerdir?"]
    )

    @field_validator("q")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean question text"""
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) < 3:
            raise ValueError("Question too short (minimum 3 characters)")
        return v


class RAGQueryResponse(BaseModel):
    """RAG query response model"""
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer with medical disclaimer")
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Source documents used for answer generation"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline metadata (tokens, model, etc.)"
    )
    error: str | None = Field(None, description="Error message if query failed")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
def health() -> HealthResponse:
    """
    Service health check.

    Returns basic service status and environment information.
    Always returns 200 OK if the service is running.
    """
    return HealthResponse(status="ok", env=settings.env)


@app.get(
    "/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Readiness probe",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service not ready (Qdrant unreachable)"}
    }
)
def ready() -> ReadinessResponse | JSONResponse:
    """
    Readiness probe for Kubernetes/Docker health checks.

    Checks if the API can serve traffic by verifying Qdrant connection.

    Returns:
        - 200 OK if Qdrant is reachable
        - 503 Service Unavailable if Qdrant is down
    """
    try:
        # Lazy import to avoid connection at import time
        from rag.client_qdrant import get_qdrant_client

        # Try to get collections from Qdrant
        client = get_qdrant_client()
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]

        logger.info(f"Readiness check passed. Collections: {collection_names}")

        return ReadinessResponse(
            ready=True,
            qdrant={
                "connected": True,
                "collections": collection_names,
                "count": len(collection_names)
            }
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "qdrant": {
                    "connected": False,
                    "error": str(e)
                }
            }
        )


@app.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    tags=["RAG"],
    summary="Query medical knowledge base",
    responses={
        200: {"description": "Successful answer generation"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """
    Query the RAG pipeline to get AI-generated answers from medical knowledge base.

    **Process:**
    1. Embed user question using OpenAI embeddings
    2. Search internal (FreeHekim) and external collections in Qdrant
    3. Merge results using Reciprocal-Rank Fusion
    4. Generate answer with GPT-4
    5. Add medical disclaimer

    **Args:**
        request: RAGQueryRequest with user question

    **Returns:**
        RAGQueryResponse with answer, sources, and metadata

    **Example:**
        ```json
        {
          "q": "Metformin yan etkileri nelerdir?"
        }
        ```
    """
    try:
        logger.info(f"Received RAG query: {request.q[:50]}...")
        result = retrieve_answer(request.q)
        return RAGQueryResponse(**result)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again later."
        )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event() -> None:
    """Log startup information"""
    logger.info(f"🚀 FreeHekim RAG API starting in {settings.env} mode")
    logger.info(f"📊 Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    logger.info(f"🤖 Embedding provider: {settings.embed_provider}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown"""
    logger.info("🛑 FreeHekim RAG API shutting down")
