import json
import traceback
from typing import List

from django.db.models import Q, Value
from allauth.account.models import EmailAddress
from django.urls import reverse
from django.views import generic
from django.conf import settings
from django.db.models import F
from django.contrib import messages
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.core.paginator import Paginator
from django.db.models import JSONField
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models.expressions import RawSQL
from allauth.account.views import EmailView

from pprint import pformat, pprint
from django.utils.translation import gettext_lazy as _
import slugify
from buildings.forms import (
    ChangeEmailForm,
    ChangePasswordForm,
)
from buildings.models import Dataset
from buildings.models.newmodels import (
    Building,
    LatestViewData,
    ProblemFlag,
    Response,
    Survey,
    UserConfigs,
)
from buildings.models.newsurveys import DynamicSurveyForm
from buildings.models.models import EvalUnit

import logging

from buildings.utils.query_utils import DatasetQParser, SurveyQParser
from buildings.utils.utility import get_b64_encoded_json

log = logging.getLogger(__name__)


@login_required(login_url="account_login")
def index(request):
    template = "buildings/index.html"

    datasets = Dataset.objects.all().order_by("id")
    surveys = Survey.objects.all().order_by("id")

    total_votes = Response.objects.count() or 1
    latest_votes = Response.objects.order_by("-date_modified").all()

    num_user_votes = Response.objects.filter(created_by=request.user).count()
    user_votes = (
        Response.objects.filter(created_by=request.user)
        .order_by("-date_modified")
        .all()
    )

    page_num_latest = request.GET.get("latest_votes_page", 1)
    page_num_user = request.GET.get("user_votes_page", 1)
    latest_votes_page = Paginator(latest_votes, 10).get_page(page_num_latest)
    user_votes_page = Paginator(user_votes, 10).get_page(page_num_user)

    active_tab = request.GET.get("active_tab", "latest")

    context = {
        "datasets": datasets,
        "surveys": surveys,
        "total_votes": total_votes,
        "num_user_votes": num_user_votes,
        "latest_votes_page": latest_votes_page,
        "user_votes_page": user_votes_page,
        "active_tab": active_tab,
    }
    # This returns partial HTML content only for the activity tab
    if request.htmx:
        rendered_content = render_block_to_string(
            template, "activity-tab-content", context=context, request=request
        )
    else:
        rendered_content = render(request, template, context)

    return HttpResponse(content=rendered_content)


@login_required(login_url="account_login")
def datasets(request):

    datasets = Dataset.objects.all()
    context = {"datasets": datasets}
    return render(request, "buildings/datasets.html", context)


@login_required(login_url="account_login")
def dataset(request, dataset_slug: str):

    dataset = Dataset.objects.get(slug=dataset_slug)
    surveys = Survey.objects.filter(dataset=dataset)

    context = {"dataset": dataset, "surveys": surveys}
    return render(request, "buildings/dataset.html", context)


@login_required(login_url="account_login")
def surveys(request):
    template_name = "buildings/surveys.html"
    status = request.GET.get("status", "").upper()
    status = Q(status=status) if status else Q()

    surveys = Survey.objects.filter(status).order_by("-id").all()
    context = {"surveys": surveys}

    if request.htmx:
        rendered_block = render_block_to_string(
            template_name, "surveys-list", context=context, request=request
        )
        return HttpResponse(content=rendered_block)

    return render(request, "buildings/surveys.html", context)


@login_required(login_url="account_login")
def survey_results(request, survey_slug):

    num_results_per_page = 10
    template_name = "buildings/survey_results.html"

    print(f"META PATH_INFO: {request.META['PATH_INFO']}")

    pagenum = request.GET.get("page") or 1
    orderby_field = request.GET.get("field") or "address"
    orderby_dir = request.GET.get("dir") or "asc"
    dataset_query = get_b64_encoded_json(request.GET.get("dataset_query"))
    survey_query = get_b64_encoded_json(request.GET.get("survey_query"))
    p_bldg_cols = get_b64_encoded_json(request.GET.get("user_bldg_cols"))
    p_survey_cols = get_b64_encoded_json(request.GET.get("user_survey_cols"))

    surveys = Survey.objects.all()
    survey = Survey.objects.get(slug=survey_slug)
    dataset = survey.dataset

    results = survey.get_results().filter(response_data__isnull=False)

    default_bldg_cols = dataset.get_fields_to_display()
    default_survey_cols = survey.get_columns_to_display()

    user_config, _ = UserConfigs.objects.get_or_create(pk=request.user.id)

    # If we got a config from params, save in DB
    # Empty array means empty user config - if no param it would be empty dict
    dataset_id = str(dataset.id)
    if p_bldg_cols or p_bldg_cols == []:
        # The user set their config, we need to update the DB value and set
        # the current user columns to the parameter value
        user_bldg_cols = user_config.res_page_bldg_cols[dataset_id] = p_bldg_cols
        user_config.save()
    else:
        # No param set, take previous saved value or defaults
        user_bldg_cols = user_config.res_page_bldg_cols.get(
            dataset_id, default_bldg_cols
        )

    # Same thing for survey config columns
    survey_id = str(survey.id)
    if p_survey_cols or p_survey_cols == []:
        user_survey_cols = user_config.res_page_survey_cols[survey_id] = p_survey_cols
        user_config.save()
    else:
        user_survey_cols = user_config.res_page_survey_cols.get(
            survey_id, default_survey_cols
        )

    # Includes all columns we can order by
    bldg_orderby_cols = [
        {"id": "num_responses", "label": "Number of Responses"}
    ] + dataset.get_orderby_fields()
    survey_orderby_cols = default_survey_cols

    if dataset_query:
        dataset_q_parser = DatasetQParser(
            schema=dataset.schema, json_field_name="attrs"
        )
        dataset_q = dataset_q_parser.parse_query(dataset_query)
        print(dataset_q)
        results = results.filter(dataset_q)
        print(results.count())

    if survey_query:
        survey_q_parser = SurveyQParser(prefix=None)
        surveys_q = survey_q_parser.parse_query(survey_query)
        print(surveys_q)

        results = results.filter(surveys_q)
        print(results.count())

    # Need to use F to hide nulls, otherwise order_by descneding would show them first
    order_by = getattr(F(orderby_field), orderby_dir)(nulls_last=True)

    page = Paginator(
        results.order_by(order_by), per_page=num_results_per_page
    ).get_page(pagenum)

    qb_dataset_filters = dataset.get_schema(prefix="")
    qb_surveys_filters = {
        "optgroups": {survey.name: {"en": survey.name}},
        "filters": survey.get_query_builder_schema(field_prefix="response_data__"),
    }

    gen_excel_url = reverse("buildings:gen_excel")

    context = {
        "current_survey": survey,
        "surveys": surveys,
        "page": page,
        "survey_orderby_cols": survey_orderby_cols,
        "bldg_orderby_cols": bldg_orderby_cols,
        "qb_dataset_filters": qb_dataset_filters,
        "qb_surveys_filters": qb_surveys_filters,
        "orderby_field": orderby_field,
        "orderby_dir": orderby_dir,
        "user_bldg_cols": user_bldg_cols,
        "default_bldg_cols": default_bldg_cols,
        "user_survey_cols": user_survey_cols,
        "default_survey_cols": default_survey_cols,
        "gen_excel_url": gen_excel_url,
        "export_config": {"id": survey.id, "type": "survey"},
    }

    if request.htmx:
        rendered_block = render_block_to_string(
            template_name, "page-and-paging-controls", context=context, request=request
        )
        return HttpResponse(content=rendered_block)

    return render(request, template_name, context)


@login_required(login_url="account_login")
def do_survey_redirect(_, survey_slug):
    survey = get_object_or_404(Survey, slug=survey_slug)
    random_building = survey.get_next_building_to_survey()

    return redirect(
        "buildings:do_survey",
        survey_slug=survey_slug,
        building_slug=random_building.slug,
    )


@login_required(login_url="account_login")
def do_survey(request, survey_slug, building_slug):

    building = get_object_or_404(Building, slug=building_slug)
    survey = get_object_or_404(Survey, slug=survey_slug)
    surveys = Survey.objects.filter(status=Survey.Status.ACTIVE)

    # Verify the building is in the survey's target population or 404
    if not survey.is_building_in_target_pop(building):
        # TODO: Have a nice 404 page template
        raise Http404(
            f"Building {building.address} was not found in survey {survey.name}!"
        )

    next_building = survey.get_next_building_to_survey()
    next_building_url = reverse(
        "buildings:do_survey", args=[survey_slug, next_building.slug]
    )

    prev_response = None
    previous_problem_flag = None

    if request.method == "POST":

        logging.debug(f"POST: {request.POST}")

        if "problem_flag" in request.POST:
            # TODO: Add a note to the no_building flag
            flag = ProblemFlag(building=building, created_by=request.user)
            flag.save()

            return redirect(
                "buildings:do_survey",
                survey_slug=survey_slug,
                building_slug=next_building.slug,
            )

        # Save the last orientation/zoom for the building for later visits
        if "latest_view_data" in request.POST:
            data = request.POST.getlist("latest_view_data")[0]
            if len(data) > 0:
                data = json.loads(data)
                latest_view_data = LatestViewData(
                    building=building,
                    created_by=request.user,
                    sv_pano=data["sv_pano"],
                    sv_heading=data["sv_heading"],
                    sv_pitch=data["sv_pitch"],
                    sv_zoom=data["sv_zoom"],
                    marker_lat=data["marker_lat"],
                    marker_lng=data["marker_lng"],
                )
                latest_view_data.save()

        # Else, we're submitting a survey response
        form = DynamicSurveyForm(survey, request.POST)

        if form.is_valid():
            # Delete any previous problem flag at this location
            previous_problem_flag = ProblemFlag.objects.filter(
                building=building, created_by=request.user
            ).first()
            if previous_problem_flag:
                previous_problem_flag.delete()

            # Create a Response
            Response.objects.update_or_create(
                defaults={"data": form.cleaned_data},
                building=building,
                survey=survey,
                created_by=request.user,
            )

            return redirect(
                "buildings:do_survey",
                survey_slug=survey_slug,
                building_slug=next_building.slug,
            )
        else:
            logging.error("form invalid - shouldn't happen!")
            logging.error(form.errors)
            # We'll return the form with errors below, although this shouldn't happen

    else:
        # GET request
        previous_problem_flag = ProblemFlag.objects.filter(
            building=building, created_by=request.user
        ).first()

        if not previous_problem_flag:
            prev_response = Response.objects.filter(
                created_by=request.user, survey=survey, building=building
            ).first()

        form = DynamicSurveyForm(survey, prev_response.data if prev_response else None)

    # Columns config
    default_bldg_cols = survey.dataset.get_fields_to_display()
    # All the values for JS retrieval
    bldg_cols_and_values = {
        d["id"]: building.get_field(d["id"]) or "" for d in default_bldg_cols
    }
    # Get the saved user column config or the default if not set for the survey
    user_config, _ = UserConfigs.objects.get_or_create(pk=request.user.id)
    saved_col_config = user_config.get_survey_page_building_columns(survey)
    user_bldg_cols = (
        saved_col_config
        if saved_col_config or saved_col_config == []
        else default_bldg_cols
    )

    update_settings_url = reverse("buildings:update_user_survey_column_settings")

    context = {
        "survey": survey,
        "building": building,
        "key": settings.GOOGLE_MAPS_API_KEY,
        "building_coords": {
            "lat": building.lat,
            "lng": building.lng,
        },
        "geojson": None,
        "latest_view_data_value": None,
        "next_building_url": next_building_url,
        "form": form,
        "previous_problem_flag": previous_problem_flag,
        "default_bldg_cols": default_bldg_cols,
        "user_bldg_cols": user_bldg_cols,
        "bldg_cols_and_values": bldg_cols_and_values,
        "update_settings_url": update_settings_url,
        "all_surveys": surveys,
    }

    return render(request, "buildings/survey_rendering_full.html", context)


@login_required(login_url="account_login")
def query(request, dataset_slug):

    # Get the dataset by slug
    dataset = get_object_or_404(Dataset, slug=dataset_slug)

    if request.method == "POST":
        query = json.loads(request.body)
        log.debug(query)
        parser = DatasetQParser(schema=dataset.schema)
        q = parser.parse_query(query)
        log.debug(q)
        buildings = Building.objects.filter(dataset_id=dataset.id).filter(q)

        print(buildings.query)
        print(buildings.count())

    context = {
        "dataset_name": dataset.name,
        "querybuilder_filters": dataset.schema,
    }
    return render(request, "buildings/query.html", context)


def get_surveys_qb_filters_and_optgroups_for_results(survey: Survey):

    filters = []
    survey_name = survey.name

    optgroups = {survey_name: {"en": survey_name}}

    filters = survey.get_query_builder_schema(field_prefix="data_")

    return {"filters": filters, "optgroups": optgroups}


def get_surveys_qb_filters_and_optgroups(surveys: List[Survey]):

    combined = []
    optgroups = {}

    for survey in surveys:
        survey_name = survey.name
        optgroups[survey_name] = {"en": survey_name}
        combined.extend(survey.get_query_builder_schema())

    return {"filters": combined, "optgroups": optgroups}


def get_survey_target_population(dataset_q, surveys_q):
    candidates = (
        Building.objects.filter(dataset_q)
        .annotate(
            response_data=RawSQL(
                """select jsonb_object_agg(key, value)
                    from (
                        select 
                            id, key, jsonb_agg(distinct value) as value
                            from (
                                select 
                                    id, key, jsonb_array_elements(value) as value
                                from (
                                    select 
                                        id, key,
                                        case jsonb_typeof(value)
                                            when 'array' then value
                                            else jsonb_build_array(value)
                                        end as value
                                    from (
                                        select 
                                            r.building_id as id,
                                            concat('s_', r.survey_id, '_', (jsonb_each(r.data)).key) as key, 
                                            (jsonb_each(r.data)).value 
                                        from responses r
                                        where r.building_id = buildings.id
                                    ) as sub
                                ) as sub2
                            ) as sub3    
                        group by id, key
                    ) as sub4
                    group by id""",
                (),
                output_field=JSONField(),
            )
        )
        .filter(surveys_q)
    )
    return candidates


@login_required(login_url="account_login")
def newsurvey_api(request, dataset_slug):
    # Get the dataset by slug
    dataset = get_object_or_404(Dataset, slug=dataset_slug)

    surveys_on_dataset = Survey.objects.filter(dataset=dataset)
    log.info(f"{surveys_on_dataset.count()} surveys found on dataset {dataset.name}")

    if request.method == "POST":
        query = json.loads(request.body)
        log.debug(pformat(query))

        dataset_query = query["dataset_query"]
        dataset_q_parser = DatasetQParser(schema=dataset.schema)
        dataset_q = dataset_q_parser.parse_query(dataset_query)

        surveys_query = query["surveys_query"]

        survey_q_parser = SurveyQParser()
        surveys_q = survey_q_parser.parse_query(surveys_query)
        print(surveys_query)

        candidates = get_survey_target_population(dataset_q, surveys_q)

        print(candidates)
        print(candidates.count())


@login_required(login_url="account_login")
def new_survey(request):
    """
    Create a new survey on a dataset, and optionally the output of other surveys on that dataset
    """

    num_results_per_page = 10

    print(f"META PATH_INFO: {request.META['PATH_INFO']}")

    if request.method == "POST":
        body = json.loads(request.body)
        if "survey_name" not in body or "source_dataset" not in body:
            return HttpResponseBadRequest()

        survey_name = body.get("survey_name")
        dataset_slug = body.get("source_dataset")
        description = body.get("survey_decription")
        dataset_query = get_b64_encoded_json(body.get("dataset_query")) or None
        survey_query = get_b64_encoded_json(body.get("survey_query")) or None

        dataset = Dataset.objects.filter(slug=dataset_slug).first()
        new_survey = Survey(
            name=survey_name,
            description=description,
            dataset=dataset,
            dataset_filter=dataset_query,
            surveys_filter=survey_query,
            created_by=request.user,
        )
        new_survey.save()
        print(f"Created new survey {new_survey.id} {new_survey.slug}")
        return redirect("buildings:edit_survey", survey_slug=new_survey.slug)

    datasets = Dataset.objects.all()
    # TODO: what if slug is invalid?
    p_dataset_slug = request.GET.get("source_dataset")
    dataset = (
        Dataset.objects.filter(slug=p_dataset_slug).first()
        if p_dataset_slug
        else datasets[0]
    )
    if not dataset:
        raise Http404(f"No dataset found for {p_dataset_slug}")

    pagenum = request.GET.get("page") or 1
    orderby_field = request.GET.get("field") or "address"
    orderby_dir = request.GET.get("dir") or "asc"
    dataset_query = get_b64_encoded_json(request.GET.get("dataset_query"))
    survey_query = get_b64_encoded_json(request.GET.get("survey_query"))
    p_bldg_cols = get_b64_encoded_json(request.GET.get("user_bldg_cols"))
    p_survey_cols = get_b64_encoded_json(request.GET.get("user_survey_cols"))

    # Survey can be None if this is the first survey created on a dataset
    surveys_on_dataset = Survey.objects.filter(dataset=dataset)

    # We create a temporary new survey object so we can use its methods to get the target pop
    # We will only save this object if the user submitted the form (i.e. it's a POST request)
    new_survey = Survey(
        dataset=dataset,
        dataset_filter=dataset_query or None,
        surveys_filter=survey_query or None,
    )
    candidates = new_survey.get_target_population()

    print(candidates.count())

    default_bldg_cols = dataset.get_fields_to_display()
    default_survey_cols = []  # survey.get_columns_to_display()

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

    survey_filters_and_optgroups = get_surveys_qb_filters_and_optgroups(
        surveys_on_dataset
    )

    context = {
        "current_dataset": dataset,
        "surveys": surveys_on_dataset,
        "datasets": datasets,
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
    }

    template_name = "buildings/new_survey/new_survey.html"

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


class EvalUnitDetailView(generic.DetailView):
    """
    TODO: Create a detail view for out eval units, showing votes and info summary
    """

    model = EvalUnit
    template_name = "buildings/detail.html"


@login_required(login_url="account_login")
def profile(request):
    current_email = EmailAddress.objects.get_for_user(
        user=request.user, email=request.user.email
    )

    if request.method == "POST":
        if "submit_change_email" in request.POST:
            new_email_form = ChangeEmailForm(user=request.user, data=request.POST)

            if new_email_form.is_valid():
                # Perhaps hacky way to do this, but reuse allauth's email registration view
                v = EmailView()
                post_data = request.POST.copy()
                post_data["action_add"] = ""
                request.POST = post_data
                v.request = request
                res = v.post(request)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"Verification sent to {request.POST['email']}. Your email address will be changed once you verify it.",
                    extra_tags="email_verification_message",
                )
            else:
                print(new_email_form.errors)
                context = {
                    "pw_form": ChangePasswordForm(user=request.user),
                    "email_form": new_email_form,
                    "current_email": current_email,
                }
                return render(request, "buildings/profile.html", context=context)

        elif "submit_change_pw" in request.POST:
            new_pw_form = ChangePasswordForm(user=request.user, data=request.POST)

            if new_pw_form.is_valid():
                new_pw_form.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"Successfully changed your password!",
                    extra_tags="password_change_message",
                )
            else:
                print(f"not valid: {new_pw_form.errors.as_data()}")
                context = {
                    "pw_form": new_pw_form,
                    "email_form": ChangeEmailForm(user=request.user),
                    "current_email": current_email,
                }
                return render(request, "buildings/profile.html", context=context)

            pass

    change_pw_form = ChangePasswordForm(user=request.user)
    change_email_form = ChangeEmailForm(user=request.user)

    context = {
        "pw_form": change_pw_form,
        "email_form": change_email_form,
        "current_email": current_email,
    }
    return render(request, "buildings/profile.html", context=context)


"""
POC test to integrate react components into pages
"""
def test_react_1(request):
    template = "react_test/test_react_1.html"
    return render(request, template, context={})


def test_react_2(request):
    template = "react_test/test_react_2.html"
    return render(request, template, context={})
