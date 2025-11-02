"""
FreeHekim RAG API

FastAPI application providing Retrieval-Augmented Generation endpoints
for medical content search and question-answering.
"""

import logging
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from config import Settings
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from rag.pipeline import retrieve_answer

# Configure logging (plain or JSON)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()


def _configure_logging() -> None:
    try:
        logging.getLogger().setLevel(getattr(logging, settings.log_level, logging.INFO))
        if settings.log_json:
            try:
                from pythonjsonlogger import jsonlogger
            except Exception:
                logger.warning(
                    "JSON logging requested but python-json-logger not installed; using plain logs"
                )
                return
            root = logging.getLogger()
            for h in list(root.handlers):
                root.removeHandler(h)
            handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            handler.setFormatter(formatter)
            root.addHandler(handler)
    except Exception:
        logger.debug("Logging configuration could not be fully applied", exc_info=True)


_configure_logging()


# FastAPI app with metadata
@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Startup
    logger.info(f"🚀 FreeHekim RAG API starting in {settings.env} mode")
    logger.info(f"📊 Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    logger.info(f"🤖 Embedding provider: {settings.embed_provider}")
    try:
        yield
    finally:
        # Shutdown
        logger.info("🛑 FreeHekim RAG API shutting down")


app = FastAPI(
    title="FreeHekim RAG API",
    description="Retrieval-Augmented Generation API for FreeHekim medical content",
    version="1.0.0",
    docs_url="/docs" if settings.env != "production" else None,  # Disable in prod
    redoc_url="/redoc" if settings.env != "production" else None,
    lifespan=_lifespan,
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
# Basic Protections & Observability Middlewares
# ============================================================================


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request id to each request and response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.info(
                f"{request.method} {request.url.path} - {duration:.1f}ms - X-Request-ID={req_id}"
            )
        response.headers["X-Request-ID"] = req_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with Content-Length exceeding configured limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        try:
            content_length = request.headers.get("content-length")
            if content_length is not None and int(content_length) > self.max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"error": "Request body too large"},
                )
        except Exception:
            # Fail-open for safety; downstream may still reject
            logger.debug("Could not parse Content-Length header", exc_info=True)
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Very simple per-IP sliding window rate limiter."""

    def __init__(self, app: ASGIApp, requests_per_minute: int) -> None:
        super().__init__(app)
        self.limit = requests_per_minute
        self.window_seconds = 60
        self.state: dict[str, deque] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        # Prefer Cloudflare's connecting IP if present
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        # Fallback to first X-Forwarded-For entry
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        now = time.monotonic()
        ip = self._client_ip(request)

        q = self.state[ip]
        # purge old
        while q and now - q[0] > self.window_seconds:
            q.popleft()

        if len(q) >= self.limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"},
            )

        q.append(now)
        return await call_next(request)


# Install middlewares
app.add_middleware(RequestIDMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_size_bytes)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

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
        examples=["Diyabet belirtileri nelerdir?"],
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
        default_factory=list, description="Source documents used for answer generation"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Pipeline metadata (tokens, model, etc.)"
    )
    error: str | None = Field(None, description="Error message if query failed")


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"], summary="Health check endpoint")
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
        503: {"description": "Service not ready (Qdrant unreachable)"},
    },
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
                "count": len(collection_names),
            },
        )
    except Exception:
        # Log full details server-side; avoid exposing internals to clients
        logger.error("Readiness check failed", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "qdrant": {
                    "connected": False,
                    # Do not expose internal exception details
                    "error": "unavailable",
                },
            },
        )


@app.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    tags=["RAG"],
    summary="Query medical knowledge base",
    responses={
        200: {"description": "Successful answer generation"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
def rag_query(request: RAGQueryRequest, raw: Request) -> RAGQueryResponse:
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
        # Optional API key check
        if settings.require_api_key:
            provided = raw.headers.get("x-api-key") or raw.headers.get("X-Api-Key")
            expected = settings.get_api_key()
            if not expected or not provided or provided != expected:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        logger.info(f"Received RAG query: {request.q[:50]}...")
        result = retrieve_answer(request.q)
        return RAGQueryResponse(**result)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again later.",
        ) from e


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

# Lifespan handler replaces deprecated on_event startup/shutdown
