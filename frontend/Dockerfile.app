### BUILDER IMAGE ###
FROM python:3.13-slim AS builder

# set environment variables and /venv
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


### APP IMAGE ###
FROM python:3.13-slim

# set environment variables and /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"
COPY --from=builder /venv /venv

# Non-privileged user
RUN useradd -m rctool
USER rctool

# Copy app and set permissions for random UID OpenShift user
WORKDIR /app
COPY --chown=rctool:rctool . /app
RUN  chmod -R 777 /app

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check

CMD ["sh", "-c", "/app/start_app.sh"]
