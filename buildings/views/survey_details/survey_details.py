import json
import re

from django.db.models import F
from django.http import (
    HttpResponse,
    QueryDict,
)
from django.utils import timezone
from django.core.paginator import Paginator
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext_lazy as _
from buildings.models.newmodels import Survey
from buildings.models.newsurveys import DynamicSurveyForm
from .forms_fields_widgets import (
    NumberFieldForm,
    OptionsFieldForm,
    OptionsFieldFormForRadioInputs,
    OptionsFieldFormForCheckboxes,
    CheckboxFieldWithSpecifyForm,
    RadioFieldWithSpecifyForm,
    TextFieldForm,
)
from django.template.loader import render_to_string

import logging

from buildings.utils.utility import get_b64_encoded_json
from buildings.views.views import get_surveys_qb_filters_and_optgroups

log = logging.getLogger(__name__)


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
    if field_type == "boolean":
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

        # New code: append third option if boolean_or_null
        if field_type == "boolean_or_null":
            defaults.append({"pos": 2, "val": None, "label": {"en": "Other"}})

        return (
            {"pos": pos, "type": "boolean", "widget": "radio"},
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
    field_type = field_schema.get("widget")
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


def get_field_form_class_and_default_vals(field_type: str):
    if field_type == "number":
        return (
            NumberFieldForm,
            {"number_type": "integer", "is_required": False},
        )
    if field_type == "text":
        return (
            TextFieldForm,
            {"is_required": False, "num_lines": 3, "max_length": 5_000},
        )
    if field_type in ["boolean", "boolean_or_null"]:
        opts = ["True", "False"]
        if field_type == "boolean_or_null":
            opts.append("Other")
        return (
            OptionsFieldForm,
            {"options": opts},
        )

    if field_type in ["radio"]:
        return (
            OptionsFieldFormForRadioInputs,
            {
                "num_columns": 1,  # makes the option selected!!
                "options": ["Option 1", "Option 2"],
                "is_required": False,
            },
        )

    if field_type in ["multi_checkbox"]:
        return (
            OptionsFieldFormForCheckboxes,
            {
                "num_columns": 1,  # makes the option selected!!
                "options": ["Option 1", "Option 2"],
                "is_required": False,
            },
        )
    if field_type in ["radio_w_specify"]:
        return (
            RadioFieldWithSpecifyForm,
            {
                "num_columns": 1,
                "options": ["Option 1", "Option 2", "Specify"],
                "specify_option": "Specify",
                "is_required": False,
            },
        )
    if field_type in ["multi_checkbox_specify"]:
        return (
            CheckboxFieldWithSpecifyForm,
            {
                "num_columns": 1,
                "options": ["Option 1", "Option 2", "Specify"],
                "specify_option": "Specify",
                "is_required": False,
            },
        )
    raise ValueError(f"Unimplemented field type {field_type}")

@login_required(login_url="account_login")
def render_question_preview(request):
    """
    Returns a rendered new question form and its preview.
    Called by HTMX dynamically as questions are added or edited.
    """

    print(request.GET)
    print(request.POST)

    # We accept both POST and GET here the same way
    data = getattr(request, request.method)
    field_type = data.get("field_type")
    field_num = data.get("field_num") or 0
    field_label = data.get("field_label") or f"Field {field_num} Label"
    question_text = data.get("question_text") or f"Question {field_num} Text"

    # Generate appropriate new_field_form
    field_form_class, field_form_default_val = get_field_form_class_and_default_vals(
        field_type
    )

    print("field_form_default_val", field_form_default_val)

    schema_template, schema_default_options = get_json_schema_with_default_options(
        field_type, data
    )

    if request.POST:
        new_field_form = field_form_class(
            field_num, request.POST, disabled=False
        )  # field_num is included in POST

        schema_options = transform_options_to_survey_schema(
            field_type, data.getlist("options")
        )
    else:
        field_form_default_val |= {
            "field_label": field_label,
            "question_text": question_text,
        }
        new_field_form = field_form_class(
            field_num=field_num, data=field_form_default_val, disabled=False
        )
        schema_options = schema_default_options

    # Add stuff to schema
    field_schema = {
        **schema_template,
        **{
            "label": {"en": field_label},
            "question_text": {"en": question_text},
        },
    }
    field_schema = (
        field_schema | {"options": schema_options}
        if field_form_class.has_options
        else field_schema
    )

    new_field_form.is_valid()

    tmp_survey_for_render = Survey(schema={"field": field_schema})
    rendered_field = DynamicSurveyForm(tmp_survey_for_render, request.POST)

    context = {
        "rendered_field": rendered_field,
        "field_form": new_field_form,
        "field_num": field_num,
    }

    return render(request, "buildings/survey_details/form_renderer_template.html", context)


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


@login_required(login_url="account_login")
def survey_details(request, survey_slug):

    all_question_types = [
        {"id": "number", "label": "Number"},
        {"id": "text", "label": "Text"},
        {"id": "boolean", "label": "True/False"},
        {"id": "boolean_or_null", "label": "True/False/Other"},
        {"id": "radio", "label": "Single-Choice"},
        {"id": "multi_checkbox", "label": "Multiple-Choice"},
        {"id": "radio_w_specify", "label": "Single-Choice with Specify"},
        {"id": "multi_checkbox_specify", "label": "Multiple-Choice with Specify"},
    ]

    num_results_per_page = 10

    if request.method == "POST":
        body = json.loads(request.body)
        log.debug(f"POST request to survey_details_questions {body}")

        survey = Survey.objects.filter(slug=survey_slug).first()

        if "delete_draft" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} DELETING SURVEY {survey.id}: {survey.name}"
            )
            survey.delete()
            return redirect("buildings:surveys")

        if "activate_survey" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} ACTIVATING SURVEY {survey.id}: {survey.name}"
            )
            survey.status = Survey.Status.ACTIVE
            survey.save()
            return redirect("buildings:survey_details", survey_slug=survey_slug)

        if "reactivate_survey" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} REACTIVATING SURVEY {survey.id}: {survey.name}"
            )
            survey.status = Survey.Status.ACTIVE
            survey.save()
            return redirect("buildings:survey_details", survey_slug=survey_slug)

        if "complete_survey" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} COMPLETING SURVEY {survey.id}: {survey.name}"
            )
            survey.status = Survey.Status.COMPLETED
            survey.save()
            return redirect("buildings:survey_details", survey_slug=survey_slug)

        if "unarchive_survey" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} UNARCHVING SURVEY {survey.id}: {survey.name}"
            )
            survey.status = Survey.Status.COMPLETED
            survey.save()
            return redirect("buildings:survey_details", survey_slug=survey_slug)

        if "archive_survey" in body:
            logging.info(
                f"user {request.user.id} {request.user.username} ARCHVING SURVEY {survey.id}: {survey.name}"
            )
            survey.status = Survey.Status.ARCHIVED
            survey.save()
            return redirect("buildings:survey_details", survey_slug=survey_slug)

        new_survey_schema = {}

        for field_id, field_data in body.items():
            field_form, field_schema = get_field_form_and_schema(field_data)
            log.debug(f"schema: {field_schema}")
            new_survey_schema[field_id] = field_schema

        # Survey exists for sure, we want to update it with the new schema
        survey = Survey.objects.filter(slug=survey_slug).first()
        survey.schema = new_survey_schema
        survey.date_modified = timezone.now()
        survey.save()
        return render(
            request,
            "buildings/survey_details/last_saved_time.html",
            {"date_modified": survey.date_modified},
        )

    survey = get_object_or_404(Survey, slug=survey_slug)
    dataset = survey.dataset

    pagenum = request.GET.get("page") or 1
    orderby_field = request.GET.get("field") or "address"
    orderby_dir = request.GET.get("dir") or "asc"
    p_bldg_cols = get_b64_encoded_json(request.GET.get("user_bldg_cols"))
    p_survey_cols = get_b64_encoded_json(request.GET.get("user_survey_cols"))

    candidates = survey.get_target_population()

    default_bldg_cols = dataset.get_fields_to_display()
    default_survey_cols = []

    # Column config for refreshing the view
    # Unlike in survey results, we don't want to save the user config
    # as this is only for convenience when viewing candidates
    # Users can't return to the survey cretion view so we don't save config.
    if p_bldg_cols or p_bldg_cols == []:
        # The user set their config, we need to update the DB value and set
        # the current user columns to the parameter value
        user_bldg_cols = p_bldg_cols
    else:
        # No param set, take previous saved value or defaults
        user_bldg_cols = default_bldg_cols

    if p_survey_cols or p_survey_cols == []:
        user_survey_cols = p_survey_cols
    else:
        user_survey_cols = default_survey_cols

    # Includes all columns we can order by
    bldg_orderby_cols = [
        {"id": "num_responses", "label": "Number of Responses"}
    ] + dataset.get_orderby_fields()
    survey_orderby_cols = default_survey_cols

    # Need to use F to hide nulls, otherwise order_by descneding would show them first
    order_by = getattr(F(orderby_field), orderby_dir)(nulls_last=True)
    candidates = candidates.order_by(order_by, "id")
    page = Paginator(candidates, per_page=num_results_per_page).get_page(pagenum)

    qb_dataset_filters = dataset.get_schema(prefix="")
    dataset_filter_rules = survey.get_readonly_rules("dataset")
    survey_filter_rules = survey.get_readonly_rules("surveys")

    # TODO: Store this directly, shouldn't have to calculate every time
    surveys_on_dataset = Survey.objects.filter(dataset=dataset)
    survey_filters_and_optgroups = get_surveys_qb_filters_and_optgroups(
        surveys_on_dataset
    )

    existing_fields_to_render = []

    num_fields = len(survey.schema)
    sorted_fields = sorted(survey.schema.values(), key=lambda x: x["pos"])
    for field_num, field_schema in enumerate(sorted_fields):

        field_type = field_schema.get("widget")

        disable_forms = survey.status == "ACTIVE"

        field_form = get_bound_field_form_from_schema(
            field_num + 1, field_schema, disabled=disable_forms
        )
        # need to render the field itself, and the field form
        # if survey is active, deactivate all inputs - survey is read only

        tmp_survey_for_render = Survey(schema={"field": field_schema})
        field_preview = DynamicSurveyForm(tmp_survey_for_render, request.POST)
        existing_fields_to_render.append((field_type, field_form, field_preview))

    context = {
        "survey": survey,
        "dataset": dataset,
        "num_fields": num_fields,
        "page": page,
        "survey_orderby_cols": survey_orderby_cols,
        "bldg_orderby_cols": bldg_orderby_cols,
        "dataset_filter_rules": dataset_filter_rules,
        "survey_filter_rules": survey_filter_rules,
        "qb_dataset_filters": qb_dataset_filters,
        "qb_surveys_filters": survey_filters_and_optgroups,
        "orderby_field": orderby_field,
        "orderby_dir": orderby_dir,
        "user_bldg_cols": user_bldg_cols,
        "default_bldg_cols": default_bldg_cols,
        "user_survey_cols": user_survey_cols,
        "default_survey_cols": default_survey_cols,
        "all_question_types": all_question_types,
        "existing_fields_to_render": existing_fields_to_render,
    }

    template_name = "buildings/survey_details/survey_details.html"

    # We want to render the entire template if the trigger is source-dataset-select
    # hx-swap is set to none on that attribute but we insert multiple elements out of band
    if request.htmx:
        if request.headers.get("Hx-Trigger") == "source-dataset-select":
            print(
                "Source dataset select triggered the HTMX request. Need to OOB swap JS variables and QB filters"
            )
            return render(request, "buildings/newsurvey/htmx_partial.html", context)
        else:
            rendered_block = render_block_to_string(
                template_name,
                "page-and-paging-controls",
                context=context,
                request=request,
            )
        return HttpResponse(content=rendered_block)

    return render(request, template_name, context)
