# syntax=docker/dockerfile:1

# ---- Builder: install Python dependencies into a venv -----------------
FROM python:3.12-slim AS builder

WORKDIR /build

# git is required at runtime by app.services.git_service (real `git` CLI
# subprocess calls), so it's installed in both stages.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- Runtime: slim image with just the venv + app code ----------------
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY app ./app

# Data, workspaces (sandbox execution + git repos) need to be writable and
# should be mounted as a volume in production so version history and git
# repos survive container restarts -- see docker-compose.yml.
RUN mkdir -p /app/data /app/workspaces && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
