from django.test import TestCase
from django.contrib.staticfiles import finders

from django.urls import reverse

# import forms
from rctool.forms import import_rc_data, develop_rc, export_rc_data
import pandas as pd
import datetime as dt
from io import StringIO
import json


# Tests data import and export from sample_data.csv
class BaseTestCase(TestCase):
    test_csv = finders.find("sample_data/sample_data.csv")

    # test if the sample csv file exists
    def test_sample_csv_exists(self):
        assert self.test_csv is not None

    def test_import_csv(self):
        # read the csv file
        with open(self.test_csv, "r") as file:
            data = file.read()
            assert data is not None
            assert len(data) > 0

    def test_import_rc_data_form(self):
        # test the import form
        self.form_data_import = {
            "header_row": 1,
            "csv_upload": open(self.test_csv, "rb"),
        }
        form_import = import_rc_data(data=self.form_data_import)
        print(form_import.errors if form_import.errors else "form_import is valid")
        assert form_import.is_valid()

        # try to post the form data and check if the form submission is successful
        response = self.client.post(
            reverse("rctool_import", kwargs={"tour_request_id": 0}),
            data=self.form_data_import,
            follow=True,
        )
        # check if the form submission is successful
        assert response.status_code == 200

        # if form submission with sample data is successful, the table data should be populated
        assert (
            len(response.context["table_data"]) > 0
        ), "Table data is empty, sample form import failed"

        # check if the raw field data is populated
        raw_fielddata = response.context["raw_field_data"]
        assert raw_fielddata is not None

        df_fielddata = pd.read_json(StringIO(raw_fielddata))
        df_fielddata["datetime"] = pd.to_datetime(df_fielddata["datetime"])
        df_fielddata["datetime"] = df_fielddata["datetime"].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return df_fielddata

    # test if the develop rc form is valid and can be submitted successfully

    def test_develop_rc_form(self):
        self.form_data_develop = {
            "set_offset1": 0,
            "set_offset2": 0,
            "set_breakpoint1": 0,
            "set_breakpoint2": 0,
        }

        form_develop = develop_rc(data=self.form_data_develop)
        print(form_develop.errors if form_develop.errors else "form_develop is valid")
        assert form_develop.is_valid()

        # load raw field data from the import form
        df_fielddata = self.test_import_rc_data_form()
        # set all field data to active
        df_fielddata["active"] = "checked"

        def col_to_string(lst, format=None):
            values = lst.values.tolist()
            values_list = []

            for val in values:
                if isinstance(val, str):
                    values_list.append(val)
                elif isinstance(val, float):
                    values_list.append(str(val))

            return ",".join(values_list)

        # create post data for the develop rc form
        post_data = {
            "offset1": 0,
            "offset2": 0,
            "breakpoint1": 0,
            "breakpoint2": 0,
            "toggle_weighted_fit": "on",
            "tour_request_status_id": 0,
            "n-seg": 1,
            "fieldData_datetime": col_to_string(df_fielddata["datetime"]),
            "fieldData_comments": col_to_string(df_fielddata["comments"]),
            "fieldData_uncertainty": col_to_string(df_fielddata["uncertainty"]),
            "fieldData_stage": col_to_string(df_fielddata["stage"]),
            "fieldData_discharge": col_to_string(df_fielddata["discharge"]),
            "fieldData_active": col_to_string(df_fielddata["active"]),
            "filename": "testexport.pdf",
        }

        # try to post the form data and check if the form submission is successful
        response = self.client.post(
            reverse("rctool_develop_autofit"),
            data=post_data,
            follow=True,
        )

        # check if the form submission is successful
        assert response.status_code == 200

        # test if a rating curve was successfully autofitted
        rc_data = response.context["rc"]
        assert rc_data is not None
        assert len(rc_data) > 0

        return rc_data

    def test_export_rc_data_form(self):
        self.form_data_export = {
            "export_filetype": "session results (pdf)",
            "export_filename": "testexport.pdf",
            "export_station_name": "teststation",
            "export_comments": "test comments",
            "export_date_applic_init": "2024-01-01",
            "export_date_applic_final": "2024-01-31",
        }

        # check if the import form is valid
        form_export = export_rc_data(data=self.form_data_export)
        print(form_export.errors if form_export.errors else "form_export is valid")
        assert form_export.is_valid()

        rc_data = self.test_develop_rc_form()
        # try to post the form data and check if the form submission is successful
        post_dict_initialize = {
            "fieldData_datetime": "2024-01-01",
            "fieldData_comments": "2024-01-02",
            "fieldData_uncertainty": "1",
            "fieldData_stage": "2",
            "fieldData_discharge": "3",
            "fieldData_active": "1",
            "rc_out": json.dumps(rc_data),
            "filename_out": "testexport.pdf",
        }

        response_initialize = self.client.post(
            reverse("rctool_export_initialize"),
            data=post_dict_initialize,
            follow=True,
        )
        # # check if the form submission is successful
        assert response_initialize.status_code == 200

        df_fielddata = self.test_import_rc_data_form()
        df_fielddata["toggle_point"] = "checked"
        post_dict_output = {
            "fielddatacsv-to-output": json.dumps(df_fielddata.to_dict()),
            "rc_output": json.dumps(rc_data),
            "export_filetype": "session results (pdf)",
            "export_filename": "testexport.pdf",
            "export_station_name": "teststation",
            "export_comments": "test comments",
            "export_date_applic_init": "2024-01-01",
            "export_date_applic_final": "2024-01-31",
        }
        response_output = self.client.post(
            reverse("rctool_export_output"),
            data=post_dict_output,
            follow=True,
        )
        # check if the output is a pdf:
        assert response_output.status_code == 200
        assert response_output["Content-Type"] == "application/pdf"
