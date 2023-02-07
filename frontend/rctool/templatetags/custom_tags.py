# django modules
from django import template
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
from lmfit.models import PowerLawModel
from collections import defaultdict
from ..functions.fit_linear_model import fit_linear_model

register = template.Library()

@register.simple_tag
def count_segments(num_seg):
	num_seg += 1
	return num_seg

@register.simple_tag
def create_table(t_data):
	table_dict = {'headings':t_data[0], 'data':t_data[1:]}
	return table_dict
	

@register.simple_tag
def fit_data(field_data, offsets, breakpoint1=None, rc_data=None, n_seg=None, adjust_seg=None, *args):

	# Initialize and filter
	df_field_raw = pd.DataFrame(field_data[1:], columns=field_data[0])
	df_field = df_field_raw[df_field_raw['toggle_point'] == True]

	# add to output list
	field_data = [[a,b] for a, b in zip(df_field['stage'].tolist(), df_field['discharge'].tolist())]
	rc_data_output = [{'label': 'field', 'data': field_data}] # if n_seg = 0, this will be the output
	rc_param_output = None # if n_seg = 0, this will be the output


	"""---------------------------------
	INITIALIZE RATING CURVE SEGMENTS
	------------------------------------"""
	# CONDITION: For when a user wants to add a new segment
	# if n_seg is input into this function, this code will be called
	
	# calculate the boundaries of each fit
	x_step = 5
	x_min = df_field['discharge'].min()
	x_max = df_field['discharge'].max()
	rmse_best = 10000.00 # initialize with something unrealistically high

	if n_seg == 1:
		[mdl_data, mdl_param] = fit_linear_model(df_field, offsets[0], 'model segment 1')
		rc_data_output = rc_data_output + mdl_data
		rc_param_output = [mdl_param['wgt']]

	elif n_seg == 2:
		#check if breakpoint exists and is within bounds of fitting data
		if breakpoint1 and breakpoint1 > x_min and breakpoint1 < x_max:
			df_lower = df_field[df_field['discharge'] <= breakpoint1]
			df_upper = df_field[df_field['discharge'] >= df_lower['discharge'].iloc[-1]] # creates df of all values greater than last point of first field data df (so we have an intersect point)

			if len(df_lower['discharge']) > 1 and len(df_upper['discharge']) > 1: #breaks if trying to fit a line through one point
				[mdl_data_lower, mdl_param_lower] = fit_linear_model(df_lower, offsets[0], 'model segment 1')
				intersect_point_1 = [[mdl_data_lower[0]['data'][-1][0], mdl_data_lower[0]['data'][-1][1]]] # retrieve last point of first model segment for starting point of second segment
				[mdl_data_upper, mdl_param_upper] = fit_linear_model(df_upper, offsets[1], 'model segment 2', intersect_point_1)
				best_rc_data = mdl_data_lower + mdl_data_upper
				best_rc_param = [mdl_param_lower['wgt'], mdl_param_upper['wgt']]

		# if no breakpoint specified, iterate between numerous breakpoints and optimize fit
		else:
			for k in np.arange(x_min, x_max, x_step):
				df_lower = df_field[df_field['discharge'] <= k]
				df_upper = df_field[df_field['discharge'] >= df_lower['discharge'].iloc[-1]] 
				if len(df_lower['discharge']) > 1 and len(df_upper['discharge']) > 1:
					[mdl_data_lower, mdl_param_lower] = fit_linear_model(df_lower, offsets[0], 'model segment 1')
					intersect_point_1 = [[mdl_data_lower[0]['data'][-1][0], mdl_data_lower[0]['data'][-1][1]]]
					[mdl_data_upper, mdl_param_upper] = fit_linear_model(df_upper, offsets[1], 'model segment 2', intersect_point_1)
					rmse = np.mean([mdl_param_lower['wgt']['rmse'], mdl_param_upper['wgt']['rmse']])

					if rmse_best > rmse:
						rmse_best = rmse
						best_rc_data = mdl_data_lower + mdl_data_upper
						best_rc_param = [mdl_param_lower['wgt'], mdl_param_upper['wgt']]

		rc_data_output = rc_data_output + best_rc_data
		rc_param_output = best_rc_param


	rc_dict = {'data':rc_data_output, 'parameters':rc_param_output}
			

	# elif n_seg == 3:
	# 	for k in np.arange(x_min, x_max, x_step):
	# 		df_lower = df_field[df_field['discharge'] <= k]
	# 		if len(df_lower['discharge']) > 1: #breaks if trying to fit a line through one point
	# 			[mdl_data_lower, mdl_param_lower] = fit_linear_model(df_lower, offset1, 'model segment 1')

	# 			for j in np.arange(k, x_max, x_step):
	# 				df_middle = df_field[(df_field['discharge'] >= k) & (df_field['discharge'] <= j)]
	# 				df_upper = df_field[df_field['discharge'] >= j]

	# 				if len(df_middle['discharge']) > 1 and len(df_upper['discharge']) > 1:
	# 					[mdl_data_middle, mdl_param_middle] = fit_linear_model(df_middle, offset1, 'model segment 2')
	# 					[mdl_data_upper, mdl_param_upper] = fit_linear_model(df_upper, offset1, 'model segment 3')
	# 					rmse = np.mean([mdl_param_lower['wgt']['rmse'],
	# 									mdl_param_middle['wgt']['rmse'],
	# 									mdl_param_upper['wgt']['rmse']])

	# 					if rmse_best > rmse:
	# 						best_rc_data = mdl_data_lower + mdl_data_middle + mdl_data_upper
	# 						best_rc_param = [mdl_param_lower['wgt'], mdl_param_middle['wgt'], mdl_param_upper['wgt']]
	# 	rc_data_output = rc_data_output + best_rc_data
	# 	rc_param_output = best_rc_param



	return rc_dict
	



