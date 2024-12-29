FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ADD * /

EXPOSE 8000
WORKDIR /
RUN uv sync --frozen
CMD uv run gunicorn app:app