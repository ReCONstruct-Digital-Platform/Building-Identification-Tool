import json

from django.db.models import F
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
)
from django.core.paginator import Paginator
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from django.utils.translation import gettext_lazy as _
from buildings.models import Dataset
from buildings.models.newmodels import Survey
from buildings.models.newsurveys import DynamicSurveyForm
from .forms_fields_widgets import OptionsFieldForm, OptionsFieldFormWithSpecify

import logging

from buildings.utils.utility import get_b64_encoded_json
from buildings.views.views import get_surveys_qb_filters_and_optgroups

log = logging.getLogger(__name__)


def transform_to_schema(field_type, options):
    if field_type == "true_false":
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
    if field_type == "multiple_choice":
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


def get_schema_template_with_defaults(field_type):
    if field_type == "true_false":
        return (
            {
                "pos": 0,
                "type": "boolean",
                "widget": "radio",
            },
            [
                {"pos": 0, "val": True, "label": {"en": "True"}},
                {"pos": 1, "val": False, "label": {"en": "False"}},
                {"pos": 2, "val": None, "label": {"en": "Other"}},
            ],
        )
    if field_type == "multiple_choice":
        return (
            {
                "pos": 0,
                "widget": "multi_checkbox_specify",
                "type": "text",  # TODO customizable
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


def get_field_form_class_and_default_vals(field_type: str):
    if field_type == "true_false":
        return (
            OptionsFieldForm,
            {"options": ["True", "False", "Other"]},
        )
    if field_type == "multiple_choice":
        return (
            OptionsFieldFormWithSpecify,
            {
                "options": ["Option 1", "Option 2"],
            },
        )


@login_required(login_url="account_login")
def render_question_preview(request):
    """
    Renders a question for preview. Called by HTMX dynamically as question is edited.
    """

    print(request.headers)
    print(request.GET)
    print(request.POST)

    # We accept both POST and GET here the same way
    data = getattr(request, request.method)
    field_type = data.get("field_type")
    field_num = data.get("field_num") or 0
    field_label = data.get("field_label") or f"Field {field_num} Label"
    question_text = data.get("question_text") or f"Question {field_num} Text"
    num_columns = data.get("num_columns") or 1

    # Generate appropriate new_field_form
    field_form_class, field_form_default_val = get_field_form_class_and_default_vals(
        field_type
    )

    schema_template, schema_default_options = get_schema_template_with_defaults(
        field_type
    )

    if request.POST:
        new_field_form = field_form_class(
            field_num,
            request.POST,
        )  # field_num is included in POST
        schema_options = transform_to_schema(field_type, data.getlist("options"))
    else:
        field_form_default_val |= {
            "field_label": field_label,
            "question_text": question_text,
        }
        new_field_form = field_form_class(
            field_num=field_num, data=field_form_default_val
        )
        schema_options = schema_default_options

    field_schema = schema_template | {
        "label": {"en": field_label},
        "question_text": {"en": question_text},
        "options": schema_options,
        "widget_config": {"attrs": {"class": f"survey-{num_columns}col"}},
    }

    # Get default schema options
    tmp_survey_for_render = Survey(schema={"field": field_schema})

    new_field_form.is_valid()

    rendered_field = DynamicSurveyForm(tmp_survey_for_render, request.POST)

    context = {
        "rendered_field": rendered_field,
        "new_field_form": new_field_form,
        "field_num": field_num,
    }

    return render(request, "buildings/edit_survey/form_renderer_template.html", context)


@login_required(login_url="account_login")
def edit_survey_questions(request, survey_slug):

    all_question_types = [
        {"id": "true_false", "label": "True/False/Other"},
        # {"id": "single_choice", "label": "Single-Choice"},
        {"id": "multiple_choice", "label": "Multiple-Choice"},
    ]

    num_results_per_page = 10

    if request.method == "POST":
        body = json.loads(request.body)
        if "survey_name" not in body or "ds" not in body:
            return HttpResponseBadRequest()

        survey_name = body.get("survey_name")
        dataset_slug = body.get("ds")
        dataset_query = get_b64_encoded_json(body.get("dataset_query")) or None
        survey_query = get_b64_encoded_json(body.get("survey_query")) or None

        dataset = Dataset.objects.filter(slug=dataset_slug).first()
        new_survey = Survey(
            name=survey_name,
            dataset=dataset,
            dataset_filter=dataset_query,
            surveys_filter=survey_query,
        )
        new_survey.save()

    survey = get_object_or_404(Survey, slug=survey_slug)
    dataset = survey.dataset

    # Get filters to display

    pagenum = request.GET.get("page") or 1
    orderby_field = request.GET.get("field") or "address"
    orderby_dir = request.GET.get("dir") or "asc"
    dataset_query = get_b64_encoded_json(request.GET.get("dataset_query"))
    survey_query = get_b64_encoded_json(request.GET.get("survey_query"))
    p_bldg_cols = get_b64_encoded_json(request.GET.get("user_bldg_cols"))
    p_survey_cols = get_b64_encoded_json(request.GET.get("user_survey_cols"))

    candidates = survey.get_target_population()

    print(candidates.count())

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

    page = Paginator(
        candidates.order_by(order_by), per_page=num_results_per_page
    ).get_page(pagenum)

    qb_dataset_filters = dataset.get_schema(prefix="")

    surveys_on_dataset = Survey.objects.filter(dataset=dataset)
    survey_filters_and_optgroups = get_surveys_qb_filters_and_optgroups(
        surveys_on_dataset
    )

    # TODO: Render all questions from survey schema
    test_form = None
    context = {
        "test_form": test_form,
        "survey": survey,
        "dataset": dataset,
        "surveys": surveys_on_dataset,
        "page": page,
        "survey_orderby_cols": survey_orderby_cols,
        "bldg_orderby_cols": bldg_orderby_cols,
        "qb_dataset_filters": qb_dataset_filters,
        "qb_surveys_filters": survey_filters_and_optgroups,
        "orderby_field": orderby_field,
        "orderby_dir": orderby_dir,
        "user_bldg_cols": user_bldg_cols,
        "default_bldg_cols": default_bldg_cols,
        "user_survey_cols": user_survey_cols,
        "default_survey_cols": default_survey_cols,
        "all_question_types": all_question_types,
    }

    template_name = "buildings/edit_survey/edit_survey.html"

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
