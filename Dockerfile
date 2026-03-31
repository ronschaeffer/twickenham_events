# Stage 1: Builder — install Poetry, export requirements, build wheel
FROM python:3.11-slim AS builder

WORKDIR /build

# Install Poetry and export plugin
RUN pip install --no-cache-dir poetry poetry-plugin-export

# Copy dependency files first (cache-friendly layer)
COPY pyproject.toml poetry.lock ./

# Export requirements (main + ai extras, no dev)
RUN poetry export --with ai --without dev -f requirements.txt -o requirements.txt

# Copy source and build the wheel
COPY src/ src/
COPY README.md ./
RUN poetry build -f wheel


# Stage 2: Runtime — lean image with only production deps
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies from exported requirements
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

# Install the built wheel
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy config example and Docker-optimized default config
COPY config/config.yaml.example /app/config/config.yaml.example
COPY config/config.docker.yaml /app/config/config.yaml

# Create data and output directories
RUN mkdir -p /app/data /app/output

# Expose web server port
EXPOSE 47476

# Health check: try web server /health endpoint, fall back to process check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:47476/health')" \
  || python -c "import os, signal; os.kill(1, 0)" || exit 1

# Default: run the long-running service (requires MQTT_ENABLED=true)
ENTRYPOINT ["twick-events"]
CMD ["service"]
