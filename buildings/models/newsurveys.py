import json
import logging
from pprint import pprint
from django import forms
from django.forms import Form
from django.utils import formats
from django.http import QueryDict
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from buildings.models.newmodels import Survey
from buildings.newwidgets import (
    MultiCheckboxSpecify2,
    MultiCheckboxSpecifyRequired2,
    RadioSelect,
    RadioWithSpecify2,
)


def get_widget_for_field(widget_type):
    if widget_type == "radio":
        return RadioSelect(attrs={"class": "survey-1col"})
    if widget_type == "radio_w_specify":
        return RadioWithSpecify2(attrs={"class": "survey-1col"})
    if widget_type == "multi_checkbox":
        return MultiCheckboxSpecify2(attrs={"class": "survey-1col"}, has_specify=False)
    if widget_type == "multi_checkbox_specify":
        return MultiCheckboxSpecify2(attrs={"class": "survey-1col"}, has_specify=True)
    if widget_type == "multi_checkbox_required":
        return MultiCheckboxSpecifyRequired2(attrs={"class": "survey-3col"})
    if widget_type == "multi_checkbox_required_specify":
        return MultiCheckboxSpecifyRequired2(
            attrs={"class": "survey-3col"}, has_specify=True
        )
    raise Exception(f"Unknown widget type: {widget_type}")


class MyNullIntegerField(forms.IntegerField):

    def to_python(self, value):
        """
        The parent class will throw an error if int() fails on the value.
        TO support passing in "null" we'll catch that special case and
        convert it to None
        """
        try:
            value = super().to_python(value)
        except ValidationError as e:
            if value == "null":
                return None
            raise e
        return value

    def bound_data(self, data, initial):
        """
        Here we convert a None bound data to "null" for the widget
        """
        data = super().bound_data(data, initial)
        if data is None:
            return "null"
        return data


class MyJSONField(forms.JSONField):
    """
    Custom field to hold a list of values.
    We don't actually want to convert to and from JSON.
    """

    def to_python(self, value):
        super().to_python(value)
        # Return an empty list if no input was given.
        if "on" in value:
            value.remove("on")
        return value

    def bound_data(self, data, initial):
        """
        Override completely, don't try to json.loads"""
        if self.disabled:
            return initial
        return data

    def prepare_value(self, value):
        """
        Override completely - don't try to json.dumps"""
        return value


class MyNullBooleanField(forms.NullBooleanField):

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        if data in [True, False]:
            return str(data).lower()
        return "null"


def get_field_type(field_type, required: bool):

    if field_type == "integer":
        return forms.IntegerField(required=required)
    if field_type == "boolean":
        return MyNullBooleanField(required=required)
    if field_type in ["text", "string"]:
        return MyJSONField(required=required)


def order_schema_by_question_number(schema):
    """Ordering not garanteed to persist through JSONB/dict serde"""
    return dict(sorted(schema.items(), key=lambda x: x[1]["question_number"]))


class DynamicSurveyForm(Form):
    """
    Dynamically generate a form based on a survey schema.
    We create a response object using the cleaned data down the line
    """

    def __init__(self, survey: Survey, *args, **kwargs):
        super(DynamicSurveyForm, self).__init__(*args, **kwargs)

        print(self.data)

        # Check if there is non-empty data - it would have been set
        # from a POST request or from a previous response
        self.was_filled = True if self.data else False

        schema = order_schema_by_question_number(survey.schema)
        modals = survey.modals

        for field, config in schema.items():
            self.fields[field] = get_field_type(
                config["type"], config["required"] if "required" in config else False
            )
            self.fields[field].label = config["label"]["en"]
            self.fields[field].question_text = config["question_text"]["en"]
            self.fields[field].question_number = config["question_number"]

            if "has_modal" in config and config["has_modal"]:
                self.fields[field].has_modal = True
                self.fields[field].modal = modals[field]

            self.fields[field].widget = get_widget_for_field(config["widget"])

            if "widget_config" in config:
                for k, v in config["widget_config"].items():
                    # We don't want to overwrite the whole attrs attribute
                    # but add each k/v indivudally
                    if k == "attrs":
                        for k, v in config["widget_config"]["attrs"].items():
                            self.fields[field].widget.attrs[k] = v
                    else:
                        setattr(self.fields[field].widget, k, v)

            if "options" in config:
                self.fields[field].widget.choices = [
                    (k, _(v["option_text"]["en"])) for k, v in config["options"].items()
                ]

            if self.data and field in self.data:
                print(f"Field {field} is bound")
                self.fields[field].widget.is_bound = True
                self.fields[field].widget.initial = self.data[field]
