import io
import json
from datetime import datetime
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404


from buildings.models.newmodels import (
    Survey,
    UserConfigs,
)
from buildings.models.models import (
    EvalUnit,
    UploadImageJob,
)
import logging

from buildings.utils.query_utils import DatasetQParser, SurveyQParser
from buildings.utils.utility import get_b64_encoded_json


@require_POST
@login_required(login_url="account_login")
def upload_imgs(request, building_id):
    """
    We'll process the image uploading asynchronously using a PythonAnywhere (PA) Always-on Task
    We have to do this because PA doesn't support launching background threads.
    If we switch to another VPS, we should implement the background thread solution
    https://blog.pythonanywhere.com/198/
    https://www.pythonanywhere.com/forums/topic/3627/
    """
    data = json.loads(request.body)
    eval_unit = get_object_or_404(EvalUnit, pk=building_id)
    if settings.DEBUG:
        print("debug mode job not created")
        return HttpResponse("debug mode job not created")
    UploadImageJob(
        eval_unit=eval_unit,
        user=request.user,
        job_data=data,
        status=UploadImageJob.Status.PENDING,
    ).save()
    return HttpResponse("Ok")


@require_POST
@login_required(login_url="account_login")
def update_user_survey_column_settings(request):
    logging.debug(f"Update user survey column settings: {request.body}")
    body = json.loads(request.body)
    survey = Survey.objects.get(slug=body["survey_slug"])

    if sur_page_bldg_cols := body.get("sur_page_bldg_cols", None):
        user_config, _ = UserConfigs.objects.get_or_create(pk=request.user.id)
        user_config.sur_page_bldg_cols = {survey.id: sur_page_bldg_cols}
        user_config.save()

    return HttpResponse("Ok")


@require_POST
@login_required(login_url="account_login")
def gen_excel(request):

    body = json.loads(request.body)

    config = body.get("export_config")

    # TODO: Want to support exporting Dataset and Survey candidates as well
    if config["type"] not in ["survey"]:
        raise Exception(f"Unsupported export type {config['type']}")

    survey = Survey.objects.get(pk=config["id"])
    dataset = survey.dataset

    default_bldg_cols = dataset.get_orderby_fields()
    default_survey_cols = survey.get_columns_to_display()

    orderby_field = body.get("field") or "address"
    orderby_dir = body.get("dir") or "asc"
    dataset_query = get_b64_encoded_json(body.get("dataset_query"))
    survey_query = get_b64_encoded_json(body.get("survey_query"))

    # Take the columns from curfrent query or default otherwise
    bldg_cols = get_b64_encoded_json(body.get("user_bldg_cols")) or default_bldg_cols
    survey_cols = (
        get_b64_encoded_json(body.get("user_survey_cols")) or default_survey_cols
    )

    results = survey.get_results()
    if dataset_query:
        dataset_q_parser = DatasetQParser(
            schema=dataset.schema, json_field_name="attrs"
        )
        dataset_q = dataset_q_parser.parse_query(dataset_query)
        results = results.filter(dataset_q)

    if survey_query:
        survey_q_parser = SurveyQParser(prefix=None)
        surveys_q = survey_q_parser.parse_query(survey_query)
        results = results.filter(surveys_q)

    # Need to use F to hide nulls, otherwise order_by descending would show them first
    order_by = getattr(F(orderby_field), orderby_dir)(nulls_last=True)

    paginator = Paginator(results.order_by(order_by), per_page=50)

    bldg_fields = [f["id"] for f in bldg_cols]
    survey_fields = [f["id"] for f in survey_cols]

    bldg_header = [f["label"] for f in bldg_cols]
    survey_header = [f["label"] for f in survey_cols]
    # all columns currently configured
    header = bldg_header + survey_header

    binary_object = io.BytesIO()

    wb = Workbook()
    ws = wb.active
    ws.title = "Buildings with their Responses"
    ws.append(header)

    ws2 = wb.create_sheet(title="Individual Responses")
    header2 = (
        ["Respondent", "Respondent Email", "Date Created", "Date Modified"]
        + survey_header
        + bldg_header
    )
    ws2.append(header2)

    for i in range(paginator.num_pages):
        page = paginator.get_page(i)

        for building in page:

            row = []

            for field in bldg_fields:
                if "attrs__" in field:
                    val = building.attrs[field.replace("attrs__", "")]
                else:
                    val = getattr(building, field)
                row.append(val)

            for field in survey_fields:
                # These are all lists
                val = building.response_data.get(field)
                if not val:
                    row.append("")
                    continue

                # Convert each inner value to something nice
                converted = []
                for v in val:
                    if v == None:
                        continue

                    if not isinstance(v, str):
                        converted.append(str(v))
                    else:
                        converted.append(v)

                val = ", ".join(converted)
                row.append(val)

            ws.append(row)

            # Now process individual responses
            for resp in building.response_set.filter(survey=survey):
                row2 = []
                row2.extend(
                    [
                        resp.created_by.username,
                        resp.created_by.email,
                        resp.date_added.strftime("%Y-%m-%dT%H:%M:%S"),
                        resp.date_modified.strftime("%Y-%m-%dT%H:%M:%S"),
                    ]
                )
                for field in survey_fields:
                    val = resp.data.get(field)

                    if val == None:
                        val = ""

                    elif not isinstance(val, list):
                        if not isinstance(val, str):
                            val = str(val)
                    else:
                        # Convert each inner value to something nice
                        converted = []
                        for v in val:
                            if v == None:
                                continue

                            if not isinstance(v, str):
                                converted.append(str(v))
                            else:
                                converted.append(v)

                        val = ", ".join(converted)
                    row2.append(val)

                for field in bldg_fields:
                    if "attrs__" in field:
                        val = resp.building.attrs[field.replace("attrs__", "")]
                    else:
                        val = getattr(resp.building, field)

                    row2.append(val)

                ws2.append(row2)

    # ws.auto_filter.ref = ws.dimensions
    table1 = Table(displayName="Table1", ref=ws.dimensions)
    table2 = Table(displayName="Table2", ref=ws2.dimensions)

    # Add a default style with striped rows and banded columns
    style = TableStyleInfo(
        name="TableStyleMedium9",
        showRowStripes=True,
    )
    table1.tableStyleInfo = table2.tableStyleInfo = style

    """
    Table must be added using ws.add_table() method to avoid duplicate names.
    Using this method ensures table name is unque through out defined names and all other table name. 
    """
    ws.add_table(table1)
    ws2.add_table(table2)

    wb.save(binary_object)
    binary_object.seek(0)
    binary_data = binary_object.read()

    response = HttpResponse(
        # full list of content_types can be found here
        # https://stackoverflow.com/a/50860387/13946204
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.write(binary_data)
    return response
