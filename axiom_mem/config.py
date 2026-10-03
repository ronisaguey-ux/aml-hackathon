import os
from pathlib import Path

# Paths
DEFAULT_DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.getenv("AXIOM_DB_PATH", str(DEFAULT_DATA_DIR / "axiom_mem.db"))

# Embedding Provider Configuration
# Supported: "fastembed" (local ONNX, zero external network), "openai" (text-embedding-v4), "hash" (offline fallback)
EMBEDDING_PROVIDER = os.getenv("AXIOM_EMBEDDING_PROVIDER", "fastembed").lower()
FASTEMBED_MODEL = os.getenv("AXIOM_FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
TEXT_EMBEDDING_MODEL = os.getenv("TEXT_EMBEDDING_MODEL", "text-embedding-v4")

# Server Config
HOST = os.getenv("AXIOM_HOST", "0.0.0.0")
PORT = int(os.getenv("AXIOM_PORT", "8000"))
WORKERS = int(os.getenv("AXIOM_WORKERS", "1"))

# Ranking & Retention Hyperparameters
RRF_K = int(os.getenv("AXIOM_RRF_K", "60"))
BM25_WEIGHT = float(os.getenv("AXIOM_BM25_WEIGHT", "1.0"))
DENSE_WEIGHT = float(os.getenv("AXIOM_DENSE_WEIGHT", "1.0"))

# Execution & Column G boost
EXECUTION_BOOST = float(os.getenv("AXIOM_EXECUTION_BOOST", "1.35"))
TEMPORAL_RECENCY_BOOST = float(os.getenv("AXIOM_TEMPORAL_BOOST", "1.25"))
OPTIONS_DISCRIMINATOR_BOOST = float(os.getenv("AXIOM_OPTIONS_BOOST", "1.30"))
COMPOSITION_EXPANSION_BOOST = float(os.getenv("AXIOM_COMPOSITION_BOOST", "1.20"))

# Operational Hygiene
DATA_RETENTION_DAYS = int(os.getenv("AXIOM_DATA_RETENTION_DAYS", "30"))
