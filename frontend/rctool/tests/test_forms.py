"""
Unit tests for all three Django Form classes in forms.py.

These tests cover valid inputs, invalid inputs, and optional field handling
without needing a database or a running server.
"""
import pytest
from django.test import TestCase

from rctool.forms import develop_rc, export_rc_data, import_rc_data


# ---------------------------------------------------------------------------
# import_rc_data form
# ---------------------------------------------------------------------------

class TestImportRcDataForm(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "input_session_type": "new",
            "csv_content": '{"stage":{"0":0.3},"discharge":{"0":0.05}}',
            "session_content": "",
            "csv_separator": ",",
            "header_row": 1,
        }
        data.update(overrides)
        return data

    def test_valid_new_session(self):
        form = import_rc_data(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_load_session(self):
        form = import_rc_data(data=self._valid_data(input_session_type="load"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_semicolon_separator(self):
        form = import_rc_data(data=self._valid_data(csv_separator=";"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_tab_separator(self):
        form = import_rc_data(data=self._valid_data(csv_separator="\t"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_session_type(self):
        form = import_rc_data(data=self._valid_data(input_session_type="bogus"))
        self.assertFalse(form.is_valid())

    def test_invalid_separator(self):
        form = import_rc_data(data=self._valid_data(csv_separator="|"))
        self.assertFalse(form.is_valid())

    def test_header_row_must_be_integer(self):
        form = import_rc_data(data=self._valid_data(header_row="not-an-int"))
        self.assertFalse(form.is_valid())
        self.assertIn("header_row", form.errors)

    def test_header_row_missing_is_invalid(self):
        data = self._valid_data()
        del data["header_row"]
        form = import_rc_data(data=data)
        self.assertFalse(form.is_valid())

    def test_csv_content_optional(self):
        """csv_content is required=False — empty string is valid."""
        form = import_rc_data(data=self._valid_data(csv_content=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_session_content_optional(self):
        form = import_rc_data(data=self._valid_data(session_content=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_header_row_value_1(self):
        form = import_rc_data(data=self._valid_data(header_row=1))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["header_row"], 1)


# ---------------------------------------------------------------------------
# develop_rc form
# ---------------------------------------------------------------------------

class TestDevelopRcForm(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "set_offset1": 0.0,
            "set_offset2": 0.0,
            "set_breakpoint1": 0,
            "set_breakpoint2": 0,
        }
        data.update(overrides)
        return data

    def test_valid_zeroes(self):
        form = develop_rc(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_positive_offsets(self):
        form = develop_rc(data=self._valid_data(set_offset1=0.15, set_offset2=0.10))
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_negative_offset(self):
        """Negative offsets are mathematically valid (raises stage datum)."""
        form = develop_rc(data=self._valid_data(set_offset1=-0.05))
        self.assertTrue(form.is_valid(), form.errors)

    def test_offset_is_float(self):
        form = develop_rc(data=self._valid_data(set_offset1=0.123))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertAlmostEqual(form.cleaned_data["set_offset1"], 0.123)

    def test_breakpoint_must_be_integer(self):
        form = develop_rc(data=self._valid_data(set_breakpoint1="not-int"))
        self.assertFalse(form.is_valid())
        self.assertIn("set_breakpoint1", form.errors)

    def test_missing_offset_is_invalid(self):
        data = self._valid_data()
        del data["set_offset1"]
        form = develop_rc(data=data)
        self.assertFalse(form.is_valid())

    def test_all_four_fields_required(self):
        """All four fields are required — verify each one fails when absent."""
        for field in ("set_offset1", "set_offset2", "set_breakpoint1", "set_breakpoint2"):
            data = self._valid_data()
            del data[field]
            form = develop_rc(data=data)
            self.assertFalse(form.is_valid(), f"Expected invalid when {field} is missing")


# ---------------------------------------------------------------------------
# export_rc_data form
# ---------------------------------------------------------------------------

class TestExportRcDataForm(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "export_filetype": "session results (pdf)",
            "export_filename": "test_output",
            "export_station_name": "Test Station",
            "export_comments": "test run",
            "export_date_applic_init": "2024-01-01",
            "export_date_applic_final": "2024-12-31",
        }
        data.update(overrides)
        return data

    def test_valid_pdf_export(self):
        form = export_rc_data(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_csv_export(self):
        form = export_rc_data(data=self._valid_data(export_filetype="session results (csv)"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_session_settings_export(self):
        form = export_rc_data(data=self._valid_data(export_filetype="session settings"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_filetype(self):
        form = export_rc_data(data=self._valid_data(export_filetype="word document"))
        self.assertFalse(form.is_valid())

    def test_filename_required(self):
        data = self._valid_data()
        del data["export_filename"]
        form = export_rc_data(data=data)
        self.assertFalse(form.is_valid())

    def test_filename_max_length_exceeded(self):
        form = export_rc_data(data=self._valid_data(export_filename="x" * 201))
        self.assertFalse(form.is_valid())
        self.assertIn("export_filename", form.errors)

    def test_filename_max_length_exact(self):
        form = export_rc_data(data=self._valid_data(export_filename="x" * 200))
        self.assertTrue(form.is_valid(), form.errors)

    def test_station_name_optional(self):
        form = export_rc_data(data=self._valid_data(export_station_name=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_comments_optional(self):
        form = export_rc_data(data=self._valid_data(export_comments=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_dates_optional(self):
        data = self._valid_data()
        data["export_date_applic_init"] = ""
        data["export_date_applic_final"] = ""
        form = export_rc_data(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_date_format(self):
        form = export_rc_data(data=self._valid_data(export_date_applic_init="not-a-date"))
        self.assertFalse(form.is_valid())
        self.assertIn("export_date_applic_init", form.errors)

    def test_comments_max_length_exceeded(self):
        form = export_rc_data(data=self._valid_data(export_comments="x" * 1001))
        self.assertFalse(form.is_valid())
        self.assertIn("export_comments", form.errors)
