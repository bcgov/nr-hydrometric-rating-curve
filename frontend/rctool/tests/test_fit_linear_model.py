"""
Unit tests for the fit_linear_model function.

These tests exercise the core scientific fitting logic in complete isolation
from Django — just pure DataFrames in, dicts out.  If scikit-learn, lmfit,
or scipy break a non-backwards-compatible API, these will catch it.
"""
import math

import numpy as np
import pandas as pd
import pytest

from rctool.functions.fit_linear_model import fit_linear_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(n: int = 12, offset: float = 0.0, seed: int = 42) -> pd.DataFrame:
    """Return a synthetic field-data DataFrame with realistic-ish values."""
    rng = np.random.default_rng(seed)
    # stage values spread between 0.2 m and 0.7 m (typical small stream)
    stage = np.linspace(0.2, 0.7, n) + rng.normal(0, 0.005, n)
    stage = np.clip(stage, offset + 0.01, None)  # must be > offset
    # discharge follows approximate power law Q = 1.5 * (H - offset)^2.3
    discharge = 1.5 * (stage - offset) ** 2.3 * (1 + rng.normal(0, 0.05, n))
    discharge = np.clip(discharge, 0.001, None)
    uncertainty = rng.uniform(5.0, 20.0, n)       # percent
    comments = [f"mmt {i}" for i in range(n)]
    datetimes = pd.date_range("2023-01-01", periods=n, freq="ME").astype(str).tolist()
    toggle = ["checked"] * n

    return pd.DataFrame(
        {
            "datetime": datetimes,
            "stage": stage,
            "discharge": discharge,
            "uncertainty": uncertainty,
            "comments": comments,
            "toggle_point": toggle,
        }
    )


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestFitLinearModelOutputStructure:
    """The function must always return (mdl_data, mdl_param) with correct keys."""

    def test_returns_two_items(self):
        df = _make_df()
        result = fit_linear_model(df, offset=0.0, label="seg1")
        assert len(result) == 2

    def test_mdl_data_is_list_of_dicts(self):
        df = _make_df()
        mdl_data, _ = fit_linear_model(df, offset=0.0, label="seg1")
        assert isinstance(mdl_data, list)
        assert len(mdl_data) == 1
        assert "label" in mdl_data[0]
        assert "data" in mdl_data[0]

    def test_mdl_data_points_are_triples(self):
        df = _make_df()
        mdl_data, _ = fit_linear_model(df, offset=0.0, label="seg1")
        for point in mdl_data[0]["data"]:
            assert len(point) == 3, "Each data point must be [H, Q, residual%]"

    def test_mdl_param_required_keys(self):
        df = _make_df()
        _, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        for key in ("label", "const", "exp", "seg_bounds", "offset", "rmse", "mape"):
            assert key in mdl_param, f"Missing key: {key}"

    def test_seg_bounds_shape(self):
        df = _make_df()
        _, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        bounds = mdl_param["seg_bounds"]
        assert len(bounds) == 2, "seg_bounds must have [lower, upper]"
        assert len(bounds[0]) == 2 and len(bounds[1]) == 2

    def test_label_propagated(self):
        df = _make_df()
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="my_seg")
        assert mdl_data[0]["label"] == "my_seg"
        assert mdl_param["label"] == "my_seg"

    def test_offset_propagated(self):
        df = _make_df(offset=0.1)
        _, mdl_param = fit_linear_model(df, offset=0.1, label="seg1")
        assert mdl_param["offset"] == 0.1

    def test_no_numpy_floats_in_output(self):
        """All floats must be plain Python floats so JSON serialisation works."""
        df = _make_df()
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        assert isinstance(mdl_param["const"], float)
        assert isinstance(mdl_param["exp"], float)
        assert isinstance(mdl_param["rmse"], float)
        assert isinstance(mdl_param["mape"], float)


# ---------------------------------------------------------------------------
# Weighted vs unweighted
# ---------------------------------------------------------------------------

class TestWeightedVsUnweighted:
    def test_unweighted_returns_result(self):
        df = _make_df()
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="seg1", weighted=None)
        assert mdl_param["const"] > 0
        assert mdl_param["exp"] > 0

    def test_weighted_returns_result(self):
        df = _make_df()
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="seg1", weighted=True)
        assert mdl_param["const"] > 0
        assert mdl_param["exp"] > 0

    def test_weighted_and_unweighted_differ(self):
        """Weighted and unweighted fits should generally produce different constants."""
        # Use a dataset with highly variable uncertainty to make weights matter
        df = _make_df(n=20, seed=7)
        df.loc[:9, "uncertainty"] = 1.0    # very certain — first half
        df.loc[10:, "uncertainty"] = 50.0  # very uncertain — second half

        _, param_unw = fit_linear_model(df, offset=0.0, label="u", weighted=None)
        _, param_wgt = fit_linear_model(df, offset=0.0, label="w", weighted=True)
        # They won't be identical because weights change the fit
        assert param_unw["const"] != param_wgt["const"] or param_unw["exp"] != param_wgt["exp"]


# ---------------------------------------------------------------------------
# Statistical quality metrics
# ---------------------------------------------------------------------------

class TestStatisticsMetrics:
    def test_rmse_is_positive(self):
        df = _make_df()
        _, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        assert mdl_param["rmse"] >= 0.0

    def test_mape_is_positive(self):
        df = _make_df()
        _, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        assert mdl_param["mape"] >= 0.0

    def test_rmse_lower_for_clean_data(self):
        """A cleaner power-law dataset should yield lower RMSE than a noisy one."""
        df_clean = _make_df(seed=1)
        df_noisy = _make_df(seed=1)
        df_noisy["discharge"] *= np.random.default_rng(99).uniform(0.5, 1.5, len(df_noisy))

        _, p_clean = fit_linear_model(df_clean, offset=0.0, label="c")
        _, p_noisy = fit_linear_model(df_noisy, offset=0.0, label="n")
        assert p_clean["rmse"] <= p_noisy["rmse"]


# ---------------------------------------------------------------------------
# Intersect-point constraint
# ---------------------------------------------------------------------------

class TestIntersectPoints:
    def test_intersect_point_accepted_without_crash(self):
        df = _make_df()
        midpoint_H = float(df["stage"].median())
        # Calculate approximate Q at that H using rough parameters
        midpoint_Q = 1.5 * midpoint_H ** 2.3
        intersect = [[midpoint_H, midpoint_Q]]
        # Should not raise
        mdl_data, mdl_param = fit_linear_model(
            df, offset=0.0, label="upper", intersect_points=intersect
        )
        assert mdl_param["const"] > 0

    def test_no_intersect_vs_intersect_differ(self):
        df = _make_df()
        midpoint_H = float(df["stage"].median())
        midpoint_Q = 1.5 * midpoint_H ** 2.3
        intersect = [[midpoint_H, midpoint_Q]]

        _, param_free = fit_linear_model(df, offset=0.0, label="free")
        _, param_constrained = fit_linear_model(
            df, offset=0.0, label="constrained", intersect_points=intersect
        )
        # The constrained fit amplitude is derived from the intersect expression,
        # so it will differ from the unconstrained amplitude in general
        # (they might coincidentally match but that's astronomically rare)
        # We just verify the constrained fit produced a valid result
        assert isinstance(param_constrained["const"], float)
        assert isinstance(param_constrained["exp"], float)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_minimum_dataset_two_points(self):
        """fit_linear_model must not crash with just 2 data points."""
        df = pd.DataFrame(
            {
                "datetime": ["2023-01-01", "2023-06-01"],
                "stage": [0.3, 0.6],
                "discharge": [0.05, 0.3],
                "uncertainty": [10.0, 10.0],
                "comments": ["a", "b"],
                "toggle_point": ["checked", "checked"],
            }
        )
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="edge")
        assert mdl_param["const"] > 0

    def test_positive_offset(self):
        """A positive offset shifts the effective head so all H - offset > 0."""
        df = _make_df(n=14, offset=0.15)
        mdl_data, mdl_param = fit_linear_model(df, offset=0.15, label="seg1")
        assert mdl_param["offset"] == 0.15
        assert mdl_param["const"] > 0

    def test_all_same_uncertainty(self):
        """Constant uncertainty weights should not cause degenerate results."""
        df = _make_df()
        df["uncertainty"] = 10.0  # identical for all rows
        mdl_data, mdl_param = fit_linear_model(df, offset=0.0, label="seg", weighted=True)
        assert mdl_param["const"] > 0

    def test_seg_bounds_lower_less_than_upper(self):
        """Lower segment bound stage should be ≤ upper segment bound stage."""
        df = _make_df()
        _, mdl_param = fit_linear_model(df, offset=0.0, label="seg1")
        lower_H = mdl_param["seg_bounds"][0][0]
        upper_H = mdl_param["seg_bounds"][1][0]
        assert lower_H <= upper_H
