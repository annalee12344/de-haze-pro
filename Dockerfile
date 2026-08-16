# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install

COPY frontend/ ./
RUN npm run build

RUN test -d dist || (echo "Build failed: dist not found" && exit 1)


# Stage 2: Backend
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2

COPY api/requirements.txt /app/api/requirements.txt

# Install CPU-only PyTorch explicitly
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.13.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install normal dependencies from PyPI
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/api/requirements.txt

COPY . .

COPY --from=frontend-builder /app/frontend/dist /app/static

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]