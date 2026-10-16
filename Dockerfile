# ==============================================================================
# Ola Domain Support Agent — Hugging Face Spaces Dockerfile Specification
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================

FROM python:3.11-slim

# 1. Create a non-root user with UID 1000 (named "user")
RUN useradd -m -u 1000 user

# 2. Set environment variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    MOCK_LLM=true \
    CREWAI_DISABLE_TELEMETRY=true \
    OTEL_SDK_DISABLED=true \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# 3. Install build tools for compiling any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Switch to non-root user
USER user

# 5. Copy requirements.txt first for Docker layer caching
COPY --chown=user requirements.txt .

# 6. Install CPU-only PyTorch and application dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 7. Pre-download the SentenceTransformer model at build time for offline execution
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 8. Copy the rest of the project with non-root ownership
COPY --chown=user . .

# 9. Expose port and start uvicorn
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
