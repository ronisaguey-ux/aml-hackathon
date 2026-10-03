#!/usr/bin/env python3
import argparse
import sys
import uvicorn
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from axiom_mem import config


def main():
    parser = argparse.ArgumentParser(description="Start AxiomMem HTTP Service for AML Challenge")
    parser.add_argument("--host", default=config.HOST, help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=config.PORT, help="Port to bind to (default: 8000)")
    parser.add_argument("--workers", type=int, default=config.WORKERS, help="Number of worker processes")
    parser.add_argument("--db-path", default=config.DB_PATH, help="Path to SQLite DB")
    parser.add_argument("--embedding-provider", choices=["fastembed", "openai", "hash"], default=config.EMBEDDING_PROVIDER)
    args = parser.parse_args()

    import os
    os.environ["AXIOM_DB_PATH"] = args.db_path
    os.environ["AXIOM_EMBEDDING_PROVIDER"] = args.embedding_provider

    print("=" * 60)
    print("🚀 Starting AxiomMem Server")
    print(f"📍 Address: http://{args.host}:{args.port}")
    print(f"💾 Storage: {args.db_path}")
    print(f"🧠 Embedder: {args.embedding_provider}")
    print("=" * 60)

    uvicorn.run(
        "axiom_mem.server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info"
    )


if __name__ == "__main__":
    main()
