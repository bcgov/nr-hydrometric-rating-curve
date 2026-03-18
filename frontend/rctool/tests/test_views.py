"""
View tests: URL smoke tests, POST payloads, and image-generation helpers.

Covers todo items:
  - URL routing smoke tests (GET 200) for all named URLs
  - POST rctool_develop_initialize — new session
  - POST rctool_develop_initialize — load session (round-trip)
  - POST rctool_develop_autofit — 1 seg and 2 seg
  - POST rctool_export_initialize
  - GET healthcheck
  - create_export_rc_img and create_export_res_img return base64 strings
"""
import base64
import io
import json
from io import StringIO

import numpy as np
import pandas as pd
import pytest
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from rctool.views import create_export_rc_img, create_export_res_img


# ---------------------------------------------------------------------------
# Shared test-data helpers
# ---------------------------------------------------------------------------

def _load_sample_csv() -> pd.DataFrame:
    """Load the canonical sample_data.csv that ships with the app."""
    csv_path = finders.find("sample_data/sample_data.csv")
    df = pd.read_csv(csv_path)
    df = df.dropna(how="all")
    df.columns = df.columns.str.lower()
    df["comments"] = df["comments"].str.replace(",", ";", regex=False)
    return df


def _csv_json() -> str:
    return _load_sample_csv().to_json()


def _col_to_string(series: pd.Series) -> str:
    return ",".join(str(v) for v in series.values.tolist())


def _import_and_get_fielddata(client: Client) -> pd.DataFrame:
    """POST to rctool_develop_initialize and return parsed field data."""
    resp = client.post(
        reverse("rctool_develop_initialize"),
        data={
            "header_row": 1,
            "csv_content": _csv_json(),
            "input_session_type": "new",
            "session_content": "",
            "csv_separator": ",",
        },
        follow=True,
    )
    assert resp.status_code == 200
    raw = resp.context["fielddatacsv"]
    df = pd.read_json(StringIO(raw))
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def _autofit_and_get_rc(client: Client, df: pd.DataFrame, n_seg: int = 1, breakpoint: float | None = None) -> dict:
    """POST to rctool_develop_autofit and return the rc context dict."""
    df = df.copy()
    df["active"] = "checked"
    post = {
        "offset1": 0,
        "offset2": 0,
        "n-seg": n_seg,
        "toggle_weighted_fit": "on",
        "tour_request_status_id": 0,
        "fieldData_datetime": _col_to_string(df["datetime"]),
        "fieldData_comments": _col_to_string(df["comments"]),
        "fieldData_uncertainty": _col_to_string(df["uncertainty"]),
        "fieldData_stage": _col_to_string(df["stage"]),
        "fieldData_discharge": _col_to_string(df["discharge"]),
        "fieldData_active": _col_to_string(df["active"]),
        "filename": "test.pdf",
    }
    if breakpoint is not None:
        post["breakpoint1"] = breakpoint
    resp = client.post(reverse("rctool_develop_autofit"), data=post, follow=True)
    assert resp.status_code == 200
    return resp.context["rc"]


# ---------------------------------------------------------------------------
# URL smoke tests — GET
# ---------------------------------------------------------------------------

class TestUrlSmokeTests(TestCase):
    def test_home_get(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

    def test_about_get(self):
        resp = self.client.get(reverse("about"))
        self.assertEqual(resp.status_code, 200)

    def test_healthcheck_get(self):
        resp = self.client.get(reverse("healthcheck"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"OK")

    def test_rctool_tour_intro_get(self):
        resp = self.client.get(reverse("rctool_tour_intro", args=[0]))
        self.assertEqual(resp.status_code, 200)

    def test_rctool_import_get(self):
        resp = self.client.get(reverse("rctool_import", args=[0]))
        self.assertEqual(resp.status_code, 200)

    def test_download_sample_data_get(self):
        resp = self.client.get(reverse("download_sample_data"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.get("Content-Type", ""))

    def test_rctool_export_initialize_get(self):
        """GET on export/initialize should return 200 with an empty export form."""
        resp = self.client.get(reverse("rctool_export_initialize"))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# rctool_develop_initialize — new session POST
# ---------------------------------------------------------------------------

class TestDevelopInitializeNewSession(TestCase):
    def test_status_200(self):
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": _csv_json(),
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

    def test_table_dict_populated(self):
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": _csv_json(),
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        self.assertGreater(len(resp.context["table_dict"]["data"]), 0)

    def test_fielddatacsv_present(self):
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": _csv_json(),
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        self.assertIsNotNone(resp.context["fielddatacsv"])

    def test_rc_present_and_non_empty(self):
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": _csv_json(),
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        rc = resp.context["rc"]
        self.assertIsNotNone(rc)
        self.assertIn("data", rc)
        self.assertIn("parameters", rc)

    def test_invalid_json_redirects_gracefully(self):
        """Malformed JSON in csv_content should not crash with a 500."""
        resp = self.client.post(
            reverse("rctool_develop_initialize"),
            data={
                "header_row": 1,
                "csv_content": "THIS IS NOT JSON }{",
                "input_session_type": "new",
                "session_content": "",
                "csv_separator": ",",
            },
            follow=True,
        )
        # Should redirect back to import page gracefully, not 500
        self.assertIn(resp.status_code, [200, 302])


# ---------------------------------------------------------------------------
# rctool_develop_initialize — load session (round-trip)
# ---------------------------------------------------------------------------

class TestDevelopInitializeLoadSession(TestCase):
    def _build_session_json(self) -> str:
        """
        Build a session JSON string in the format the load path expects.

        The view's load path (views.py:394) applies ast.literal_eval() to each
        cell in the "data" and "parameters" columns — so those cells must be
        *strings* of Python literals, not already-parsed Python objects.
        This mirrors what happens when a user loads the .dat CSV: pandas reads
        each cell as a string, and the UI posts that content as JSON.
        """
        df = _import_and_get_fielddata(self.client)
        df["active"] = "checked"
        rc_data = _autofit_and_get_rc(self.client, df)

        df["toggle_point"] = "checked"
        # The view's load path expects exactly these 6 columns in this order
        field_cols = ["datetime", "discharge", "stage", "uncertainty", "comments", "toggle_point"]
        field_data_values = df[field_cols].values.tolist()
        rc_output_dict = dict(rc_data)
        rc_output_dict["data"] = list(rc_output_dict["data"])
        rc_output_dict["data"].append(field_data_values)
        rc_output_dict["filename"] = ["roundtrip_test"]

        rc_output_df = pd.DataFrame.from_dict(rc_output_dict, orient="index")
        rc_output_df = rc_output_df.transpose()

        # Stringify data/parameter cells so ast.literal_eval works in the view
        for col in ("data", "parameters"):
            if col in rc_output_df.columns:
                rc_output_df[col] = rc_output_df[col].apply(
                    lambda v: str(v) if not isinstance(v, str) else v
                )

        return rc_output_df.to_json()

    def test_load_session_roundtrip(self):
        """Load a session JSON back into the tool and verify RC is present."""
        session_json = self._build_session_json()
        resp = self.client.post(
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
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rc", resp.context)
        rc_loaded = resp.context["rc"]
        self.assertIn("data", rc_loaded)
        self.assertIn("parameters", rc_loaded)


# ---------------------------------------------------------------------------
# rctool_develop_autofit — 1 segment
# ---------------------------------------------------------------------------

class TestDevelopAutofit1Seg(TestCase):
    def test_status_200(self):
        df = _import_and_get_fielddata(self.client)
        df["active"] = "checked"
        resp = self.client.post(
            reverse("rctool_develop_autofit"),
            data={
                "offset1": 0,
                "offset2": 0,
                "n-seg": 1,
                "toggle_weighted_fit": "on",
                "tour_request_status_id": 0,
                "fieldData_datetime": _col_to_string(df["datetime"]),
                "fieldData_comments": _col_to_string(df["comments"]),
                "fieldData_uncertainty": _col_to_string(df["uncertainty"]),
                "fieldData_stage": _col_to_string(df["stage"]),
                "fieldData_discharge": _col_to_string(df["discharge"]),
                "fieldData_active": _col_to_string(df["active"]),
                "filename": "test.pdf",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

    def test_rc_has_one_parameter_segment(self):
        df = _import_and_get_fielddata(self.client)
        rc = _autofit_and_get_rc(self.client, df, n_seg=1)
        self.assertEqual(len(rc["parameters"]), 1)

    def test_rc_parameter_has_required_keys(self):
        df = _import_and_get_fielddata(self.client)
        rc = _autofit_and_get_rc(self.client, df, n_seg=1)
        param = rc["parameters"][0]
        for key in ("const", "exp", "offset", "rmse", "mape", "seg_bounds"):
            self.assertIn(key, param)

    def test_unweighted_fit_also_works(self):
        df = _import_and_get_fielddata(self.client)
        df["active"] = "checked"
        resp = self.client.post(
            reverse("rctool_develop_autofit"),
            data={
                "offset1": 0,
                "offset2": 0,
                "n-seg": 1,
                # no toggle_weighted_fit key → unweighted
                "tour_request_status_id": 0,
                "fieldData_datetime": _col_to_string(df["datetime"]),
                "fieldData_comments": _col_to_string(df["comments"]),
                "fieldData_uncertainty": _col_to_string(df["uncertainty"]),
                "fieldData_stage": _col_to_string(df["stage"]),
                "fieldData_discharge": _col_to_string(df["discharge"]),
                "fieldData_active": _col_to_string(df["active"]),
                "filename": "test.pdf",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        rc = resp.context["rc"]
        self.assertIsNotNone(rc)


# ---------------------------------------------------------------------------
# rctool_develop_autofit — 2 segments with explicit breakpoint
# ---------------------------------------------------------------------------

class TestDevelopAutofit2Seg(TestCase):
    def test_2seg_explicit_breakpoint_200(self):
        df = _import_and_get_fielddata(self.client)
        breakpoint_H = float(df["stage"].median())
        df["active"] = "checked"
        resp = self.client.post(
            reverse("rctool_develop_autofit"),
            data={
                "offset1": 0,
                "offset2": 0,
                "n-seg": 2,
                "breakpoint1": breakpoint_H,
                "toggle_weighted_fit": "on",
                "tour_request_status_id": 0,
                "fieldData_datetime": _col_to_string(df["datetime"]),
                "fieldData_comments": _col_to_string(df["comments"]),
                "fieldData_uncertainty": _col_to_string(df["uncertainty"]),
                "fieldData_stage": _col_to_string(df["stage"]),
                "fieldData_discharge": _col_to_string(df["discharge"]),
                "fieldData_active": _col_to_string(df["active"]),
                "filename": "test.pdf",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

    def test_2seg_rc_context_present(self):
        df = _import_and_get_fielddata(self.client)
        rc = _autofit_and_get_rc(self.client, df, n_seg=2)
        self.assertIn("parameters", rc)
        self.assertGreater(len(rc["parameters"]), 0)


# ---------------------------------------------------------------------------
# rctool_export_initialize
# ---------------------------------------------------------------------------

class TestExportInitialize(TestCase):
    def test_post_200(self):
        df = _import_and_get_fielddata(self.client)
        df["active"] = "checked"
        rc_data = _autofit_and_get_rc(self.client, df)
        resp = self.client.post(
            reverse("rctool_export_initialize"),
            data={
                "fieldData_datetime": _col_to_string(df["datetime"]),
                "fieldData_comments": _col_to_string(df["comments"]),
                "fieldData_uncertainty": _col_to_string(df["uncertainty"]),
                "fieldData_stage": _col_to_string(df["stage"]),
                "fieldData_discharge": _col_to_string(df["discharge"]),
                "fieldData_active": _col_to_string(df["active"]),
                "rc_out": json.dumps(rc_data),
                "filename_out": "export_test.pdf",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

    def test_form_in_context(self):
        resp = self.client.get(reverse("rctool_export_initialize"))
        self.assertIn("form", resp.context)


# ---------------------------------------------------------------------------
# create_export_rc_img and create_export_res_img
# ---------------------------------------------------------------------------

def _minimal_rc_dict(n_segs: int = 1) -> dict:
    params = [
        {
            "label": "model segment 1",
            "const": 1.5,
            "exp": 2.3,
            "offset": 0.0,
            "seg_bounds": [[0.2, 0.03], [0.7, 0.50]],
            "rmse": 0.01,
            "mape": 2.0,
        }
    ]
    if n_segs == 2:
        params.append(
            {
                "label": "model segment 2",
                "const": 2.0,
                "exp": 2.1,
                "offset": 0.0,
                "seg_bounds": [[0.45, 0.25], [0.90, 1.30]],
                "rmse": 0.02,
                "mape": 3.0,
            }
        )
    stage = np.linspace(0.2, 0.7, 10)
    discharge = 1.5 * stage ** 2.3
    field_data = [[float(s), float(d), float(s), "checked"] for s, d in zip(stage, discharge)]
    return {
        "data": [{"label": "field", "data": [[float(s), float(d), "checked"] for s, d in zip(stage, discharge)]}],
        "parameters": params,
    }


def _minimal_field_df(n: int = 10, all_active: bool = True) -> pd.DataFrame:
    stage = np.linspace(0.2, 0.7, n)
    discharge = 1.5 * stage ** 2.3
    discharge_error = np.zeros(n)
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2023-01-01", periods=n, freq="ME").astype(str),
            "stage": stage,
            "discharge": discharge,
            "uncertainty": [10.0] * n,
            "comments": [""] * n,
            "toggle_point": ["checked" if all_active else ("unchecked" if i % 2 else "checked") for i in range(n)],
            "Discharge Error (%)": discharge_error,
        }
    )


class TestCreateExportImages(TestCase):
    def test_create_rc_img_returns_string(self):
        rc = _minimal_rc_dict(n_segs=1)
        df = _minimal_field_df()
        result = create_export_rc_img(df, rc)
        self.assertIsInstance(result, str)

    def test_create_rc_img_is_valid_base64(self):
        rc = _minimal_rc_dict(n_segs=1)
        df = _minimal_field_df()
        result = create_export_rc_img(df, rc)
        # Should decode without error
        decoded = base64.b64decode(result)
        self.assertGreater(len(decoded), 0)

    def test_create_rc_img_2seg_no_crash(self):
        rc = _minimal_rc_dict(n_segs=2)
        df = _minimal_field_df()
        result = create_export_rc_img(df, rc)
        self.assertIsInstance(result, str)

    def test_create_rc_img_with_inactive_points(self):
        rc = _minimal_rc_dict(n_segs=1)
        df = _minimal_field_df(n=12, all_active=False)
        result = create_export_rc_img(df, rc)
        self.assertIsInstance(result, str)

    def test_create_res_img_returns_string(self):
        df = _minimal_field_df()
        result = create_export_res_img(df, _minimal_rc_dict())
        self.assertIsInstance(result, str)

    def test_create_res_img_is_valid_base64(self):
        df = _minimal_field_df()
        result = create_export_res_img(df, _minimal_rc_dict())
        decoded = base64.b64decode(result)
        self.assertGreater(len(decoded), 0)
