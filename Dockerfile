# ==============================================================================
# Multi-stage Dockerfile for Hugging Face Spaces (Docker SDK)
# Stage 1: Build the React + TypeScript frontend
# Stage 2: Run FastAPI backend and serve static frontend assets
# ==============================================================================

# Stage 1: Frontend Build
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Backend & Full-Stack Server
FROM python:3.11-slim

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install Python backend dependencies
COPY --chown=user backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy Backend Code
COPY --chown=user backend/ .

# Copy compiled frontend build into frontend_dist
COPY --chown=user --from=frontend-builder /build/dist ./frontend_dist

# Hugging Face Spaces expects traffic on port 7860
EXPOSE 7860

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

# ==============================================================================
# FILE SUMMARY: Dockerfile
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# Multi-stage containerization blueprint configured specifically for Hugging Face Spaces:
#   1. Stage 1 (frontend-builder): Compiles Vite React TypeScript bundle into production dist.
#   2. Stage 2 (python-runtime): Installs dependencies for FastAPI and Pandas, provisions
#      user 1000 per Hugging Face Spaces specification, copies backend source and static dist.
#   3. Exposes port 7860 and launches Uvicorn ASGI server.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Mounts compiled frontend dist via 'backend/main.py'.
# - Configured by repository metadata in 'README.md'.
# ==============================================================================
