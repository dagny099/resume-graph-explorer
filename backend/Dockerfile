FROM python:3.12-slim

# libmagic1 is required by python-magic (file type detection)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (gunicorn + eventlet are declared in the file)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application source
COPY resume_explorer/ ./resume_explorer/
COPY tools/ ./tools/

# Persistent session data lives here (ephemeral on free tier — acceptable for demo)
RUN mkdir -p data/sessions

ENV PORT=8000 \
    DATA_PATH=/app/data \
    SOCKETIO_ASYNC_MODE=eventlet

EXPOSE 8000

# Flask-SocketIO requires exactly 1 gunicorn worker in eventlet mode
CMD gunicorn \
    --worker-class eventlet \
    --workers 1 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --log-level info \
    "resume_explorer.api.app:create_app()"
