FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY services ./services
COPY schemas ./schemas
COPY tools/evaluation ./tools/evaluation
COPY tools/feasibility ./tools/feasibility

RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app

EXPOSE 8000 8001 8002 8010 8020 8021 8022
