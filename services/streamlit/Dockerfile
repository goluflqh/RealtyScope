FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir "uv==0.11.3"

COPY --from=app_deps pyproject.toml uv.lock README.md ./
COPY --from=app_src . ./src
RUN uv sync --frozen --no-dev --extra streamlit --no-editable

COPY --from=app_services . ./services

EXPOSE 8501
CMD ["streamlit", "run", "services/streamlit/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
