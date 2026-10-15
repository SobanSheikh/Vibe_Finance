FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed-cache \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir . \
    && python -c "from fastembed import TextEmbedding; model = TextEmbedding(model_name='BAAI/bge-small-en-v1.5'); next(model.query_embed('deployment readiness'))" \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /opt/fastembed-cache

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
