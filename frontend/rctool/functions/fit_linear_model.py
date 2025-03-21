import pandas as pd
import numpy as np
from lmfit import models, Parameters
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
import math


def fit_linear_model(df, offset, label, weighted=None, intersect_points=None, *args):
    # input dataframe with columns H, Q, and U
    df_data = df.copy()
    df_data.drop(["datetime", "comments", "toggle_point"], axis=1, inplace=True)
    df_data = df_data.rename(
        columns={"discharge": "Q", "stage": "H", "uncertainty": "U"}
    )
    df_data.sort_values("H", inplace=True)

    # Apply offset
    df_data["H0"] = df_data["H"] - offset

    # init model
    plm = models.PowerLawModel()
    # set initial condition for model parameters
    # params = plm.guess(df_data['Q'], x=df_data['H0'])

    # JOHNS CODE FOR GUESSING OFFSET
    params = Parameters()
    params.add("amplitude", value=0.1, min=0.001, max=100)
    params.add("exponent", value=2, min=0.5, max=5)

    # add constraint so model passes through intersect points
    if intersect_points:
        for idx, point in enumerate(intersect_points):
            constraint_name = "amplitude"
            constraint_expression = "{0:g}*{1:g}**(-(exponent))".format(
                point[1], point[0] - offset
            )
            params.add(constraint_name, expr=constraint_expression)

    result = plm.fit(df_data["Q"], params, x=df_data["H0"])
    
    unw_const = float(result.best_values["amplitude"])
    unw_exp = float(result.best_values["exponent"])
    unw_best = result.best_fit

    unw_residual = list(
        100 * (np.array(unw_best) - np.array(df_data["Q"])) / np.array(df_data["Q"])
    )
    unw_seg_nodes = [
        [np.array(df_data["H"])[0], unw_best[0]],
        [np.array(df_data["H"])[-1], unw_best[-1]],
    ]

    # set uncertianty to %
    df_data["U"] = df_data["U"].apply(lambda x: x / 100.0)
    # set weights as 1 - % unc
    df_data["W"] = df_data["U"].apply(lambda x: 1 - x)

    # try weighting
    result = plm.fit(df_data["Q"], params, x=df_data["H0"], weights=df_data["W"])
    wgt_const = float(result.best_values["amplitude"])
    wgt_exp = float(result.best_values["exponent"])
    wgt_best = result.best_fit
    wgt_sigs = result.eval_uncertainty(sigma=2)
    wgt_residual = list(
        100 * (np.array(wgt_best) - np.array(df_data["Q"])) / np.array(df_data["Q"])
    )
    wgt_seg_nodes = [
        [np.array(df_data["H"])[0], wgt_best[0]],
        [np.array(df_data["H"])[-1], wgt_best[-1]],
    ]

    # calculate statistical parameters to analyze goodness of fit
    unw_mse = mean_squared_error(df_data["Q"], unw_best)
    unw_rmse = math.sqrt(unw_mse)
    unw_mape = mean_absolute_percentage_error(df_data["Q"], unw_best) * 100.0

    wgt_mse = mean_squared_error(df_data["Q"], wgt_best)
    wgt_rmse = math.sqrt(wgt_mse)
    wgt_mape = mean_absolute_percentage_error(df_data["Q"], wgt_best) * 100.0

    # Process and ship output
    mdl_param = {
        "unw": {
            "label": label,
            "const": unw_const,
            "exp": unw_exp,
            "seg_bounds": unw_seg_nodes,
            "offset": offset,
            "rmse": unw_rmse,
            "mape": unw_mape,
        },
        "wgt": {
            "label": label,
            "const": wgt_const,
            "exp": wgt_exp,
            "seg_bounds": wgt_seg_nodes,
            "offset": offset,
            "rmse": wgt_rmse,
            "mape": wgt_mape,
        },
    }

    if weighted:
        mdl_param = {
            "label": label,
            "const": wgt_const,
            "exp": wgt_exp,
            "seg_bounds": wgt_seg_nodes,
            "offset": offset,
            "rmse": wgt_rmse,
            "mape": wgt_mape,
        }
        wgt_data = [
            [float(a), float(b), float(c)] for a, b, c in zip(df_data["H"].tolist(), wgt_best, wgt_residual)
        ]
        mdl_data = [{"label": label, "data": wgt_data}]
    else:
        # unweighted
        mdl_param = {
            "label": label,
            "const": unw_const,
            "exp": unw_exp,
            "seg_bounds": unw_seg_nodes,
            "offset": offset,
            "rmse": unw_rmse,
            "mape": unw_mape,
        }
        unw_data = [
            [float(a), float(b), float(c)] for a, b, c in zip(df_data["H"].tolist(), unw_best, unw_residual)
        ]
        mdl_data = [{"label": label, "data": unw_data}]

    return mdl_data, mdl_param
