# ==============================================================================
# Ola Domain Support Agent — Local Container Execution (Optional)
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================

FROM python:3.11-slim

# 1. Set environment variables
ENV MOCK_LLM=true \
    CREWAI_DISABLE_TELEMETRY=true \
    OTEL_SDK_DISABLED=true \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PORT=8000 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# 2. Install minimal system packages for compiling C extensions & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy requirements.txt and prefetch script
COPY requirements.txt .
COPY scripts/prefetch_models.py scripts/prefetch_models.py

# 4. Install CPU-only PyTorch first, then application requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 5. Pre-download the embedding model at build time (non-fatal if offline)
RUN python scripts/prefetch_models.py || true

# 6. Copy the application source code
COPY . .

# 7. Create writable application runtime directories and ensure full permissions
RUN mkdir -p /app/chroma_store /app/.chroma_db /app/logs /app/data /app/transcripts && \
    chmod -R 777 /app

# 8. Expose application port
EXPOSE 8000

# 9. Start uvicorn bound to port 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
