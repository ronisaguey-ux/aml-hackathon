# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    AXIOM_DATA_DIR=/app/data \
    AXIOM_DATA_RETENTION_DAYS=30 \
    AXIOM_HOST=0.0.0.0 \
    AXIOM_PORT=8000

# Install system dependencies (including SQLite3 with FTS5 and curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml .

# Install dependencies using pip
RUN pip install --no-cache-dir .

# Copy application source code and scripts
COPY axiom_mem/ /app/axiom_mem/
COPY scripts/ /app/scripts/
COPY deploy/ /app/deploy/

# Create persistent data volume directory
RUN mkdir -p /app/data

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["python", "scripts/run_server.py", "--host", "0.0.0.0", "--port", "8000"]
