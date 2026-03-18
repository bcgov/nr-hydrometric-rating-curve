"""
Root conftest for the frontend test suite.

Sets required Django environment variables before pytest-django initialises
Django, so that `pytest` works without any extra env vars — locally, in Docker,
and in CI.  CI values (SECRET_KEY, ALLOWED_HOSTS, etc.) are set as explicit
env vars by the GitHub Actions workflow and will take precedence over these
defaults via os.environ.setdefault().
"""
import os

# Only set defaults — don't override values already in the environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rctool_project.settings")
os.environ.setdefault("SECRET_KEY", "pytest-insecure-local-only-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1")
