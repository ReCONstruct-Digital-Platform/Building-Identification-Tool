import json

from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext_lazy as _
from buildings.models.newmodels import Survey
from buildings.models.newsurveys import DynamicSurveyForm


import logging

from buildings.utils.utility import get_b64_encoded_json
from buildings.views.survey_details.survey_details_utils import (
    get_bound_field_form_from_schema,
    get_field_form_and_schema,
    get_field_form_class_and_default_vals,
    get_json_schema_with_default_options,
    transform_options_to_survey_schema,
)
from buildings.views.views import get_surveys_qb_filters_and_optgroups

log = logging.getLogger(__name__)


QUESTION_TYPES = [
    {"id": "number", "label": "Number"},
    {"id": "text", "label": "Text"},
    {"id": "boolean", "label": "True/False"},
    {"id": "boolean_or_null", "label": "True/False/Other"},
    {"id": "radio", "label": "Single-Choice"},
    {"id": "multi_checkbox", "label": "Multiple-Choice"},
    {"id": "radio_w_specify", "label": "Single-Choice with Specify"},
    {"id": "multi_checkbox_specify", "label": "Multiple-Choice with Specify"},
]


@login_required(login_url="account_login")
def survey_details(request, survey_slug):

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

    # Need to use F to hide nulls, otherwise order_by descending would show them first
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

        field_type = field_schema.get("type")

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
        "all_question_types": QUESTION_TYPES,
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

    return render(
        request, "buildings/survey_details/form_renderer_template.html", context
    )
