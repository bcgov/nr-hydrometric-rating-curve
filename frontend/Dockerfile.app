### BUILDER IMAGE ###
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder

# set environment variables
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# use python venv to copy to the app image later
ENV PATH="/venv/bin:$PATH"

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
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PATH="/venv/bin:$PATH"
COPY --from=builder /venv /venv

# create and switch to the app user
WORKDIR /app
RUN useradd -m rctool
USER rctool
COPY --chown=rctool:rctool . /app

# healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check

CMD ["sh", "-c", "/app/start_app.sh"]
