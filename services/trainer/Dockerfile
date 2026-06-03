FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir "uv==0.11.3"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra data --extra ml --no-editable

CMD ["python", \
    "-m", \
    "realtyscope.ml.train", \
    "--feature-version", \
    "ml_features_v2_non_leaky", \
    "--output-dir", \
    "data/processed/models/phase5", \
    "--mlflow-tracking-uri", \
    "http://mlflow:5000", \
    "--mlflow-registered-model-name", \
    "realtyscope-price-model", \
    "--json"]
