# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Keeps Python from generating .pyc files and enables stdout/stderr flushing
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the package and its runtime dependencies
COPY pyproject.toml .
# Copy source so the editable install resolves the packages
COPY app/ app/
COPY quant/ quant/
COPY workers/ workers/
COPY slack_bot/ slack_bot/

RUN pip install --no-cache-dir -e .

# ── Stage 2: production API image ─────────────────────────────────────────────
FROM base AS api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
