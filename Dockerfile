FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/runtime/followdesk.db

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir .

RUN mkdir -p /app/runtime && chown -R app:app /app

# Railway attaches persistent volumes after the image is built. Those mounts
# start as root-owned storage, so the process needs permission to create the
# SQLite database inside /app/runtime.

EXPOSE 8000
CMD ["sh", "-c", "uvicorn followdesk.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
