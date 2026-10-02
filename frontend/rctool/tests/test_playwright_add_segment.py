"""
Regression test: "(+) add segment" on the Develop page.

Since PR #362 the Develop form refits client-side with Pyodide instead of
reloading the page. Clicking "(+) add segment" on a 1-segment fit then threw
`TypeError: Cannot set properties of undefined (setting 'data')` in
`updateResidualChart`, and the segment 2 panel never appeared.

Slow: waits for Pyodide (fetched from the jsdelivr CDN) to finish loading
numpy/pandas/scipy/lmfit, since the bug only exists on that code path.
"""
import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

PYODIDE_TIMEOUT_MS = 180_000


@pytest.mark.playwright
def test_add_segment_renders_second_segment(page, live_server):
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.goto(live_server.url + reverse("rctool_import", args=[0]))
    page.set_input_files("#csvFile", finders.find("sample_data/sample_data.csv"))
    page.click("#enter-data-button:enabled")
    page.wait_for_selector("#add-seg-link")

    # The bug only exists on the client-side (Pyodide) refit path
    page.wait_for_function("pyodideReady", timeout=PYODIDE_TIMEOUT_MS)

    page.click("#add-seg-link")

    try:
        page.wait_for_selector("#segment2-const", timeout=30_000)
    finally:
        # Surface any JS error over a bare selector timeout
        assert errors == []
