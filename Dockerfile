FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY src/ ./src/

EXPOSE 8000
WORKDIR /app/src
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "300", "--workers", "2", "main:app"]