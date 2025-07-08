### Builder
FROM python:3.13-slim AS builder

# Envars
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

# Install gcc and cleanup apt cache
RUN apt-get update --no-install-recommends && \
    apt-get install -y gcc && \
    rm -rf /var/lib/apt/lists/*

# Setup venv and install requirements
COPY pyproject.toml ./
COPY rctool/ ./rctool
RUN python -m venv /venv && \
    pip install . --no-cache-dir


### Deployment
FROM python:3.13-slim

# Envars and venv
COPY --from=builder /venv /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

# Use a generic non-root user for security (OpenShift will override with a random UID)
USER nobody

# Copy app
WORKDIR /app
COPY . /app
RUN  chmod -R 777 /app

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check --deploy

CMD ["sh", "-c", "/app/start_app.sh"]
