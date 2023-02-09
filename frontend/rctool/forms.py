from django import forms
from django.core import validators

class DatePickerInput(forms.DateInput):
        input_type = 'date'

class import_rc_data(forms.Form):
    csv_upload = forms.FileField(label="csv file")
    header_row = forms.IntegerField(label="header row number", widget=forms.NumberInput(attrs={'class': 'form-control', 'min':1, 'value':1, 'id':'form-header-row'}))
    csv_upload.required = False
    header_row.required = False

class develop_rc(forms.Form):
    set_offset1 = forms.FloatField(label="offset 1", widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'id':'offset1'}))
    set_offset2 = forms.FloatField(label="offset 2", widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'id':'offset2'}))
    set_breakpoint1 = forms.IntegerField(label="number of breakpoints", widget=forms.NumberInput(attrs={'class form-control-sm': 'form-control','id':'breakpoint1', 'min':1, 'value':1}))
    set_breakpoint2 = forms.IntegerField(label="number of breakpoints", widget=forms.NumberInput(attrs={'class form-control-sm': 'form-control', 'id':'breakpoint2', 'min':1, 'value':1}))

class export_rc_data(forms.Form):
    export_filetype = forms.ChoiceField(label='export type', widget=forms.Select(attrs={'class': 'form-control'}), choices=[('session settings', 'session settings'), ('session results (pdf)', 'session results (pdf)'), ('session results (csv)', 'session results (csv)')])
    export_filetype.widget.attrs['onchange'] = 'toggleExportForm(this.value)'
    export_filename = forms.CharField(label="file name", widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=200)
    export_station_name = forms.CharField(label="station name", widget=forms.TextInput(attrs={'class': 'form-control'}), max_length=200)
    export_station_name.required = False
    export_date_applic_init = forms.DateField(widget=DatePickerInput)
    export_date_applic_init.widget.attrs['class'] = 'form-control'
    export_date_applic_init.required = False
    export_date_applic_final = forms.DateField(widget=DatePickerInput)
    export_date_applic_final.widget.attrs['class'] = 'form-control'
    export_date_applic_final.required = False







