FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 PORT=10000 BRAINBOB_REQUIRE_AUTH=1 \
    BRAINBOB_DATA_DIR=/var/data/workspace BRAINBOB_CACHE_DIR=/var/data/cache \
    BRAINBOB_SSE_MAX_SECONDS=240
COPY backend/requirements-runtime.txt /app/backend/requirements-runtime.txt
RUN pip install --no-cache-dir -r backend/requirements-runtime.txt
COPY backend/brainbob /app/backend/brainbob
COPY backend/server.py /app/backend/server.py
COPY backend/fixtures/rusty_rod/org.json /app/backend/fixtures/rusty_rod/org.json
COPY scripts/run-live-backend.py scripts/seed-company.py /app/scripts/
COPY fixtures/company /app/fixtures/company
EXPOSE 10000
CMD ["python", "scripts/run-live-backend.py", "--skip-preflight"]
