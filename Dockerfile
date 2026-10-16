# ==============================================================================
# Ola Domain Support Agent — Render Web Service Dockerfile Specification
# Track: Business Operations / Customer Support (Ola)
# Runtime: Docker on Render Free Tier (512 MB RAM, 0.1 CPU)
# ==============================================================================

FROM python:3.11-slim

# 1. Set environment variables
ENV MOCK_LLM=true \
    CREWAI_DISABLE_TELEMETRY=true \
    OTEL_SDK_DISABLED=true \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

# 2. Install minimal system packages for compiling C extensions & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy requirements.txt first for Docker layer caching
COPY requirements.txt .

# 4. Install CPU-only PyTorch first, then application requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 5. Pre-download the SentenceTransformer model at build time for instant offline startup
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 6. Copy the application source code
COPY . .

# 7. Create writable application runtime directories and ensure full permissions
RUN mkdir -p /app/chroma_store /app/.chroma_db /app/logs /app/data /app/transcripts && \
    chmod -R 777 /app

# 8. Expose Render default port (10000)
EXPOSE 10000

# 9. Start uvicorn dynamically bound to Render's injected $PORT (fallback to 10000)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
