import json
import re

from django.db.models import F
from django.http import (
    HttpResponse,
    QueryDict,
)
from .forms_fields_widgets import (
    NumberFieldForm,
    OptionsFieldForm,
    OptionsFieldFormForRadioInputs,
    OptionsFieldFormForCheckboxes,
    CheckboxFieldWithSpecifyForm,
    RadioFieldWithSpecifyForm,
    TextFieldForm,
)

from enum import Enum


class QuestionType(Enum):
    NUMBER = ("number", "Number", NumberFieldForm)
    TEXT = ("text", "Text", TextFieldForm)
    TRUE_FALSE = ("true_false", "True/False", OptionsFieldForm)
    TRUE_FALSE_OTHER = ("true_false_other", "True/False/Other", OptionsFieldForm)
    SINGLE_CHOICE = ("single_choice", "Single-Choice", OptionsFieldFormForRadioInputs)
    SINGLE_CHOICE_SPECIFY = (
        "single_choice_specify",
        "Single-Choice with Specify",
        RadioFieldWithSpecifyForm,
    )
    MULTIPLE_CHOICE = (
        "multiple_choice",
        "Multiple-Choice",
        OptionsFieldFormForCheckboxes,
    )
    MULTIPLE_CHOICE_SPECIFY = (
        "multiple_choice_specify",
        "Multiple-Choice with Specify",
        CheckboxFieldWithSpecifyForm,
    )

    def __new__(cls, id, label, form_class):
        entry = object.__new__(cls)
        entry.id = entry._value_ = id  # set the value, and the extra attribute
        entry.label = label
        entry.form_class = form_class
        return entry

    def __repr__(self):
        return f"<{type(self).__name__}.{self.name}: ({self.id!r}, {self.label!r})>"


def transform_survey_options_to_field_form(field_schema):
    field_type, survey_options = field_schema.get("widget"), field_schema.get("options")
    if field_type in [
        "boolean",
        "multi_checkbox",
        "radio",
        "multi_checkbox_specify",
        "radio_w_specify",
    ]:
        return [opt["label"]["en"] for opt in survey_options]


def transform_options_to_survey_schema(field_type, options):
    if field_type in ["boolean", "boolean_or_null"]:
        schema_options = []
        for i, opt in enumerate(options):

            if opt in ["True", "False"]:
                label = opt
                opt = bool(opt)
            else:
                label = opt
                opt = None

            schema_options.append(
                {
                    "pos": i,
                    "val": opt,
                    "label": {"en": label},
                }
            )
        return schema_options
    if field_type in [
        "multi_checkbox",
        "radio",
        "multi_checkbox_specify",
        "radio_w_specify",
    ]:
        schema_options = []
        for i, opt in enumerate(options):
            schema_options.append(
                {
                    "pos": i,
                    "val": opt,
                    "label": {"en": opt},
                }
            )
        return schema_options

    else:
        return None


def get_json_schema_with_default_options(field_type, data):
    pos = data.get("field_num") or 0
    is_required = data.get("is_required", False)

    if field_type == "number":
        number_type = data.get("number_type", "integer")
        step = 1 if number_type == "integer" else 0.01
        min_value = data.get("min_value", None)
        max_value = data.get("max_value", None)
        return (
            {
                "pos": pos,
                "type": number_type,
                "widget": "number",
                "widget_config": {
                    "is_required": is_required,
                    "min": min_value,
                    "max": max_value,
                    "step": step,
                },
            },
            [],
        )

    if field_type == "text":
        num_lines = data.get("num_lines", 3)
        return (
            {
                "pos": pos,
                "type": "text",
                "widget": "text",
                "widget_config": {
                    "is_required": is_required,
                    "rows": num_lines,
                },
            },
            [],
        )

    if field_type in ["boolean", "boolean_or_null"]:

        defaults = [
            {"pos": 0, "val": True, "label": {"en": "True"}},
            {"pos": 1, "val": False, "label": {"en": "False"}},
        ]
        if field_type == "boolean_or_null":
            defaults.append({"pos": 2, "val": None, "label": {"en": "Other"}})
        return (
            {
                "pos": pos,
                "type": "boolean",
                "widget": "radio",
            },
            defaults,
        )

    num_columns = data.get("num_columns") or 1
    if field_type in ["multi_checkbox", "radio"]:
        return (
            {
                "pos": pos,
                "widget": field_type,
                "type": "text",  # TODO customizable
                "widget_config": {
                    "attrs": {"class": f"survey-{num_columns}col"},
                    "is_required": is_required,
                },
            },
            [
                {
                    "pos": 0,
                    "val": "option_1",
                    "label": {"en": "Option 1"},
                },
                {
                    "pos": 1,
                    "val": "option_2",
                    "label": {"en": "Option 2"},
                },
            ],
        )
    if field_type in ["multi_checkbox_specify", "radio_w_specify"]:
        specify_option_value = data.get("specify_option") or "other"
        value_type = "text"
        return (
            {
                "pos": pos,
                "widget": field_type,
                "type": value_type,
                "widget_config": {
                    "attrs": {"class": f"survey-{num_columns}col"},
                    "specify_input_type": value_type,
                    "specify_option_value": specify_option_value,
                    "is_required": is_required,
                },
            },
            [
                {
                    "pos": 0,
                    "val": "option_1",
                    "label": {"en": "Option 1"},
                },
                {
                    "pos": 1,
                    "val": "option_2",
                    "label": {"en": "Option 2"},
                },
                {
                    "pos": 2,
                    "val": "other",
                    "label": {"en": "Specify"},
                },
            ],
        )
    raise ValueError(f"Unimplemented field type {field_type}")


def _field_has_options(field_type: str) -> bool:
    return field_type in [
        "boolean",
        "boolean_or_null",
        "multi_checkbox",
        "radio",
        "multi_checkbox_specify",
        "radio_w_specify",
    ]


def get_bound_field_form_from_schema(
    field_num: int, field_schema: dict, disabled: bool = False
) -> dict:
    """
    Takes a field schema and returns a bound field form.
    Used to display existing fields in the survey edit view.
    """
    field_type = field_schema.get("type")
    field_form_opts = {
        "field_label": field_schema.get("label").get("en"),
        "question_text": field_schema.get("question_text").get("en"),
        "options": transform_survey_options_to_field_form(field_schema),
    }

    if field_type in ["boolean", "boolean_or_null"]:
        return OptionsFieldForm(field_num, data=field_form_opts, disabled=disabled)

    # Common attributes for all below fields
    widget_config = field_schema.get("widget_config", {})
    is_required = widget_config.get("is_required", False) if widget_config else False

    if field_type in ["number"]:
        min_value = widget_config.get("min", None)
        max_value = widget_config.get("max", None)
        number_type = widget_config.get("number_type", "integer")
        data = {
            **field_form_opts,
            **{
                "min_value": min_value,
                "max_value": max_value,
                "number_type": number_type,
                "is_required": is_required,
            },
        }
        return NumberFieldForm(field_num, data=data, disabled=disabled)

    if field_type in ["text"]:
        num_lines = widget_config.get("rows", 3)
        data = {
            **field_form_opts,
            **{
                "num_lines": num_lines,
                "is_required": is_required,
            },
        }
        return TextFieldForm(field_num, data=data, disabled=disabled)

    num_columns = 1
    if "attrs" in widget_config and "class" in widget_config["attrs"]:
        css_class = widget_config["attrs"]["class"]

        if m := re.match(r"survey-(\d)col", css_class):
            num_columns = m.group(1)

    if field_type in ["radio"]:
        data = {
            **field_form_opts,
            **{
                "num_columns": num_columns,
                "is_required": is_required,
            },
        }
        return OptionsFieldFormForRadioInputs(field_num, data=data, disabled=disabled)

    if field_type in ["multi_checkbox"]:
        data = {
            **field_form_opts,
            **{
                "num_columns": num_columns,
                "is_required": is_required,
            },
        }
        return OptionsFieldFormForCheckboxes(field_num, data=data, disabled=disabled)

    # Common value to specify fields
    specify_option = widget_config.get("specify_option_value", "Specify")

    if field_type in ["radio_w_specify"]:
        data = {
            **field_form_opts,
            **{
                "num_columns": num_columns,
                "specify_option": specify_option,
                "is_required": is_required,
            },
        }
        return RadioFieldWithSpecifyForm(field_num, data=data, disabled=disabled)
    if field_type in ["multi_checkbox_specify"]:
        data = {
            **field_form_opts,
            **{
                "num_columns": num_columns,
                "specify_option": specify_option,
                "is_required": is_required,
            },
        }
        return CheckboxFieldWithSpecifyForm(field_num, data=data, disabled=disabled)

    raise ValueError(f"Unimplemented field type {field_type}")


def get_field_form_class_and_default_vals(question_type: str):
    if question_type == "number":
        return (
            NumberFieldForm,
            {"number_type": "integer", "is_required": False},
        )
    if question_type == "text":
        return (
            TextFieldForm,
            {"is_required": False, "num_lines": 3, "max_length": 5_000},
        )
    if question_type in ["boolean", "boolean_or_null"]:
        opts = ["True", "False"]
        if question_type == "boolean_or_null":
            opts.append("Other")
        return (
            OptionsFieldForm,
            {"options": opts},
        )

    if question_type in ["radio"]:
        return (
            OptionsFieldFormForRadioInputs,
            {
                "num_columns": 1,  # makes the option selected!!
                "options": ["Option 1", "Option 2"],
                "is_required": False,
            },
        )

    if question_type in ["multi_checkbox"]:
        return (
            OptionsFieldFormForCheckboxes,
            {
                "num_columns": 1,  # makes the option selected!!
                "options": ["Option 1", "Option 2"],
                "is_required": False,
            },
        )
    if question_type in ["radio_w_specify"]:
        return (
            RadioFieldWithSpecifyForm,
            {
                "num_columns": 1,
                "options": ["Option 1", "Option 2", "Specify"],
                "specify_option": "Specify",
                "is_required": False,
            },
        )
    if question_type in ["multi_checkbox_specify"]:
        return (
            CheckboxFieldWithSpecifyForm,
            {
                "num_columns": 1,
                "options": ["Option 1", "Option 2", "Specify"],
                "specify_option": "Specify",
                "is_required": False,
            },
        )
    raise ValueError(f"Unimplemented field type {question_type}")


def get_field_form_and_schema(data):
    """ """
    field_type = data.get("field_type")
    field_num = data.get("field_num")
    field_label = data.get("field_label")
    question_text = data.get("question_text")

    assert field_type, "Field type is required"
    assert field_num, "Field number is required"
    assert field_label, "Field label is required"
    assert question_text, "Question text is required"

    schema_template, _ = get_json_schema_with_default_options(field_type, data)

    # Add stuff to schema
    field_schema = {
        **schema_template,
        **{
            "label": {"en": field_label},
            "question_text": {"en": question_text},
        },
    }
    if _field_has_options(field_type):
        if isinstance(data, QueryDict):
            options = data.getlist("options")
        else:
            options = data.get("options")
        # If a single option is passed, it's a string, not a list
        # which will casue the next function to consider every character as an option
        if not isinstance(options, list):
            options = [options]

        field_schema = field_schema | {
            "options": transform_options_to_survey_schema(field_type, options)
        }

    return None, field_schema
