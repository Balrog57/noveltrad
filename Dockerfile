# NovelTrad multi-stage Dockerfile (SDD 6.2).
# Base image pinned by digest: python:3.12.13-slim-bookworm.
# Build stage: installs only uv==0.11.33, runs `uv sync --locked --no-dev`.
# Final stage: copies the environment and sources without compiler or cache.
# Runs as unprivileged user/group 10001:10001; only /data and the necessary
# system temporaries are writable.

ARG SOURCE_COMMIT=0000000000000000000000000000000000000000

FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /uvx /bin/

WORKDIR /build
COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./
RUN uv sync --locked --no-dev

FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2

ARG SOURCE_COMMIT
ENV SOURCE_COMMIT=${SOURCE_COMMIT} \
    PATH="/app/.venv/bin:$PATH" \
    NOVELTRAD_DATA_DIR=/data \
    NOVELTRAD_BIND_ADDRESS=127.0.0.1 \
    NOVELTRAD_PORT=8501 \
    NOVELTRAD_LOG_LEVEL=INFO

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src/ ./src/

RUN mkdir -p /data && \
    printf 'SOURCE_COMMIT = %s\n' "'${SOURCE_COMMIT}'" > src/noveltrad/core/_build_env.py && \
    chown -R 10001:10001 /data && \
    chmod -R a+rX /app

USER 10001:10001

EXPOSE 8501

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)" || exit 1

ENTRYPOINT ["python", "-m", "noveltrad.app.launcher"]
