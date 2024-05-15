from django import forms
from django.core import validators


class DatePickerInput(forms.DateInput):
    input_type = "date"


class import_rc_data(forms.Form):
    input_session_type = forms.ChoiceField(
        label="import type",
        widget=forms.Select(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px;",
            }
        ),
        choices=[
            ("new", "new session"),
            ("load", "load previous session"),
        ],
    )

    csv_content = forms.CharField(
        label="csv content",
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px; height: 200px;",
            }
        ),
    )
    header_row = forms.IntegerField(
        label="header row number",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "min": 1,
                "value": 1,
                "id": "form-header-row",
                "style": "font-size: 11.5px;",
            }
        ),
    )

    # define form actions
    def clean(self):
        cleaned_data = super().clean()
        csv_content = cleaned_data.get("csv_content")
        header_row = cleaned_data.get("header_row")

        # check if csv content is empty
        if csv_content == "":
            self.add_error("csv_content", "csv content is empty")

        # check if header row is out of range
        if header_row < 1:
            self.add_error("header_row", "header row is out of range")


class develop_rc(forms.Form):
    set_offset1 = forms.FloatField(
        label="offset 1",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "id": "offset1",
                "style": "font-size: 11.5px;",
            }
        ),
    )
    set_offset2 = forms.FloatField(
        label="offset 2",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "id": "offset2",
                "style": "font-size: 11.5px;",
            }
        ),
    )
    set_breakpoint1 = forms.IntegerField(
        label="number of breakpoints",
        widget=forms.NumberInput(
            attrs={
                "class form-control-sm": "form-control",
                "id": "breakpoint1",
                "value": 1,
                "style": "font-size: 11.5px;",
            }
        ),
    )
    set_breakpoint2 = forms.IntegerField(
        label="number of breakpoints",
        widget=forms.NumberInput(
            attrs={
                "class form-control-sm": "form-control",
                "id": "breakpoint2",
                "value": 1,
                "style": "font-size: 11.5px;",
            }
        ),
    )


class export_rc_data(forms.Form):
    export_filetype = forms.ChoiceField(
        label="export type",
        widget=forms.Select(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px;",
            }
        ),
        choices=[
            ("session settings", "session settings"),
            ("session results (pdf)", "session results (pdf)"),
            ("session results (csv)", "session results (csv)"),
        ],
    )
    export_filetype.widget.attrs["onchange"] = "toggleExportForm(this.value)"
    export_filename = forms.CharField(
        label="file name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px;",
            }
        ),
        max_length=200,
    )
    export_station_name = forms.CharField(
        label="station name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px;",
            }
        ),
        max_length=200,
    )
    export_station_name.required = False
    export_comments = forms.CharField(
        label="comments",
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm",
                "style": "font-size: 11.5px; height:60px;",
            }
        ),
        max_length=1000,
    )
    export_comments.required = False
    export_date_applic_init = forms.DateField(widget=DatePickerInput)
    export_date_applic_init.widget.attrs["class"] = "form-control form-control-sm"
    export_date_applic_init.required = False
    export_date_applic_final = forms.DateField(widget=DatePickerInput)
    export_date_applic_final.widget.attrs["class"] = "form-control form-control-sm"
    export_date_applic_final.required = False
