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

# Copy app and loosen permissions
COPY . /app
COPY start_app.sh /app/start_app.sh
COPY --from=builder /venv /venv
RUN  chmod -R 777 /app

# create and switch to the app user
WORKDIR /app
RUN useradd -m rctool
USER rctool
COPY --chown=rctool:rctool . /app

# healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check

CMD ["sh", "-c", "/app/start_app.sh"]
