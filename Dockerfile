# ==========================================
# Stage 1: Build dependencies
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system utilities needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runtime image
# ==========================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Copy virtual environment and installed packages from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code and files
COPY app/ ./app
COPY scripts/ ./scripts
COPY data/ ./data
COPY requirements.txt .

# Limit PyTorch CPU threads and workers to minimize memory footprint under 512MB RAM
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

# Pre-compile the FAISS dense search index during image build
# This avoids doing it on startup or needing network access at runtime
ENV GOOGLE_API_KEY="dummy_key_for_build"
RUN python scripts/build_index.py

# Create a non-privileged system user for execution (Security Hardening)
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Start production uvicorn server with 1 worker to save memory
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
