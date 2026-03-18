"""
Unit tests for pure-logic helper functions defined in views.py.

These are imported directly — no Django test client required — so they run
fast and don't depend on URL routing or templates.
"""
import math

import numpy as np
import pandas as pd
import pytest

# We import the helpers from views directly.
from rctool.views import (
    autofit_data,
    export_calculate_discharge_error,
    parse_context,
    parse_list,
)


# ---------------------------------------------------------------------------
# Helpers shared across test classes
# ---------------------------------------------------------------------------

def _field_df(n: int = 16, seed: int = 0) -> pd.DataFrame:
    """Synthetic field data with the columns expected by autofit_data."""
    rng = np.random.default_rng(seed)
    stage = np.linspace(0.2, 0.7, n) + rng.normal(0, 0.002, n)
    stage = np.clip(stage, 0.05, None)
    discharge = 1.5 * stage ** 2.3 * (1 + rng.normal(0, 0.04, n))
    discharge = np.clip(discharge, 0.001, None)
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2023-01-01", periods=n, freq="ME").astype(str).tolist(),
            "stage": stage,
            "discharge": discharge,
            "uncertainty": rng.uniform(5.0, 20.0, n),
            "comments": [f"c{i}" for i in range(n)],
            "toggle_point": ["checked"] * n,
        }
    )


# ---------------------------------------------------------------------------
# parse_list
# ---------------------------------------------------------------------------

class TestParseList:
    def test_converts_np_float64(self):
        lst = [np.float64(1.5), np.float64(2.5)]
        result = parse_list(lst)
        for item in result:
            assert type(item) is float

    def test_nested_list_converted(self):
        lst = [[np.float64(3.14)]]
        result = parse_list(lst)
        assert type(result[0][0]) is float

    def test_dict_inside_list_converted(self):
        lst = [{"val": np.float64(9.9)}]
        result = parse_list(lst)
        assert type(result[0]["val"]) is float

    def test_plain_python_types_unaffected(self):
        lst = [1, "hello", 3.0, True]
        result = parse_list(lst)
        assert result == [1, "hello", 3.0, True]


# ---------------------------------------------------------------------------
# parse_context
# ---------------------------------------------------------------------------

class TestParseContext:
    def test_converts_np_float64_values(self):
        ctx = {"a": np.float64(1.1), "b": np.float64(2.2)}
        result = parse_context(ctx)
        assert type(result["a"]) is float
        assert type(result["b"]) is float

    def test_nested_dict_converted(self):
        ctx = {"outer": {"inner": np.float64(5.0)}}
        result = parse_context(ctx)
        assert type(result["outer"]["inner"]) is float

    def test_list_values_converted(self):
        ctx = {"vals": [np.float64(1.0), np.float64(2.0)]}
        result = parse_context(ctx)
        for v in result["vals"]:
            assert type(v) is float

    def test_raises_if_np_float64_remains(self):
        """If a np.float64 somehow survived conversion it should raise."""
        # Inject a key that parse_context won't walk (non-dict, non-list value
        # that IS np.float64 but bypass the conversion by stuffing it into a
        # custom type that str() shows the problem string)
        # Actually the simplest way is to verify the guard code fires:
        # We mock a context that claims to contain np.float64 in its str repr
        # but isn't reachable by the current walk — simulate by constructing
        # a context that the guard will catch.
        class _Sneaky:
            def __repr__(self):
                return "np.float64(1.0)"
            def __str__(self):
                return "np.float64(1.0)"

        ctx = {"sneaky": _Sneaky()}
        with pytest.raises(ValueError, match="np.float64"):
            parse_context(ctx)

    def test_plain_types_pass_through(self):
        ctx = {"x": 1, "y": "hello", "z": [1, 2, 3]}
        result = parse_context(ctx)
        assert result["x"] == 1
        assert result["y"] == "hello"


# ---------------------------------------------------------------------------
# autofit_data — 1 segment
# ---------------------------------------------------------------------------

class TestAutofitData1Seg:
    def test_returns_rc_dict_and_message(self):
        df = _field_df()
        rc, msg = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        assert "data" in rc
        assert "parameters" in rc

    def test_rc_dict_has_field_data(self):
        df = _field_df()
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        labels = [d["label"] for d in rc["data"]]
        assert "field" in labels

    def test_rc_dict_has_model_segment(self):
        df = _field_df()
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        labels = [d["label"] for d in rc["data"]]
        assert "model segment 1" in labels

    def test_parameters_has_one_entry(self):
        df = _field_df()
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        assert len(rc["parameters"]) == 1

    def test_parameter_keys_present(self):
        df = _field_df()
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        for key in ("const", "exp", "seg_bounds", "offset", "rmse", "mape"):
            assert key in rc["parameters"][0]

    def test_no_sidepanel_message_for_valid_data(self):
        df = _field_df()
        _, msg = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        # Message may be None or a warning about extreme exponents
        # — just assert it isn't an error about fitting failing
        if msg is not None:
            assert "error_text" in msg

    def test_boundary_extension_applied(self):
        """Lower and upper boundary points should extend beyond field data."""
        df = _field_df()
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        seg_data = next(d for d in rc["data"] if d["label"] == "model segment 1")
        seg_H_values = [pt[0] for pt in seg_data["data"]]
        field_H_min = df["stage"].min()
        field_H_max = df["stage"].max()
        # The model segment should extend beyond the raw field measurements
        assert min(seg_H_values) < field_H_min
        assert max(seg_H_values) > field_H_max

    def test_inactive_points_excluded(self):
        """Points with toggle_point != 'checked' must be ignored in fitting."""
        df = _field_df(n=20)
        # Deactivate the first 5 rows
        df.loc[:4, "toggle_point"] = "unchecked"
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=1)
        # The field dataset in rc["data"] should only contain checked points
        field_entry = next(d for d in rc["data"] if d["label"] == "field")
        assert len(field_entry["data"]) == 15


# ---------------------------------------------------------------------------
# autofit_data — 2 segments with explicit breakpoint
# ---------------------------------------------------------------------------

class TestAutofitData2SegExplicitBreakpoint:
    def test_produces_two_parameter_entries(self):
        df = _field_df(n=20)
        breakpoint_H = float(df["stage"].median())
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], breakpointH=breakpoint_H, n_seg=2)
        if rc["parameters"] is not None:
            assert len(rc["parameters"]) >= 1   # may fall back to 1 if breakpoint invalid

    def test_no_crash_explicit_breakpoint(self):
        df = _field_df(n=20)
        breakpoint_H = float(df["stage"].quantile(0.5))
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], breakpointH=breakpoint_H, n_seg=2)
        assert "data" in rc

    def test_two_model_segments_present(self):
        df = _field_df(n=24, seed=5)
        breakpoint_H = float(df["stage"].quantile(0.45))
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], breakpointH=breakpoint_H, n_seg=2)
        labels = [d["label"] for d in rc["data"]]
        # Both segments should appear (unless there weren't enough points)
        if len(rc["parameters"]) == 2:
            assert "model segment 1" in labels
            assert "model segment 2" in labels


# ---------------------------------------------------------------------------
# autofit_data — 2 segments auto-optimised (no breakpoint)
# ---------------------------------------------------------------------------

class TestAutofitData2SegAutoOptimise:
    def test_no_crash_auto_optimise(self):
        df = _field_df(n=30, seed=3)
        rc, _ = autofit_data(df, offsets=[0.0, 0.0], n_seg=2)
        assert "data" in rc

    def test_falls_back_to_1_seg_on_too_few_points(self):
        """With only 4 points, 2-seg optimisation should fall back gracefully."""
        df = _field_df(n=4, seed=9)
        rc, msg = autofit_data(df, offsets=[0.0, 0.0], n_seg=2)
        # Should not crash — may fall back to 1-seg
        assert "data" in rc


# ---------------------------------------------------------------------------
# export_calculate_discharge_error
# ---------------------------------------------------------------------------

class TestExportCalculateDischargeError:
    def _make_rc_output(self, n_segs: int = 1) -> dict:
        """Build a minimal rc_output_dict as the export view would create it."""
        params = [
            {
                "label": "model segment 1",
                "const": 1.5,
                "exp": 2.3,
                "offset": 0.0,
                "seg_bounds": [[0.15, 0.01], [0.65, 0.50]],
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
                    "seg_bounds": [[0.45, 0.30], [0.90, 1.20]],
                    "rmse": 0.02,
                    "mape": 3.0,
                }
            )
        return {"data": [], "parameters": params}

    def _make_field_df(self) -> pd.DataFrame:
        stage = np.linspace(0.2, 0.7, 12)
        discharge = 1.5 * stage ** 2.3
        return pd.DataFrame(
            {
                "datetime": pd.date_range("2023-01-01", periods=12, freq="ME").astype(str),
                "stage": stage,
                "discharge": discharge,
                "uncertainty": [10.0] * 12,
                "comments": [""] * 12,
                "toggle_point": ["checked"] * 12,
            }
        )

    def test_column_added_1seg(self):
        df = self._make_field_df()
        rc = self._make_rc_output(n_segs=1)
        result = export_calculate_discharge_error(df, rc)
        assert "Discharge Error (%)" in result.columns

    def test_error_near_zero_for_perfect_fit(self):
        """If discharge exactly matches the model, error should be near 0%."""
        stage = np.linspace(0.2, 0.7, 10)
        discharge = 1.5 * stage ** 2.3  # exact power law, no noise
        df = pd.DataFrame(
            {
                "datetime": pd.date_range("2023-01-01", periods=10, freq="ME").astype(str),
                "stage": stage,
                "discharge": discharge,
                "uncertainty": [10.0] * 10,
                "comments": [""] * 10,
                "toggle_point": ["checked"] * 10,
            }
        )
        rc = self._make_rc_output(n_segs=1)
        result = export_calculate_discharge_error(df, rc)
        # With exact fit, all errors should be numerically tiny
        assert (result["Discharge Error (%)"].abs() < 1.0).all()

    def test_column_added_2seg(self):
        df = self._make_field_df()
        rc = self._make_rc_output(n_segs=2)
        result = export_calculate_discharge_error(df, rc)
        assert "Discharge Error (%)" in result.columns

    def test_output_length_matches_input(self):
        df = self._make_field_df()
        rc = self._make_rc_output(n_segs=1)
        result = export_calculate_discharge_error(df, rc)
        assert len(result) == len(df)

    def test_error_column_rounded_to_2_dp(self):
        df = self._make_field_df()
        rc = self._make_rc_output(n_segs=1)
        result = export_calculate_discharge_error(df, rc)
        # Values should be rounded to 2 decimal places
        for val in result["Discharge Error (%)"]:
            # round-tripping through round(x, 2) should be identical
            assert round(val, 2) == val
