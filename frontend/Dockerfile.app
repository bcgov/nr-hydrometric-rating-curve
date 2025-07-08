### BUILDER IMAGE ###
FROM python:3.13-slim AS builder

# set environment variables and /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

RUN apt-get update --no-install-recommends && \
    apt-get install -y gcc 

# set up venv
RUN python -m venv /venv

# install requirements
COPY pyproject.toml ./
COPY README.md ./
COPY rctool/ ./rctool
RUN pip install . --no-cache-dir

### APP IMAGE ###
FROM python:3.13-slim

# set environment variables and /venv
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

# Non-privileged user
RUN useradd -m rctool
USER rctool

# Copy app and /venv
WORKDIR /app
COPY --chown=rctool:rctool . /app
COPY --from=builder /venv /venv

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check

CMD ["sh", "-c", "/app/start_app.sh"]
