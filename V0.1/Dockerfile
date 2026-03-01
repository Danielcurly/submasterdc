# Stage 1: Build the Next.js frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend source and dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
# Build the static export
RUN npm run build
# The exported files will be in /app/frontend/out


# Stage 2: Build the Python backend and final image
FROM python:3.11-slim AS final
WORKDIR /app

# Install system dependencies
# ffmpeg is required for Whisper and embedded subtitle extraction
# gosu is required to step down from root to PGID/PUID
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . /app/
# Remove frontend source if copied over, we only need the build
RUN rm -rf /app/frontend

# Copy the static frontend build into the container
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Ensure script is executable
RUN chmod +x /app/entrypoint.sh

# Provide a writable cache directory for HuggingFace/Whisper
ENV HF_HOME=/app/data/cache
ENV XDG_CACHE_HOME=/app/data/cache

# Expose the single FastAPI port
EXPOSE 8000

# Volume points
VOLUME ["/app/data", "/media"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
