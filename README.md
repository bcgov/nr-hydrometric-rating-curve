<!-- PROJECT SHIELDS -->

[![Analysis](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/analysis.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/analysis.yml)
[![Merge](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/merge.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/merge.yml)
[![Scheduled](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/scheduled.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/scheduled.yml)

[![Issues](https://img.shields.io/github/issues/bcgov/nr-hydrometric-rating-curve)](/../../issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/bcgov/nr-hydrometric-rating-curve)](/../../pulls)
[![MIT License](https://img.shields.io/github/license/bcgov/nr-hydrometric-rating-curve.svg)](/LICENSE.md)
![Lifecycle:Maturing](https://img.shields.io/badge/Lifecycle-Maturing-007EC6)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)

# Hydrometric Rating Application (HydRA)

## Intro

A hydrometric rating curve describes the mathematical relationship between stage and discharge for a given hydrometric station. Rating curves allow to convert stage measurements to discharge measurements based on previously measured stage and discharge data pairs. The Hydrometric Rating Application (HydRA) allows users to upload any stage and discharge datasets, develop and optimize rating models as well as save and compare results from previous sessions.

The HydRA app is hosted in the BC Gov GitHub organization and is available [here](https://hydra.nrs.gov.bc.ca/). This repository contains all source code for the HydRA app and allows to run the app locally using docker.

## Managing the app packages

After cloning the repository, use the `poetry` python package manager to install the dependencies by running `poetry install` from the `frontend` directory. To update the dependencies, run `poetry update` or edit the `pyproject.toml` file.

## Running the app locally

### With Docker or Podman

This project includes a `compose.yml` file at the project root that works with both Docker and Podman:

```bash
# Build and run
podman compose up --build
# or
docker compose up --build
```

The app will be available at:
- App: http://localhost:3000
- Nginx: http://localhost:3001

### With docker-compose (legacy)

- Create a `.env` file in the `frontend` directory of the project by copying the `.env.example` file and updating the values as needed. For development, the `DJANGO_DEBUG` variable should be set to `True`.
- To run the django server locally, install docker and docker-compose. Run `docker compose -f ./frontend/docker-compose.dev.yml up --build` to start the development server. The app will be available at `http://localhost:8003`. Note: the non-dev version of the app is served via nginx at `http://localhost:{WEB_PORT}`.

## Running tests locally

The project uses [`pytest`](https://pytest.org) with [`pytest-django`](https://pytest-django.readthedocs.io) and [`pytest-cov`](https://pytest-cov.readthedocs.io) for testing and coverage reporting.

### Quick start (without Docker)

```bash
# from the frontend/ directory
pip install . xhtml2pdf pytest-django pytest-cov

# run all tests with coverage
DEBUG=False \
  ALLOWED_HOSTS='localhost,' \
  CSRF_TRUSTED_ORIGINS='http://localhost' \
  SECRET_KEY='local_dev_key' \
  pytest
```

### With Docker

Build the container and attach to the running shell, then run:

```bash
pytest
```

The `pytest.ini` file configures the `DJANGO_SETTINGS_MODULE`, test discovery paths, and enforces a **minimum 80% coverage threshold**.  Tests are also run automatically on every PR and push to `main` via the [Analysis workflow](.github/workflows/analysis.yml).

### Test layout

| File | What it tests |
|------|---------------|
| `rctool/tests/test_fit_linear_model.py` | Unit tests for the power-law curve fitting function |
| `rctool/tests/test_views_helpers.py` | Unit tests for `parse_context`, `autofit_data`, `export_calculate_discharge_error` |
| `rctool/tests/test_forms.py` | Django form validation — valid and invalid inputs |
| `rctool/tests/test_views.py` | View smoke tests (GET/POST), image generation helpers |
| `rctool/tests/test_integration.py` | Full end-to-end pipelines: import → autofit → PDF/CSV/session export |
| `rctool/tests/test_legacy.py` | Original tests (preserved for reference) |

### Renovate auto-merge

[Renovate](https://docs.renovatebot.com) is configured to **auto-merge** non-major dependency updates once all CI checks pass.  Major version bumps require human review.
