### BUILDER IMAGE ###
FROM python:3.13-slim AS builder

# set environment variables and /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

# Install gcc and cleanup apt cache
RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc && \
    rm -rf /var/lib/apt/lists/*

# Setup venv and install requirements
COPY pyproject.toml ./
COPY rctool/ ./rctool
RUN python -m venv /venv && \
    pip install . --no-cache-dir


### APP IMAGE ###
FROM python:3.13-slim

# Envars and venv
COPY --from=builder /venv /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

# Copy app and set permissions (read all, write db.sqlite3)
WORKDIR /app
COPY . /app
RUN touch ./db.sqlite3 && \
    chmod 666 ./db.sqlite3

# Use a generic non-root user for security (OpenShift will override with a random UID)
USER nobody

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check --deploy

CMD ["sh", "-c", "/app/start_app.sh"]
