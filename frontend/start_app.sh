#!/bin/sh

echo "---> starting application ..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput
gunicorn --bind=:"${WEB_PORT_INTERNAL}" --workers="${GUNICORN_WORKERS}" --log-level=info --limit-request-line="${GUNICORN_LIMIT_REQ_LINE}" --limit-request-field_size="${GUNICORN_LIMIT_REQ_FIELDSIZE}" --timeout="${GUNICORN_TIMEOUT}" rctool_project.wsgi:application
