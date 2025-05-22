### BUILDER IMAGE ###
# syntax=docker/dockerfile:1
FROM python:3.13-slim@sha256:56a11364ffe0fee3bd60af6d6d5209eba8a99c2c16dc4c7c5861dc06261503cc AS BUILDER

# set environment variables
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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
FROM python:3.13-slim@sha256:56a11364ffe0fee3bd60af6d6d5209eba8a99c2c16dc4c7c5861dc06261503cc AS APP
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/venv/bin:$PATH"
COPY . /app
COPY start_app.sh /app/start_app.sh
# create and switch to the app user
RUN  chmod -R 777 /app
RUN useradd -m rctool
USER rctool


# copy project
COPY --from=BUILDER /venv /venv

# healthcheck
HEALTHCHECK --interval=60s --timeout=10s \
    CMD python manage.py check

CMD ["sh", "-c", "/app/start_app.sh"]
