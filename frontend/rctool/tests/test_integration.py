"""
Full end-to-end integration tests.

Each test class drives the complete workflow:
    CSV import → rctool_develop_initialize
    → rctool_develop_autofit
    → rctool_export_initialize
    → rctool_export_output (different filetypes)

Tests cover:
  - PDF export
  - CSV results export
  - Session settings (.dat) export
  - Session settings round-trip: export then re-import
"""
import json
from io import StringIO

import pandas as pd
import pytest

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

try:
    from xhtml2pdf import pisa as _pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Shared pipeline helpers
# ---------------------------------------------------------------------------

def _load_sample_df() -> pd.DataFrame:
    csv_path = finders.find("sample_data/sample_data.csv")
    df = pd.read_csv(csv_path)
    df = df.dropna(how="all")
    df.columns = df.columns.str.lower()
    df["comments"] = df["comments"].str.replace(",", ";", regex=False)
    return df


def _col_str(series: pd.Series) -> str:
    return ",".join(str(v) for v in series.values.tolist())


class _PipelineBase(TestCase):
    """Mixin providing reusable pipeline steps."""

    # ------------------------------------------------------------------
    # Step 1 — Import CSV
    # ------------------------------------------------------------------
    def _step_import(self) -> pd.DataFrame:
        df = _load_sample_df()
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": df.to_json(),
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200, "Import step failed")
        raw = resp.context["fielddatacsv"]
        field_df = pd.read_json(StringIO(raw))
        field_df["datetime"] = pd.to_datetime(field_df["datetime"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return field_df

    # ------------------------------------------------------------------
    # Step 2 — Autofit
    # ------------------------------------------------------------------
    def _step_autofit(self, field_df: pd.DataFrame, n_seg: int = 1) -> dict:
        field_df = field_df.copy()
        field_df["active"] = "checked"
        resp = self.client.post(
            reverse("rctool_develop_autofit"),
            data={
                "offset1": 0,
                "offset2": 0,
                "n-seg": n_seg,
                "toggle_weighted_fit": "on",
                "tour_request_status_id": 0,
                "fieldData_datetime": _col_str(field_df["datetime"]),
                "fieldData_comments": _col_str(field_df["comments"]),
                "fieldData_uncertainty": _col_str(field_df["uncertainty"]),
                "fieldData_stage": _col_str(field_df["stage"]),
                "fieldData_discharge": _col_str(field_df["discharge"]),
                "fieldData_active": _col_str(field_df["active"]),
                "filename": "integration_test",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200, "Autofit step failed")
        rc = resp.context["rc"]
        self.assertIsNotNone(rc, "rc context missing after autofit")
        return rc

    # ------------------------------------------------------------------
    # Step 3 — Export initialize
    # ------------------------------------------------------------------
    def _step_export_init(self, field_df: pd.DataFrame, rc: dict) -> None:
        field_df = field_df.copy()
        field_df["active"] = "checked"
        resp = self.client.post(
            reverse("rctool_export_initialize"),
            data={
                "fieldData_datetime": _col_str(field_df["datetime"]),
                "fieldData_comments": _col_str(field_df["comments"]),
                "fieldData_uncertainty": _col_str(field_df["uncertainty"]),
                "fieldData_stage": _col_str(field_df["stage"]),
                "fieldData_discharge": _col_str(field_df["discharge"]),
                "fieldData_active": _col_str(field_df["active"]),
                "rc_out": json.dumps(rc),
                "filename_out": "integration_test",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200, "Export init step failed")

    # ------------------------------------------------------------------
    # Step 4 — Export output
    # ------------------------------------------------------------------
    def _step_export_output(
        self,
        field_df: pd.DataFrame,
        rc: dict,
        filetype: str,
        filename: str = "integration_test",
    ):
        field_df = field_df.copy()
        field_df["toggle_point"] = "checked"
        resp = self.client.post(
            reverse("rctool_export_output"),
            data={
                "fielddatacsv-to-output": json.dumps(field_df.to_dict()),
                "rc_output": json.dumps(rc),
                "export_filetype": filetype,
                "export_filename": filename,
                "export_station_name": "Integration Test Station",
                "export_comments": "automated integration test",
                "export_date_applic_init": "2024-01-01",
                "export_date_applic_final": "2024-12-31",
            },
            follow=True,
        )
        return resp


# ---------------------------------------------------------------------------
# Integration Test 1 — PDF export
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not XHTML2PDF_AVAILABLE,
    reason="xhtml2pdf not installed; skipping PDF integration test",
)
class TestFullPipelinePdfExport(_PipelineBase):
    def test_pdf_export_end_to_end(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (pdf)")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")

    def test_pdf_content_not_empty(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (pdf)")
        self.assertGreater(len(resp.content), 100)

    def test_pdf_starts_with_magic_bytes(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (pdf)")
        # PDF files start with %PDF
        self.assertTrue(resp.content[:4] == b"%PDF")


# ---------------------------------------------------------------------------
# Integration Test 2 — CSV results export
# ---------------------------------------------------------------------------

class TestFullPipelineCsvExport(_PipelineBase):
    def test_csv_export_status_200(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (csv)")
        self.assertEqual(resp.status_code, 200)

    def test_csv_export_content_type(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (csv)")
        self.assertIn("text/csv", resp["Content-Type"])

    def test_csv_export_content_disposition_filename(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(
            field_df, rc, filetype="session results (csv)", filename="myresults"
        )
        self.assertIn("myresults.csv", resp["Content-Disposition"])

    def test_csv_export_contains_header_row(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (csv)")
        content = resp.content.decode("utf-8")
        self.assertIn("RATING CURVE OUTPUT SUMMARY", content)

    def test_csv_export_contains_model_parameters(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (csv)")
        content = resp.content.decode("utf-8")
        self.assertIn("MODEL PARAMETERS", content)

    def test_csv_export_contains_model_inputs(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session results (csv)")
        content = resp.content.decode("utf-8")
        self.assertIn("MODEL INPUTS", content)


# ---------------------------------------------------------------------------
# Integration Test 3 — Session settings export
# ---------------------------------------------------------------------------

class TestFullPipelineSessionSettingsExport(_PipelineBase):
    def test_session_settings_status_200(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session settings")
        self.assertEqual(resp.status_code, 200)

    def test_session_settings_content_type(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session settings")
        self.assertIn("text/csv", resp["Content-Type"])

    def test_session_settings_dat_extension_in_header(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(
            field_df, rc, filetype="session settings", filename="mysession"
        )
        self.assertIn(".dat", resp["Content-Disposition"])

    def test_session_settings_not_empty(self):
        field_df = self._step_import()
        rc = self._step_autofit(field_df)
        self._step_export_init(field_df, rc)
        resp = self._step_export_output(field_df, rc, filetype="session settings")
        content = resp.content.decode("utf-8")
        self.assertGreater(len(content.strip()), 0)


# ---------------------------------------------------------------------------
# Integration Test 4 — Session round-trip (export → reload)
#
# The "session settings" export produces a .dat CSV file intended for the UI
# file-picker.  Reloading a session in the browser reads the file content and
# POSTs it as JSON (the JS client-side code serialises the DataFrame as JSON
# before sending).  We replicate that serialisation here: the view's load path
# calls pd.read_json() on session_content, so we must provide JSON, not CSV.
# ---------------------------------------------------------------------------

class TestFullPipelineSessionRoundTrip(_PipelineBase):
    def _build_session_json(self, field_df: pd.DataFrame, rc: dict) -> str:
        """
        Build the JSON string the view's load path expects.

        The view's load path (views.py:394) calls ast.literal_eval() on each
        cell in the "data" column.  That means the cells must be *strings*
        containing Python literal representations of lists/dicts — exactly as
        pandas produces when writing a DataFrame to CSV (each object cell is
        str(value)) and the UI then POSTs it as JSON for pd.read_json().

        We replicate that by converting every "data" and "parameters" value to
        its str() representation before building the JSON payload.
        """
        fdf = field_df.copy()
        fdf["toggle_point"] = "checked"
        field_values = fdf.values.tolist()

        rc_dict = dict(rc)
        rc_dict["data"] = list(rc_dict["data"])
        rc_dict["data"].append(field_values)
        rc_dict["filename"] = ["roundtrip_test"]

        rc_df = pd.DataFrame.from_dict(rc_dict, orient="index")
        rc_df = rc_df.transpose()

        # The load path calls ast.literal_eval on each cell, so cells must be
        # strings (as they would be after a CSV round-trip through pandas).
        for col in ("data", "parameters"):
            if col in rc_df.columns:
                rc_df[col] = rc_df[col].apply(
                    lambda v: str(v) if not isinstance(v, str) else v
                )

        return rc_df.to_json()

    def test_roundtrip_produces_valid_rc(self):
        """Build session JSON, reload it, and verify the RC is intact."""
        field_df = self._step_import()
        rc_original = self._step_autofit(field_df)

        session_json = self._build_session_json(field_df, rc_original)

        resp_reload = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": "",
                "input_session_type": "load",
                "session_content": session_json,
                "csv_separator": ",",
            },
            follow=True,
        )
        self.assertEqual(resp_reload.status_code, 200)
        rc_reloaded = resp_reload.context["rc"]
        self.assertIsNotNone(rc_reloaded)
        self.assertIn("parameters", rc_reloaded)
        self.assertGreater(len(rc_reloaded["parameters"]), 0)

    def test_roundtrip_parameter_values_preserved(self):
        """The const and exp values should survive the JSON round-trip."""
        field_df = self._step_import()
        rc_original = self._step_autofit(field_df)

        session_json = self._build_session_json(field_df, rc_original)

        resp_reload = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": "",
                "input_session_type": "load",
                "session_content": session_json,
                "csv_separator": ",",
            },
            follow=True,
        )
        rc_reloaded = resp_reload.context["rc"]

        orig_const = round(rc_original["parameters"][0]["const"], 4)
        orig_exp = round(rc_original["parameters"][0]["exp"], 4)
        reloaded_const = round(rc_reloaded["parameters"][0]["const"], 4)
        reloaded_exp = round(rc_reloaded["parameters"][0]["exp"], 4)

        self.assertAlmostEqual(orig_const, reloaded_const, places=3)
        self.assertAlmostEqual(orig_exp, reloaded_exp, places=3)
