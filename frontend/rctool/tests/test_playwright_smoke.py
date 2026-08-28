"""
Playwright infrastructure smoke test.

Proves the browser-driven test pipeline works end to end: pytest-playwright's
`page` fixture against pytest-django's `live_server` fixture. Deliberately
trivial (just loads the homepage) — this is plumbing, not coverage for any
specific bug. See CONTRIBUTING.md for the one-time browser install step
required to run these tests locally.

Marked `playwright` so it's excluded from the default `pytest` run (see
pytest.ini) and only runs when explicitly selected with `pytest -m playwright`.
"""
import pytest


@pytest.mark.playwright
def test_homepage_loads(page, live_server):
    page.goto(live_server.url)

    assert "RC Tool" in page.title()
    assert page.get_by_role("link", name="Start Session").is_visible()
