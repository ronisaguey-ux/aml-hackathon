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


@app.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
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
