import pandas as pd
import numpy as np
from lmfit import models, Parameters
from sklearn.metrics import mean_squared_error
import math


def fit_linear_model(df, offset, label, weighted=None, intersect_points=None, *args):

    # input dataframe with columns H, Q, and U
    df_data = df.copy()
    df_data.drop(['datetime', 'comments', 'toggle_point'], axis=1, inplace=True)
    df_data = df_data.rename(columns={'discharge': 'Q', 'stage':'H', 'uncertainty':'U'})
    df_data.sort_values('H', inplace=True)

    # Apply offset
    df_data['H0'] = df_data['H'] - offset

    # init model
    plm = models.PowerLawModel()
    # set initial condition for model parameters
    # params = plm.guess(df_data['Q'], x=df_data['H0'])
    
    # JOHNS CODE FOR GUESSING OFFSET
    params = Parameters()
    params.add('amplitude', value=0.1, min=0.001, max=100)
    params.add('exponent', value=2, min=0.5, max=5)



    # add constraint so model passes through intersect points
    if intersect_points:
        for idx, point in enumerate(intersect_points):
            constraint_name = 'amplitude'
            constraint_expression = '{0:g}*{1:g}**(-(exponent))'.format(point[1], point[0] - offset)
            params.add(constraint_name, expr=constraint_expression)
    
    result = plm.fit(df_data['Q'], params, x=df_data['H0'])
        

    unw_const = round(result.best_values['amplitude'], 4)
    unw_exp = round(result.best_values['exponent'], 4)
    unw_best = result.best_fit
    unw_residual = list( 100 * (np.array(unw_best) - np.array(df_data['Q']) ) / np.array(df_data['Q']) )
    unw_seg_nodes = [[round(np.array(df_data['H'])[0], 3), round(unw_best[0], 3)], [round(np.array(df_data['H'])[-1], 3), round(unw_best[-1], 3)]]

    # set uncertianty to %
    df_data['U'] = df_data['U'].apply(lambda x: x / 100.)
    # set weights as 1 - % unc
    df_data['W'] = df_data['U'].apply(lambda x: 1 - x)
    # try weighting
    result = plm.fit(df_data['Q'], params, x=df_data['H0'], weights=df_data['W'])
    wgt_const = round(result.best_values['amplitude'], 4)
    wgt_exp = round(result.best_values['exponent'], 4)
    wgt_best = result.best_fit
    wgt_sigs = result.eval_uncertainty(sigma=2)
    wgt_residual = list( 100 * (np.array(wgt_best) - np.array(df_data['Q']) ) / np.array(df_data['Q']) )
    wgt_seg_nodes = [[round(np.array(df_data['H'])[0], 3), round(wgt_best[0], 3)], [round(np.array(df_data['H'])[-1], 3), round(wgt_best[-1], 3)]]

    # calculate statistical parameters to analyze goodness of fit
    unw_mse = mean_squared_error(df_data['Q'], unw_best)
    unw_rmse = round(math.sqrt(unw_mse), 3)

    wgt_mse = mean_squared_error(df_data['Q'], wgt_best)
    wgt_rmse = round(math.sqrt(wgt_mse), 3)

    # Process and ship output
    mdl_param = {
        'unw': {'label': label ,'const': unw_const, 'exp': unw_exp, 'seg_bounds':unw_seg_nodes, 'offset': offset, 'rmse': unw_rmse},
        'wgt': {'label': label, 'const': wgt_const,'exp': wgt_exp, 'seg_bounds':wgt_seg_nodes,'offset': offset, 'rmse': wgt_rmse}
    }

    if weighted:
        mdl_param = {'label': label, 'const': wgt_const,'exp': wgt_exp, 'seg_bounds':wgt_seg_nodes,'offset': offset, 'rmse': wgt_rmse}
        wgt_data = [[a,b, c] for a, b, c in zip(df_data['H'].tolist(), wgt_best, wgt_residual)] 
        mdl_data = [{'label': label, 'data': wgt_data}]
    else:
        # unweighted
        mdl_param = {'label': label ,'const': unw_const, 'exp': unw_exp, 'seg_bounds':unw_seg_nodes, 'offset': offset, 'rmse': unw_rmse}
        unw_data = [[a,b, c] for a, b, c in zip(df_data['H'].tolist(), unw_best, unw_residual)] 
        mdl_data = [{'label': label, 'data': unw_data}]

    return mdl_data, mdl_param



