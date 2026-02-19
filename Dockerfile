# Lightweight build for Render (512MB limit)
FROM python:3.11-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && find /usr/local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true \
    && find /usr/local -type d -name tests -exec rm -rf {} + 2>/dev/null; true \
    && find /usr/local -type d -name test -exec rm -rf {} + 2>/dev/null; true \
    && rm -rf /root/.cache/pip

# Copy only application code (not tests, docs, etc.)
COPY ./app ./app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port (Render uses PORT env var, default to 10000)
EXPOSE 10000

# Set default port for Render
ENV PORT=10000

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 10000)}/health')" || exit 1

# Run with minimal workers - use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --limit-max-requests 1000
