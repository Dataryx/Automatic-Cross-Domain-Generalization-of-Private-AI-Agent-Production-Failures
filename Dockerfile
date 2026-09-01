FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY services ./services
COPY schemas ./schemas
COPY eval ./eval
COPY sim ./sim

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000 8001 8002
