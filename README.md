<!-- PROJECT SHIELDS -->

[![Analysis](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/analysis.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/analysis.yml)
[![Merge](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/merge.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/merge.yml)
[![Release](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/prod.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/prod.yml)
[![Scheduled](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/scheduled.yml/badge.svg)](https://github.com/bcgov/nr-hydrometric-rating-curve/actions/workflows/scheduled.yml)

[![Issues](https://img.shields.io/github/issues/bcgov/nr-hydrometric-rating-curve)](/../../issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/bcgov/nr-hydrometric-rating-curve)](/../../pulls)
[![MIT License](https://img.shields.io/github/license/bcgov/nr-hydrometric-rating-curve.svg)](/LICENSE.md)
![Lifecycle:Maturing](https://img.shields.io/badge/Lifecycle-Maturing-007EC6)

# Hydrometric Rating Application (HydRA)

## Intro

A hydrometric rating curve describes the mathematical relationship between stage and discharge for a given hydrometric station. Rating curves allow to convert stage measurements to discharge measurements based on previously measured stage and discharge data pairs. The Hydrometric Rating Application (HydRA) allows users to upload any stage and discharge datasets, develop and optimize rating models as well as save and compare results from previous sessions.

The HydRA app is hosted in the BC Gov GitHub organization and is available [here](https://hydra.nrs.gov.bc.ca/). This repository contains all source code for the HydRA app and allows to run the app locally using docker.

## Managing the app packages

After cloning the repository, use the `poetry` python package manager to install the dependencies by running `poetry install` from the `frontend` directory. To update the dependencies, run `poetry update` or edit the `pyproject.toml` file.

## Running the app locally

- Create a `.env` file in the `frontend` directory of the project by copying the `.env.example` file and updating the values as needed. For development, the `DJANGO_DEBUG` variable should be set to `True`.
- To run the django server locally, install docker and docker-compose. Run `docker compose -f ./frontend/docker-compose.dev.yml up --build` to start the development server. The app will be available at `http://localhost:8003`. Note: the non-dev version of the app is served via nginx at `http://localhost:{WEB_PORT}`.

## Running tests locally

To run Django tests, it is easiest to build the Docker container and attach to the running shell. The command `python manage.py test` executes the tests in Django.

##### Contributing Authors

NHC (Tyler De Jong, Tobias Müller), ENV X