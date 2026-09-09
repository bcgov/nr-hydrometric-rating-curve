# How to contribute

Government employees, public and members of the private sector are encouraged to contribute to the repository by **forking and submitting a pull request**.

(If you are new to GitHub, you might start with a [basic tutorial](https://help.github.com/articles/set-up-git) and check out a more detailed guide to [pull requests](https://help.github.com/articles/using-pull-requests/).)

Pull requests will be evaluated by the repository guardians on a schedule and if deemed beneficial will be committed to the main branch.

All contributors retain the original copyright to their stuff, but by contributing to this project, you grant a world-wide, royalty-free, perpetual, irrevocable, non-exclusive, transferable license to all users **under the terms of the [license](./LICENSE.md) under which this project is distributed**.

## Running Playwright (browser) tests locally

Some tests under `frontend/rctool/tests/` drive a real browser via
[Playwright](https://playwright.dev/python/) against a live Django test server, to cover behaviour
that only exists in client-side JavaScript. They're marked `playwright` and excluded from the
default `pytest` run (see `frontend/pytest.ini`), so they need one extra one-time setup step and an
explicit opt-in flag to run.

One-time setup, from the `frontend` directory, after installing the project's regular test
dependencies (see `README.md`):

```bash
pip install pytest-playwright
playwright install --with-deps chromium   # downloads the browser binary + its OS-level dependencies
```

`--with-deps` installs system packages via `apt` and needs root — use `sudo playwright install-deps
chromium` first if you don't have passwordless sudo, then re-run `playwright install chromium`
without `--with-deps`.

Then run just the Playwright tests with:

```bash
DJANGO_ALLOW_ASYNC_UNSAFE=1 pytest -m playwright --no-cov
```

Two env vars matter here, both already set for you in CI (see `.github/workflows/analysis.yml`):

- `DJANGO_ALLOW_ASYNC_UNSAFE=1` — required. Playwright's sync API trips Django's async-safety check
  during `live_server`'s test-database setup; this is a known false positive for this combination,
  not a real async context.
- `PLAYWRIGHT_BROWSERS_PATH` — set this to a fixed directory (e.g. `export
  PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright` before both the `playwright install` step
  above and the `pytest` run) if browser launches fail with "Executable doesn't exist". `rctool`
  force-sets `HOME=/tmp` at import time (`rctool/views.py`, `rctool/utils.py`), which can otherwise
  make Playwright look for its installed browser in a different place than where it was installed.
