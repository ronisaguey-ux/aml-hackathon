FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml README.md ./
COPY axiom_mem/ axiom_mem/
COPY scripts/ scripts/

# Install dependencies and package
RUN uv pip install --system -e .

# Environment variables
ENV AXIOM_HOST=0.0.0.0
ENV AXIOM_PORT=8000
ENV AXIOM_WORKERS=1
ENV AXIOM_DB_PATH=/app/data/axiom_mem.db
ENV AXIOM_EMBEDDING_PROVIDER=fastembed
ENV AXIOM_DATA_RETENTION_DAYS=30

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["python3", "scripts/run_server.py"]
