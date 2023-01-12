from calendar import c
from cmath import exp
from selectors import EpollSelector
import os
import pandas as pd
import numpy as np
import csv
import ast
import math
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.urls import reverse
from django.template.loader import get_template
from .forms import import_rc_data, develop_rc, export_rc_data
from .functions.fit_linear_model import fit_linear_model
from json import dumps, loads
import json
from mysite.utils import render_to_pdf
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import base64
import io, base64


def index(response):
    return render(response, "rctool/base.html", {})

def home(response):
    return render(response, "rctool/home.html", {})

def account(response):
    return render(response, "rctool/account.html", {})

def about(response):
    return render(response, "rctool/about.html", {})



def rctool_import(request, tour_request_id=0):
    context = {}
    context['tour_request_id'] = tour_request_id

    if request.method == "POST":
        # If user is on the tour, upload test data
        if tour_request_id == 1:
            context['form'] = import_rc_data()
            try:
                df = pd.read_csv('test_files/capilano_field_data.csv') # Using this for now while we work on the develop page
                df['toggle_point'] = 'checked'
                df['datetime'] = df['datetime'].astype('str')
                context['headings'] = list(df.columns.values)
                context['table_data'] = df.values.tolist()
                context['raw_field_data'] = df.to_json(date_format='iso')
            except Exception as e:
                messages.error(request,"An unexpected error occcured.")
            return render(request, "rctool/rctool/import/rctool_import.html", context)

        # if not on a tour, upload their dataset
        import_form = import_rc_data(request.POST, request.FILES)
        if import_form.is_valid():
            fheader_row = import_form.cleaned_data["header_row"] - 1

            try:
                csv_file = import_form.cleaned_data['csv_upload']
                # Check if it is a csv file
                if not csv_file.name.endswith('.csv') and not csv_file.name.endswith('.dat'):
                    messages.error(request, 'Error: incorrect file type.')
                #Check if file size is too large
                if csv_file.multiple_chunks() or csv_file.size > 200000:
                    messages.error(request,"Uploaded file is too big (%.2f MB)." % (csv_file.size/(1000*1000),)) # change file limit size?

                ok_columns = ['datetime', 'stage', 'discharge', 'uncertainty', 'comments', 'comment','Datetime', 'DateTime', 'Stage', 'Discharge', 'Uncertainty', 'Comments', 'Comment']
                df = pd.read_csv(csv_file, usecols=lambda c: c.lower() in ok_columns, header=fheader_row, skip_blank_lines=True)
                df.columns = [x.lower() for x in df.columns]
                df = df[df['stage'].notna()]
                df = df[df['discharge'].notna()]

                
                # get filename
                csv_filename, ext = os.path.splitext(csv_file.name)
                context['filename'] = csv_filename

                # handle possible uncertainty errors
                if 'uncertainty' not in df:
                    df['uncertainty'] = 0
                df['uncertainty'].fillna(0.5, inplace=True)

                # if user did not upload comments column, of if the user uploaded a column called comment
                if 'comment' not in df and 'comments' not in df:
                    df['comments'] = '-'
                if 'comment' in df:
                    df['comments'] = df['comment']
                    df = df.drop('comment', 1)
                df['comments'].fillna('-', inplace=True)
                # remove , from any comments (was causing issues)
                df['comments'] = df['comments'].str.replace(',',' ;')
                

                df.dropna(subset=['stage', 'discharge'], inplace=True)
                df['datetime'] = df['datetime'].astype('str')
                context['headings'] = list(df.columns.values)
                context['table_data'] = df.values.tolist()
                context['raw_field_data'] = df.to_json(date_format='iso')
                context['form'] = import_form

            except Exception as e:
                messages.error(request,"Unable to upload file. "+repr(e))
                context['form'] = import_rc_data()
            return render(request, "rctool/rctool/import/rctool_import.html", context)
    else:
        context['form'] = import_rc_data()

    return render(request, "rctool/rctool/import/rctool_import.html", context)



def autofit_data(field_data, offsets, breakpointH=None, rc_data=None, n_seg=None, weighted=None, adjust_seg=None, *args):

    # Initialize and filter
    sidepanel_message = None
    df_field = field_data.copy()
    df_field = field_data[field_data['toggle_point'] == 'checked']

    # add to output list
    field_data = [[a,b,c] for a, b, c in zip(df_field['stage'].tolist(), df_field['discharge'].tolist(), df_field['toggle_point'].tolist())]
    rc_data_output = [{'label': 'field', 'data': field_data}] # if n_seg = 0, this will be the output
    rc_param_output = None # if n_seg = 0, this will be the output
    best_rc_data = None
    # remove if row already exists
    df_field = df_field.drop_duplicates(subset=['stage', 'discharge'], keep='first')

    
    # calculate the boundaries of each fit
    x_min = df_field['stage'].min()
    x_max = df_field['stage'].max()
    x_step = ( x_max - x_min ) / 50
    min_fitting_points = math.ceil(len(df_field['stage'])*0.15) # add constraint so fitting line has to pass through at least 20% of points
    rmse_best = 10000.00 # initialize with something unrealistically high

    if n_seg == 1:
        [mdl_data, mdl_param] = fit_linear_model(df_field, offsets[0], 'model segment 1', weighted)
        best_rc_data = mdl_data
        best_rc_param = mdl_param

        # add boundary points for 1.5 the max stage and 0.75 the lowest stage (but first check offset)
        if df_field['stage'].min() * 0.75 <= offsets[0]:
            # will cause issues, dont extend segment endpoints
            pass
        else:
            lower_point_H = round(df_field['stage'].min() * 0.75, 4)
            lower_point_Q = best_rc_param['const']*( lower_point_H - offsets[0]) ** best_rc_param['exp']
            if round(lower_point_Q, 4) != 0:
                lower_point_Q = round(lower_point_Q, 4)
            upper_point_H = round(df_field['stage'].max() * 1.5, 4)
            upper_point_Q = round(best_rc_param['const']*( upper_point_H - offsets[0]) ** best_rc_param['exp'], 4)

            best_rc_data[0]['data'].insert(0, [lower_point_H, lower_point_Q, 0])
            best_rc_data[0]['data'].append([upper_point_H, upper_point_Q, 0])
            best_rc_param['seg_bounds'][0] = [lower_point_H, lower_point_Q]
            best_rc_param['seg_bounds'][1] = [upper_point_H, upper_point_Q]

        rc_data_output = rc_data_output + best_rc_data
        rc_param_output = [best_rc_param]


    elif n_seg == 2:
        # sometimes none of the conditions pass or 2 segments is not possible, in this case just return 1 segment and an alert
        try:
            #check if breakpoint exists and is within bounds of fitting data
            if breakpointH and breakpointH > x_min and breakpointH < x_max:
                # create dataframes to fit rating segments
                df_lower = df_field[df_field['stage'] <= breakpointH]
                df_upper = df_field[df_field['stage'] >= breakpointH] # creates df of all values greater than last point of first field data df (so we have an intersect point)

                if len(df_lower['stage']) > 1 and len(df_upper['stage']) > 1: #breaks if trying to fit a line through one point
                    # fit lower
                    [mdl_data_lower, mdl_param_lower] = fit_linear_model(df_lower, offsets[0], 'model segment 1', weighted)

                    # calculate breakpoint Q value from breakpoint H value
                    breakpointQ = mdl_param_lower['const']*( breakpointH - mdl_param_lower['offset']) ** mdl_param_lower['exp']
                    # add breakpoint to lower data and parameters
                    mdl_data_lower[0]['data'].append([breakpointH, breakpointQ, 0])
                    intersect_point_1 = [[mdl_data_lower[0]['data'][-1][0], mdl_data_lower[0]['data'][-1][1]]] # retrieve last point of first model segment for starting point of second segment
                    mdl_param_lower['seg_bounds'][1] = [breakpointH, breakpointQ]

                    # fit upper
                    [mdl_data_upper, mdl_param_upper] = fit_linear_model(df_upper, offsets[1], 'model segment 2', weighted, intersect_point_1)

                    # add breakpoint to upper data and parameters
                    mdl_data_upper[0]['data'].insert(0, [breakpointH, breakpointQ, 0])
                    mdl_param_upper['seg_bounds'][0] = [breakpointH, breakpointQ]

                    # prepaire output
                    best_rc_data = mdl_data_lower + mdl_data_upper
                    best_rc_param = [mdl_param_lower, mdl_param_upper]

                    # add boundary points for 1.5 the max stage and 0.75 the lowest stage (but first check offset)
                    if df_field['stage'].min() * 0.75 <= offsets[0]:
                        # causes issues, dont extend rating curve
                        pass
                    else:
                        # extend rating curve
                        lower_point_H = round(df_field['stage'].min() * 0.75, 4)
                        upper_point_H = round(df_field['stage'].max() * 1.5, 4)
                        lower_point_Q = best_rc_param[0]['const']*( lower_point_H - offsets[0]) ** best_rc_param[0]['exp']
                        upper_point_Q = round(best_rc_param[1]['const']*( upper_point_H - offsets[1]) ** best_rc_param[1]['exp'], 4)
                        if round(lower_point_Q, 4) != 0:
                            lower_point_Q = round(lower_point_Q, 4)
                        best_rc_data[0]['data'].insert(0, [lower_point_H, lower_point_Q, 0])
                        best_rc_param[0]['seg_bounds'][0] = [lower_point_H, lower_point_Q]
                        best_rc_data[1]['data'].append([upper_point_H, upper_point_Q, 0])
                        best_rc_param[1]['seg_bounds'][1] = [upper_point_H, upper_point_Q]


            # if no breakpoint specified, iterate between numerous breakpoints and optimize fit
            else:
                for k in np.arange(x_min, x_max, x_step):

                    df_lower = df_field[df_field['stage'] <= k]
                    
                    if len(df_lower['stage']) > min_fitting_points:
                        [mdl_data_lower, mdl_param_lower] = fit_linear_model(df_lower, offsets[0], 'model segment 1', weighted)

                        intersect_point_H = round(k, 4)
                        intersect_point_Q = round(mdl_param_lower['const']*( intersect_point_H - mdl_param_lower['offset']) ** mdl_param_lower['exp'], 4)

                        # add breakpoint to lower data and parameters
                        mdl_data_lower[0]['data'].append([intersect_point_H, intersect_point_Q, 0])
                        intersect_point_1 = [[mdl_data_lower[0]['data'][-1][0], mdl_data_lower[0]['data'][-1][1]]] # retrieve last point of first model segment for starting point of second segment
                        mdl_param_lower['seg_bounds'][1] = [intersect_point_H, intersect_point_Q]
                        df_upper = df_field[df_field['stage'] >= intersect_point_H]

                        # test constraints
                        if len(df_upper['stage']) > min_fitting_points:
                            [mdl_data_upper, mdl_param_upper] = fit_linear_model(df_upper, offsets[1], 'model segment 2', weighted, intersect_point_1)
                            # add breakpoint to upper data and parameters
                            mdl_data_upper[0]['data'].insert(0, [intersect_point_H, intersect_point_Q, 0])
                            mdl_param_upper['seg_bounds'][0] = [intersect_point_H, intersect_point_Q]

                            rmse = np.mean([mdl_param_lower['rmse'], mdl_param_upper['rmse']])

                            if rmse_best > rmse:
                                rmse_best = round(rmse,3)
                                best_rc_data = mdl_data_lower + mdl_data_upper
                                best_rc_param = [mdl_param_lower, mdl_param_upper]


                # add boundary points for 1.5 the max stage and 0.75 the lowest stage
                if offsets[0] <= df_field['stage'].min() * 0.75:
                    lower_point_H = round(df_field['stage'].min() * 0.75, 4)
                    lower_point_Q = best_rc_param[0]['const']*( lower_point_H - offsets[0]) ** best_rc_param[0]['exp']
                    if round(lower_point_Q, 4) != 0:
                        lower_point_Q = round(lower_point_Q, 4)
                    upper_point_H = round(df_field['stage'].max() * 1.5, 4)
                    upper_point_Q = round(best_rc_param[1]['const']*( upper_point_H - offsets[1]) ** best_rc_param[1]['exp'], 4)
                    best_rc_data[0]['data'].insert(0, [lower_point_H, lower_point_Q, 0])
                    best_rc_param[0]['seg_bounds'][0] = [lower_point_H, lower_point_Q]
                    best_rc_data[1]['data'].append([upper_point_H, upper_point_Q, 0])
                    best_rc_param[1]['seg_bounds'][1] = [upper_point_H, upper_point_Q]

            rc_data_output = rc_data_output + best_rc_data
            rc_param_output = best_rc_param

        except Exception as e:
            # when 2 segs dosnt work...
            print('ERROR!!', e)
            sidepanel_message = {'error_title': 'Error Auto-Fitting Rating Curve', 'error_text': 'Could not fit second segment, please specify a breakpoint and try again.'}
            [mdl_data, mdl_param] = fit_linear_model(df_field, offsets[0], 'model segment 1')
            rc_data_output = rc_data_output + mdl_data
            rc_param_output = [mdl_param]

    # check if parameters are too high / low
    for param in rc_param_output:
        if param['exp'] < 1:
            sidepanel_message = {'error_title': 'Warning', 'error_text': 'Exponent for {} is too low.'.format(param['label'])}
        elif param['exp'] > 4:
            sidepanel_message = {'error_title': 'Warning', 'error_text': 'Exponent for {} is too high.'.format(param['label'])}
        else:
            pass

    rc_dict = {'data':rc_data_output, 'parameters':rc_param_output}

    return rc_dict, sidepanel_message



def rctool_develop_initialize(request):
    context = {}

    if request.method == 'POST':

        # if a previous session is initiaizing...
        try:
            import_form = import_rc_data(request.POST, request.FILES)
            if import_form.is_valid():
                fheader_row = import_form.cleaned_data["header_row"] - 1
                csv_file = import_form.cleaned_data['csv_upload']
                if not csv_file.name.endswith('.csv') and not csv_file.name.endswith('.dat'):
                    messages.error(request, 'Error: incorrect file type.')
                if csv_file.multiple_chunks()or csv_file.size > 20000:
                    messages.error(request,"Uploaded file is too big (%.2f MB)." % (csv_file.size/(1000*1000),)) # change file limit size?
                df = pd.read_csv(csv_file)

                # preprocess data from previous session
                data_raw_lst = df['data'].values.tolist()
                data_raw_lst = list(map(ast.literal_eval, data_raw_lst))
                data_rc_lst = data_raw_lst[:-1] # extract rc data from data dict
                fielddatacsv_dat = data_raw_lst[-1]
                fielddatacsv_df = pd.DataFrame(fielddatacsv_dat, columns = ['datetime', 'discharge', 'stage', 'uncertainty', 'comments', 'toggle_point'])
                parameter_raw_lst = df['parameters'].values.tolist()
                parameter_rc_lst = parameter_raw_lst[:-2] # remove problematic nan value
                parameter_rc_lst = list(map(ast.literal_eval, parameter_rc_lst))

                offsets = [0,0]
                offsets[0] = parameter_rc_lst[0]['offset']

                if len(parameter_rc_lst) > 1:
                    offsets[1] = parameter_rc_lst[1]['offset']
                context['offsets'] = offsets
                # Format equation according to + or - offset (ie. if user enters a - offset, the equation will show (H + offset) instead of (H -- offset))
                offsets_val = offsets.copy()
                if offsets_val[0] < 0:
                    offsets_val[0] = ' + ' + str(abs(offsets_val[0]))
                    context['offsets_val'] = offsets_val
                else:
                    offsets_val[0] = ' - ' + str(abs(offsets_val[0]))
                    context['offsets_val'] = offsets_val
                if offsets_val[1] < 0:
                    offsets_val[1] = ' + ' + str(abs(offsets_val[1]))
                    context['offsets_val'] = offsets_val
                else:
                    offsets_val[1] = ' - ' + str(abs(offsets_val[1]))
                    context['offsets_val'] = offsets_val

                # round off values in parameters dict
                rc_param_rounded = []
                for rcparam_dict in parameter_rc_lst:
                    rcparam_dict['const'] = round(rcparam_dict['const'], 4)
                    rcparam_dict['exp'] = round(rcparam_dict['exp'], 4)
                    rc_param_rounded.append(rcparam_dict)

                rc_dict = {'data': data_rc_lst, 'parameters':rc_param_rounded}
                context['fielddatacsv'] = fielddatacsv_df.to_json(date_format='iso')
                context['rc'] = rc_dict
                context['table_dict'] = {'headings': fielddatacsv_df.columns.values, 'data': fielddatacsv_df.values.tolist()}
                context['n_seg'] = len(parameter_rc_lst)
                context['breakpoint1'] = None
                context['develop_tour_request_status_id'] = 0
                context['toggle_breakpoint'] = 'false'
                context['toggle_weighted_fit'] = 'false'
                context['filename'] = df['filename'][0]
                # get constraints fo input settings
                context['max_offset'] = fielddatacsv_df['stage'].min()
                # if parameter_rc_lst[0]['seg_bounds'][0][0] < fielddatacsv_df['stage'].min():
                #     context['max_offset'] = parameter_rc_lst[0]['seg_bounds'][0][0]
                # else:
                #     context['max_offset'] = fielddatacsv_df['stage'].min()



                df_filtered = fielddatacsv_df.drop_duplicates(subset=['stage'], keep='first')
                context['breakpoint_min'] = df_filtered['stage'].nsmallest(2).iloc[-1]
                context['breakpoint_max'] = df_filtered['stage'].nlargest(2).iloc[-1]

                return render(request, "rctool/rctool/develop/rctool_develop.html", context)
        except:
            pass

        # if new session...
        field_data_json = request.POST.get('pass-field-to-develop')
        field_df_raw = pd.read_json(field_data_json)
        field_df_raw['toggle_point'] = 'checked'
        field_df_raw['discharge'] = field_df_raw['discharge'].round(decimals=3)
        field_df_raw['stage'] = field_df_raw['stage'].round(decimals=3)
        field_df_raw['uncertainty'] = field_df_raw['uncertainty'].round(decimals=3)
        field_df_raw['datetime'] = field_df_raw['datetime'].apply(str)
        context['develop_tour_request_status_id'] = request.POST.get('pass-tour-status-to-develop')

    context['rc_data'] = None
    context['table_dict'] = {'headings': field_df_raw.columns.values, 'data': field_df_raw.values.tolist()}
    context['n_seg'] = 1 # this will be initialized as None and make the user enter a value, for now use 2
    # init_offsets = [None, None] # initialize at None, then optimize in autofit
    init_offsets = [0.0, 0.0]
    context['breakpoint1'] = None
    context['adjust_seg'] = None
    context['toggle_breakpoint'] = 'false'
    context['toggle_weighted_fit'] = 'false'
    weighted = None
    context['fielddatacsv'] = field_df_raw.to_json(date_format='iso')
    context['filename'] = request.POST.get('pass-filename-to-develop')

    # get constraints for input settings
    df_filtered = field_df_raw.drop_duplicates(subset=['stage'], keep='first')
    context['breakpoint_min'] = df_filtered['stage'].nsmallest(2).iloc[-1]
    context['breakpoint_max'] = df_filtered['stage'].nlargest(2).iloc[-1]

    try:
        [context['rc'], context['sidepanel_message']] = autofit_data(field_df_raw, init_offsets, context['breakpoint1'], context['rc_data'], context['n_seg'], weighted)
        context['offsets'] = [ context['rc']['parameters'][0]['offset'], context['rc']['parameters'][0]['offset'] ]
        offsets_val = [ float(context['rc']['parameters'][0]['offset']), float(context['rc']['parameters'][0]['offset']) ]

        

        if offsets_val[0] < 0:
            offsets_val[0] = ' + ' + str(abs(offsets_val[0]))
            offsets_val[1] = ' + 0.00 '
        else:
            offsets_val[0] = ' - ' + str(abs(offsets_val[0]))
            offsets_val[1] = ' - 0.00 '
        context['offsets_val'] = offsets_val

        # max offset
        context['max_offset'] = field_df_raw['stage'].min()
        # if context['rc']['parameters'][0]['seg_bounds'][0][0] < field_df_raw['stage'].min():
        #     context['max_offset'] = context['rc']['parameters'][0]['seg_bounds'][0][0]
        # else:
        #     context['max_offset'] = field_df_raw['stage'].min()

    except Exception as e:
                messages.error(request,"Unable to upload file. "+repr(e))


    return render(request, "rctool/rctool/develop/rctool_develop.html", context)


def rctool_develop_autofit(request):
    floatlist = lambda strlist : list(map(float, strlist.split(',')))


    # Initialize
    context={}
    context['breakpoint1'] = None

    if request.method == 'POST':
        offsets = [0.0, 0.0]
        offsets[0] = float(request.POST.get('offset1'))

        if request.POST.get('toggle_weighted_fit') == 'on':
            context['toggle_weighted_fit'] = 'true'
            weighted = True
        else:
            context['toggle_weighted_fit'] = 'false'
            weighted = None
        context['toggle_breakpoint'] = 'true' if request.POST.get('toggle_breakpoint') == 'on' else 'false'
        
        if request.POST.get('offset2'):
            offsets[1] = float(request.POST.get('offset2'))
        if request.POST.get('breakpoint1'):
            if context['toggle_breakpoint'] != 'true':
                context['breakpoint1'] = float(request.POST.get('breakpoint1'))

        if request.POST.get('pass-tour-status-to-develop'):
            context['develop_tour_request_status_id'] = request.POST.get('pass-tour-status-to-develop')
        
        context['n_seg'] = int(request.POST.get('n-seg'))
        context['offsets'] = offsets
            

        # Format equation according to + or - offset (ie. if user enters a - offset, the equation will show (H + offset) instead of (H -- offset))
        offsets_val = offsets.copy()
        if offsets_val[0] < 0:
            offsets_val[0] = ' + ' + str(abs(offsets_val[0]))
            context['offsets_val'] = offsets_val
        else:
            offsets_val[0] = ' - ' + str(abs(offsets_val[0]))
        if offsets_val[1] < 0:
            offsets_val[1] = ' + ' + str(abs(offsets_val[1]))
            context['offsets_val'] = offsets_val
        else:
            offsets_val[1] = ' - ' + str(abs(offsets_val[1]))

        
        # get field data from form POST
        fieldData_datetime    	= list(request.POST.get('fieldData_datetime').split(','))
        fieldData_comments    	= list(request.POST.get('fieldData_comments').split(','))
        fieldData_uncertainty 	= floatlist(request.POST.get('fieldData_uncertainty'))
        fieldData_stage 		= floatlist(request.POST.get('fieldData_stage'))
        fieldData_discharge 	= floatlist(request.POST.get('fieldData_discharge'))
        fieldData_active 		= list(request.POST.get('fieldData_active').split(','))
        
        df_passthrough = pd.DataFrame()
        df_passthrough['datetime']  = fieldData_datetime
        df_passthrough['discharge'] = fieldData_discharge
        df_passthrough['stage']     = fieldData_stage
        df_passthrough['uncertainty']   = fieldData_uncertainty
        df_passthrough['comments']      = fieldData_comments
        df_passthrough['toggle_point']  = fieldData_active

        context['table_dict'] = {'headings': df_passthrough.columns.values, 'data': df_passthrough.values.tolist()}
        context['rc_data'] = None
        context['adjust_seg'] = None
        context['fielddatacsv'] = df_passthrough.to_json(date_format='iso')
        context['offsets_val'] = offsets_val
        context['filename'] = request.POST.get('filename')

        # get constraints for input settings
        df_filtered = df_passthrough.drop_duplicates(subset=['stage'], keep='first')
        context['breakpoint_min'] = df_filtered['stage'].nsmallest(2).iloc[-1]
        context['breakpoint_max'] = df_filtered['stage'].nlargest(2).iloc[-1]

    try:
        [context['rc'], context['sidepanel_message']] = autofit_data(df_passthrough, context['offsets'], context['breakpoint1'], context['rc_data'], context['n_seg'], weighted)
        # max offset
        context['max_offset'] = df_passthrough['stage'].min()
        # if context['rc']['parameters'][0]['seg_bounds'][0][0] < df_passthrough['stage'].min():
        #     context['max_offset'] = context['rc']['parameters'][0]['seg_bounds'][0][0]
        # else:
        #     context['max_offset'] = df_passthrough['stage'].min()


    except Exception as e:
                messages.error(request, repr(e))

    return render(request, "rctool/rctool/develop/rctool_develop.html", context)



def rctool_export_initialize(request):
    context = {}
    export_form = export_rc_data()
    floatlist = lambda strlist : list(map(float, strlist.split(',')))
    if request.method == 'POST':
        # get field data from form POST
        fieldData_datetime    	= list(request.POST.get('fieldData_datetime').split(','))
        fieldData_comments    	= list(request.POST.get('fieldData_comments').split(','))
        fieldData_uncertainty 	= floatlist(request.POST.get('fieldData_uncertainty'))
        fieldData_stage 		= floatlist(request.POST.get('fieldData_stage'))
        fieldData_discharge 	= floatlist(request.POST.get('fieldData_discharge'))
        fieldData_active 		= list(request.POST.get('fieldData_active').split(','))
        rc_output = request.POST.get('rc_out')

        df_passthrough = pd.DataFrame()
        df_passthrough['datetime']  = fieldData_datetime
        df_passthrough['discharge'] = fieldData_discharge
        df_passthrough['stage']     = fieldData_stage
        df_passthrough['uncertainty']   = fieldData_uncertainty
        df_passthrough['comments']      = fieldData_comments
        df_passthrough['toggle_point']  = fieldData_active
        context['table_dict'] = {'headings': df_passthrough.columns.values, 'data': df_passthrough.values.tolist()}
        context['rc_data'] = None
        context['adjust_seg'] = None
        context['breakpoint1'] = None
        context['fielddatacsv'] = df_passthrough.to_json(date_format='iso')
        context['rc_output'] = ast.literal_eval(rc_output)
        # add filename to output dict
        context['rc_output']['filename'] = [request.POST.get('filename_out')]
    context['form'] = export_form

    return render(request, "rctool/rctool/export & review/rctool_export.html", context)


def create_export_rc_img(field_data, rc_data):
    # Initialize and prepaire
    pallet = ['#9ec1a3', '#fe5f55', '#003466']
    df_field = field_data.copy()
    df_field_active = field_data[field_data['toggle_point'] == 'checked']
    df_field_inactive = field_data[field_data['toggle_point'] == 'unchecked']
    # create plot obj
    plt.close(2)
    fig1, ax1 = plt.subplots(figsize=(11, 5), num=1)
    # scales etc
    plt.yscale('log')
    plt.xscale('log')
    ax1.grid(True, which='both')
    ax1.set_ylabel('Stage (m)')
    ax1.set_xlabel('Discharge (m$^3$/s)')
    ax1.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
    ax1.xaxis.set_minor_formatter(ticker.FormatStrFormatter('%.3f'))
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
    ax1.plot(df_field_active['stage'], df_field_active['discharge'], 'o', color=pallet[0], label='field data')
    if len(df_field_inactive['stage']) > 0:
        ax1.plot(df_field_inactive['stage'], df_field_inactive['discharge'], 'o', color='#808080', label='field data (inactive)')
    i = 1
    for segment_parameters in rc_data['parameters']:
        seg_bounds = segment_parameters['seg_bounds']
        y_seg = [seg_bounds[0][0], seg_bounds[1][0]]
        x_seg = [seg_bounds[0][1], seg_bounds[1][1]]
        ax1.plot(y_seg, x_seg, ls='-', color=pallet[i], label=segment_parameters['label'], lw=2.0)
        i += 1
    ax1.legend()
    tmpfile1 = io.BytesIO()
    fig1.savefig(tmpfile1)
    b64_1 = base64.b64encode(tmpfile1.getvalue()).decode()
    return b64_1


def create_export_res_img(field_data, rc_data):
    res_df = field_data.copy()
    # create plot obj
    plt.close(2)
    fig2, ax2 = plt.subplots(figsize=(11, 5), num=2)
    ax2.grid(True, which='both')
    # scales etc
    ax2.set_ylabel('Stage (m)')
    ax2.set_xlabel('Discharge Error (%)')
    ax2.plot(res_df['Discharge Error (%)'], res_df['stage'], 'o', color='#83c5be')
    tmpfile2 = io.BytesIO()
    fig2.savefig(tmpfile2)
    b64_2 = base64.b64encode(tmpfile2.getvalue()).decode()
    return b64_2

def export_calculate_discharge_error(field_data_output_df, rc_output_dict):
        # recalculate residual error percent
        error_perc_dat = []
        segment_parameters = rc_output_dict['parameters']
        breakpoint1 = float(segment_parameters[0]['seg_bounds'][1][0])
        if len(segment_parameters) > 1:
            df_error1 = field_data_output_df[field_data_output_df['stage'] <= breakpoint1]
        else:
            df_error1 = field_data_output_df.copy()
        const1 = segment_parameters[0]['const']
        exp1 = segment_parameters[0]['exp']
        offset1 = segment_parameters[0]['offset']
        error_perc_dat1 = 100 * ( ( const1 * ( df_error1['stage'] - offset1 ) ** exp1 ) - df_error1['discharge'] ) / df_error1['discharge']
        error_perc_dat = error_perc_dat + error_perc_dat1.tolist()
        df_error2 = field_data_output_df[field_data_output_df['stage'] >= breakpoint1]
        if len(df_error2['stage']) > 1 and len(segment_parameters) > 1:
            df_error2 = field_data_output_df[field_data_output_df['stage'] >= breakpoint1]
            const2 =segment_parameters[1]['const']
            exp2 = segment_parameters[1]['exp']
            offset2 = segment_parameters[0]['offset']
            error_perc_dat2 = 100 * ( ( const2 * ( df_error2['stage'] - offset2 ) ** exp2 ) - df_error2['discharge'] ) / df_error2['discharge']
            error_perc_dat = error_perc_dat + error_perc_dat2.tolist()
        field_data_output_df.insert(loc=4, column='Discharge Error (%)', value=error_perc_dat)


        field_data_output_df['Discharge Error (%)'] = field_data_output_df['Discharge Error (%)'].round(decimals=2)
        return field_data_output_df



def rctool_export_output(request):
    context = {}
    floatlist = lambda strlist : list(map(float, strlist.split(',')))

    if request.method == "POST":
        export_form = export_rc_data(request.POST)

        field_data_output_json = request.POST.get('fielddatacsv-to-output')
        field_data_output_df = pd.read_json(field_data_output_json)
        field_data_output_dict = field_data_output_df.to_dict()
        field_data_output_df['datetime'] = field_data_output_df['datetime'].apply(str)
        field_data_output_df['stage'] = field_data_output_df['stage'].round(decimals=4)
        field_data_output_df['discharge'] = field_data_output_df['discharge'].round(decimals=4)
        field_data_values = field_data_output_df.values.tolist()

        rc_output = request.POST.get('rc_output')
        rc_output_dict = ast.literal_eval(rc_output)
        rc_output_dict['data'].append(field_data_values)
        rc_output_df = pd.DataFrame.from_dict(rc_output_dict, orient='index')
        rc_output_df = rc_output_df.transpose()

        if export_form.is_valid():
            ftype = export_form.cleaned_data["export_filetype"]
            fname = export_form.cleaned_data["export_filename"]
            if export_form.cleaned_data["export_station_name"]:
                stname = export_form.cleaned_data["export_station_name"]
                context['stname'] = stname
            if export_form.cleaned_data["export_date_applic_init"]:
                app_period_start = export_form.cleaned_data["export_date_applic_init"]
                context['app_period_start'] = app_period_start
            if export_form.cleaned_data["export_date_applic_final"]:
                app_period_end = export_form.cleaned_data["export_date_applic_final"]
                context['app_period_end'] = app_period_end
            
            context['current_time'] = datetime.utcnow().strftime("%d/%m/%Y %H:%M")
            context['rc'] = rc_output_dict

            # Round output parameters
            for idx in range(len(rc_output_dict['parameters'])):
                rc_output_dict['parameters'][idx]['const'] = round(rc_output_dict['parameters'][idx]['const'], 4)
                rc_output_dict['parameters'][idx]['exp'] = round(rc_output_dict['parameters'][idx]['exp'], 4)

            # Format offset values for output equation
            offsets = [0,0]
            offsets[0] = rc_output_dict['parameters'][0]['offset']
            if len(rc_output_dict['parameters']) > 1:
                offsets[1] = rc_output_dict['parameters'][1]['offset']
            context['offsets'] = offsets
            # Format equation according to + or - offset (ie. if user enters a - offset, the equation will show (H + offset) instead of (H -- offset))
            offsets_val = offsets.copy()
            if offsets_val[0] < 0:
                offsets_val[0] = ' + ' + str(abs(offsets_val[0]))
                context['offsets_val'] = offsets_val
            else:
                offsets_val[0] = ' - ' + str(abs(offsets_val[0]))
                context['offsets_val'] = offsets_val
            if offsets_val[1] < 0:
                offsets_val[1] = ' + ' + str(abs(offsets_val[1]))
                context['offsets_val'] = offsets_val
            else:
                offsets_val[1] = ' - ' + str(abs(offsets_val[1]))
                context['offsets_val'] = offsets_val


            if ftype == 'session settings':
                try:
                    # output HTTP response
                    response = HttpResponse(
                        content_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="{0}.dat"'.format(fname)},
                    )
                    # write to csv
                    rc_output_df.to_csv(path_or_buf=response)
                    return response
                except Exception as e:
                    messages.error(request,"Unable to process request. "+repr(e))
            
            elif ftype == 'session results (csv)':
                export_calculate_discharge_error(field_data_output_df, rc_output_dict)
                field_table = {'headings': field_data_output_df.columns.values, 'data': field_data_output_df.values.tolist()}
                context['rc_img'] = create_export_rc_img(field_data_output_df, rc_output_dict)
                context['res_img'] = create_export_res_img(field_data_output_df, rc_output_dict)

                # create paramters df for output
                param_to_df = []
                for segment_parameter in rc_output_dict['parameters']:
                    segment_parameter['stage initial'] = segment_parameter['seg_bounds'][0][0]
                    segment_parameter['stage final'] = segment_parameter['seg_bounds'][1][0]
                    segment_parameter.pop('seg_bounds')
                    param_to_df.append(segment_parameter)
                df_parameters = pd.DataFrame(param_to_df)
                parameter_table = {'headings': df_parameters.columns.values, 'data': df_parameters.values.tolist()}

                # prepaire as output

                try:
                    # output HTTP response
                    response = HttpResponse(
                        content_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="{0}.csv"'.format(fname)},
                    )
                    # # write to csv
                    # rc_output_df.to_csv(path_or_buf=response)
                    # return response

                    writer = csv.writer(response)
                    writer.writerow(['RATING CURVE OUTPUT SUMMARY'])
                    writer.writerow(['date created (utc): {}'.format(context['current_time'])])
                    if export_form.cleaned_data["export_station_name"]:
                        writer.writerow(['location: {}'.format(export_form.cleaned_data["export_station_name"])])
                    if export_form.cleaned_data["export_date_applic_init"] and export_form.cleaned_data["export_date_applic_final"]:
                        writer.writerow(['period of applicability: {0} to {1}'.format(context['app_period_start'], context['app_period_end'])])
                    writer.writerow('')
                    writer.writerow(['MODEL PARAMETERS'])
                    writer.writerow(parameter_table['headings'])
                    for row in parameter_table['data']:
                        writer.writerow(row)
                    writer.writerow('')
                    writer.writerow(['MODEL INPUTS'])
                    writer.writerow(field_table['headings'])
                    for row in field_table['data']:
                        writer.writerow(row)

                    return response



                except Exception as e:
                    messages.error(request,"Unable to process request. "+repr(e))

            else:
                try:
                    # write to pdf option selected

                    # calculate residuals for output figures and table
                    field_data_output_df = export_calculate_discharge_error(field_data_output_df, rc_output_dict)
                    context['field_table'] = {'headings': field_data_output_df.columns.values, 'data': field_data_output_df.values.tolist()}
                    # create figure for pdf
                    context['rc_img'] = create_export_rc_img(field_data_output_df, rc_output_dict)
                    context['res_img'] = create_export_res_img(field_data_output_df, rc_output_dict)


                    # prepaire and return output pdf
                    template = get_template('rctool/rctool/export & review/rctool_export_pdf.html')
                    html = template.render(context)
                    pdf = render_to_pdf('rctool/rctool/export & review/rctool_export_pdf.html', context)
                    response = HttpResponse(pdf, content_type='application/pdf')
                    content = "inline; filename='%s'" %(fname)
                    download = request.GET.get("download")
                    if download:
                        content = "attachment; filename='%s.pdf'" %(fname)
                    response['Content-Disposition'] = content

                    return response

                except Exception as e:
                    messages.error(request,"Unable to process request. "+repr(e))

            context['form'] = export_form
            context['rc_output'] = rc_output

            return render(request, "rctool/rctool/export & review/rctool_export.html", context)
    else:
        export_form = export_rc_data()
    return render(request, "rctool/rctool/export & review/rctool_export.html", {"form":export_form})








