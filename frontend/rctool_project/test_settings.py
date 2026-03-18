"""
Django settings for the test suite.

Inherits everything from the main settings module and overrides only what the
test runner needs.  This file exists so that `pytest` works without any extra
environment variables — no SECRET_KEY, DEBUG, or ALLOWED_HOSTS needed.

Usage: set DJANGO_SETTINGS_MODULE=rctool_project.test_settings
This is already the default in frontend/pytest.ini.
"""
from rctool_project.settings import *  # noqa: F401, F403

# Provide safe test-only overrides — production keys are read from the
# environment (os.environ.get) in settings.py, so CI secrets will replace
# these naturally because CI sets the env vars before importing settings.
SECRET_KEY = (
    "pytest-insecure-local-only-key-do-not-use-in-production-7x!p24v9q"
)
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]
