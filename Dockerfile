FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY benchmarks ./benchmarks
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN useradd --system --uid 10001 --create-home routemesh
COPY --from=builder --chown=10001:10001 /app /app
COPY --chown=10001:10001 configs ./configs
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/healthz', timeout=2)"
CMD ["uvicorn", "routemesh.proxy.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS demo-backend
HEALTHCHECK NONE
CMD ["uvicorn", "routemesh.demo_backends.app:app", "--host", "0.0.0.0"]
