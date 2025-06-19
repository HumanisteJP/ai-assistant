# syntax=docker/dockerfile:1.5
FROM python:3.11-slim AS base

# ---------- system dependencies ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# ---------- python dependencies ----------
WORKDIR /app
COPY yata-agent/pyproject.toml yata-agent/uv.lock ./
RUN pip install -U uv && \
    uv pip install -r pyproject.toml --system && \
    rm -rf ~/.cache/pip

# ---------- application code ----------
COPY yata-agent /app

# ---------- optional scripts ----------
COPY scripts /scripts
ENV PATH="/scripts:$PATH"
ENV PYTHONPATH="/app/src"

# ---------- runtime ----------
EXPOSE 8000
CMD ["python", "src/main.py"]