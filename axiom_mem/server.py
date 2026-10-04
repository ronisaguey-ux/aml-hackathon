import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from axiom_mem import __version__, config
from axiom_mem.schemas import AddRequest, AddResponse, SearchRequest, SearchResponse
from axiom_mem.store.db import SQLiteStore
from axiom_mem.pipeline import MemoryPipeline

# Global singletons
store: SQLiteStore = None
pipeline: MemoryPipeline = None
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, pipeline
    # Initialize store and pipeline
    store = SQLiteStore(config.DB_PATH)
    pipeline = MemoryPipeline(store=store)
    # Apply data hygiene cleanup on startup
    cleaned = store.purge_older_than(days=config.DATA_RETENTION_DAYS)
    if cleaned > 0:
        print(f"[AxiomMem] Data hygiene: purged {cleaned} expired memories (> {config.DATA_RETENTION_DAYS} days).")
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="AxiomMem",
    version=__version__,
    description="High-Performance Agent Memory Server for AML Challenge Cycle 2",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# ★ OPTIONAL API-KEY AUTH (AML evaluation request declares an auth scheme + key).
#
# Gated on `AXIOM_API_KEY`: when the variable is unset the middleware is inert and
# the service behaves exactly as before, so enabling it can never break a running
# deployment that has not opted in. When set, every route except the liveness and
# introspection endpoints requires the key, accepted either as `Authorization:
# Bearer <key>` or `X-Api-Key: <key>` -- the two schemes the AML contract names.
# `/health` stays open so the platform's reachability check and the keep-alive
# monitor do not need credentials.
# ─────────────────────────────────────────────────────────────────────────────
_API_KEY = os.environ.get("AXIOM_API_KEY", "").strip()
_OPEN_PATHS = {"/", "/health", "/stats"}


@app.middleware("http")
async def _require_api_key(request: Request, call_next):
    if not _API_KEY or request.url.path in _OPEN_PATHS:
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    raw = request.headers.get("authorization", "") or request.headers.get("x-api-key", "")
    token = raw[7:].strip() if raw.lower().startswith("bearer ") else raw.strip()
    if token != _API_KEY:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "AxiomMem",
        "version": __version__,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "embedding_provider": config.EMBEDDING_PROVIDER,
    }


@app.get("/stats")
async def get_stats():
    total_memories = store.count_memories() if store else 0
    return {
        "total_memories": total_memories,
        "db_path": config.DB_PATH,
        "data_retention_days": config.DATA_RETENTION_DAYS,
    }


@app.post("/add", response_model=AddResponse, status_code=status.HTTP_200_OK)
@app.post("/v1/memories/add", response_model=AddResponse, status_code=status.HTTP_200_OK)
@app.post("/v1/add", response_model=AddResponse, status_code=status.HTTP_200_OK)
def add_memory(req: AddRequest):
    """
    POST /add endpoint conforming byte-for-byte to AML specification.
    Durably persists messages and ensures immediate search visibility.
    """
    try:
        response = pipeline.add(req)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process add request: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Optional add-status endpoint. The AML access request accepts an optional
# `add_status_endpoint` whose value must contain a `{task_id}` placeholder.
# Adds here are synchronous: the memory is durably written before the add
# response returns, so a request already in the `requests` table is by
# definition finished. This reports exactly that and nothing more -- a liveness
# convenience for a client that polls, not a second source of truth. The
# task_id is the `request_id` supplied on the add.
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/add/status/{task_id}")
@app.get("/v1/add/status/{task_id}")
@app.get("/v1/memories/add/status/{task_id}")
def add_status(task_id: str):
    if store is None:
        return {"task_id": task_id, "status": "unavailable", "synchronous": True}
    return {
        "task_id": task_id,
        "status": "completed" if store.is_request_seen(task_id) else "not_found",
        "synchronous": True,
    }


@app.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
@app.post("/v1/memories/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
@app.post("/v1/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_memory(req: SearchRequest):
    """
    POST /search endpoint conforming byte-for-byte to AML specification.
    Returns ranked raw observation memories for downstream answer models.
    """
    try:
        response = pipeline.search(req)
        return response
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": []}
        )
