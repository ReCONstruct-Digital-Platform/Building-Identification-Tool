import copy
from datetime import datetime, time
import json
import logging
from uuid import uuid4

from django.conf import settings
from django.db.models import F, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext_lazy as _
from buildings.models.newmodels import Survey, DatasetOnboardingJob, Dataset, Building
from buildings.models.newsurveys import DynamicSurveyForm
from buildings.utils import b2
from buildings.views.new_dataset.forms import DatasetOnboardingForm
from buildings.utils.utility import get_b64_encoded_json


log = logging.getLogger(__name__)


# Status constants for DatasetOnboardingJob
class JobStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@login_required(login_url="account_login")
def new_dataset(request):
    """
    View to handle the creation of a new dataset.
    """
    template = "buildings/new_dataset/new_dataset.html"

    if request.method == "POST":
        form = DatasetOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            # Create a new dataset onboarding job
            job = form.save(commit=False)
            job.created_by = request.user
            job.status = JobStatus.PENDING

            b2_client = b2.get_client()

            # Store CSV file location
            if "csv_file" in request.FILES:
                csv_file = request.FILES["csv_file"]
                # Generate a unique filename to avoid collisions
                filename = f"{request.user.username}/datasets/{uuid4()}/{csv_file.name}"

                # Try to upload the image
                b2_client.upload_fileobj(
                    Fileobj=csv_file,
                    Bucket=settings.B2_BUCKET_IMAGES,
                    Key=filename,
                    ExtraArgs={
                        "ContentType": "text/csv",
                        "Metadata": {
                            "user_id": str(request.user.id),
                            "username": str(request.user.username),
                        },
                    },
                )
                log.info(
                    f"Uploaded {filename} to B2 bucket {settings.B2_BUCKET_IMAGES}"
                )
                job.csv_file_path = filename

            # Store column mapping information in a JSON format that can be used
            # for processing the CSV later
            column_mapping = {
                "address": form.cleaned_data.get("address_column"),
                "admin_area_level_1": form.cleaned_data.get("state_column"),  # Province
                "postal_code": form.cleaned_data.get("zip_column"),
            }

            # Add coordinate mappings if provided
            if form.cleaned_data.get("has_coordinates") == "True":
                column_mapping.update(
                    {
                        "lat": form.cleaned_data.get("lat_column"),
                        "lng": form.cleaned_data.get("lng_column"),
                    }
                )

            # Add building detail mappings if provided
            if form.cleaned_data.get("has_building_details") == "True":
                column_mapping.update(
                    {
                        "street_name": form.cleaned_data.get("street_name_column"),
                        "street_num": form.cleaned_data.get("street_num_column"),
                        "muni": form.cleaned_data.get("muni_column"),
                        "submuni": form.cleaned_data.get("submuni_column"),
                        "const_year": form.cleaned_data.get("const_year_column"),
                        "num_floors": form.cleaned_data.get("num_floors_column"),
                        "floor_area": form.cleaned_data.get("floor_area_column"),
                    }
                )

            # Process unmapped columns and their data types
            attrs_schema = {}
            if unmapped_columns := form.cleaned_data.get("unmapped_columns"):
                for column, data_type in unmapped_columns.items():
                    # Add to column mapping with attrs__ prefix to indicate it's a dynamic attribute
                    column_mapping[f"attrs__{column}"] = column

                    # Add to schema definition
                    attrs_schema[column] = {
                        "type": data_type,
                        "label": {"en": column},  # Use column name as label
                    }

            # Store the schema for attrs fields
            job.attrs_schema = attrs_schema

            # Store the complete column mapping in the job
            job.column_mapping = column_mapping
            # Create a new Dataset with appropriate schema
            dataset = create_dataset_with_schema(job, request.user)
            job.dataset = dataset
            job.save()

            # Redirect to a success page
            return redirect("buildings:dataset_upload_success", job_id=job.id)
    else:
        form = DatasetOnboardingForm(
            initial={"name": f"New dataset {datetime.now()}", "description": ""}
        )

    # Render the form for creating a new dataset
    return render(request, template, {"form": form})


def create_dataset_with_schema(job, user):
    """
    Create a Dataset with appropriate schema based on the DatasetOnboardingJob.
    """
    # Create schema for the dataset
    schema = copy.deepcopy(Dataset.BASE_SCHEMA)

    # Add dynamic attributes to schema
    for attr_key, attr_value in job.attrs_schema.items():
        schema.append(
            {
                "id": f"attrs__{attr_key}",
                "field": f"attrs__{attr_key}",
                "label": {"en": attr_key},
                "optgroup": "attributes",
                "type": attr_value["type"],
                "input": get_input_type_for_data_type(attr_value["type"]),
            }
        )

    # Create the dataset
    dataset = Dataset.objects.create(
        name=job.name, description=job.description, created_by=user, schema=schema
    )

    return dataset


def get_input_type_for_data_type(data_type):
    """
    Map data types to input types for the schema.
    """
    mapping = {
        "string": "text",
        "number": "number",
        "boolean": "radio",
        "date": "text",  # Could be improved with a date picker
        "array": "text",
        "object": "text",
    }
    return mapping.get(data_type, "text")


@login_required(login_url="account_login")
def dataset_upload_success(request, job_id):
    """
    View to display success message after dataset upload.
    """
    job = get_object_or_404(DatasetOnboardingJob, id=job_id, created_by=request.user)

    return render(request, "buildings/new_dataset/upload_success.html", {"job": job})


@login_required(login_url="account_login")
def dataset_detail(request, dataset_slug):
    """
    View to display dataset details and a paginated list of buildings.
    Similar to survey_results but focused on buildings from a dataset.
    """
    # Get the dataset
    dataset = get_object_or_404(Dataset, slug=dataset_slug)

    upload_job = DatasetOnboardingJob.objects.filter(dataset=dataset).first()
    surveys = Survey.objects.filter(dataset=dataset)

    # Pagination parameters
    num_results_per_page = 10
    pagenum = request.GET.get("page") or 1
    orderby_field = request.GET.get("field") or "address"
    orderby_dir = request.GET.get("dir") or "asc"
    geocoding_filter = request.GET.get("geocoding_filter")

    # Get column configurations
    p_bldg_cols = get_b64_encoded_json(request.GET.get("user_bldg_cols", ""))

    # Get buildings from the dataset
    buildings = Building.objects.filter(dataset=dataset)

    # Apply geocoding filter if specified
    if geocoding_filter:
        if geocoding_filter == "success":
            buildings = buildings.filter(geocoding_error__isnull=True)
        elif geocoding_filter == "failed":
            buildings = buildings.filter(geocoding_error__isnull=False)

    # Calculate summary statistics
    total_buildings = buildings.count()
    geocoded_buildings = buildings.filter(geocoding_error__isnull=True).count()
    failed_geocoding = buildings.filter(geocoding_error__isnull=False).count()

    # Set up ordering
    order_by = getattr(F(orderby_field), orderby_dir)(nulls_last=True)
    buildings = buildings.order_by(order_by, "id")

    # Paginate the buildings
    page = Paginator(buildings, per_page=num_results_per_page).get_page(pagenum)

    # Column configuration
    default_bldg_cols = dataset.get_fields_to_display()

    if p_bldg_cols or p_bldg_cols == []:
        user_bldg_cols = p_bldg_cols
    else:
        user_bldg_cols = default_bldg_cols

    # Fields for ordering
    bldg_orderby_cols = dataset.get_orderby_fields()

    context = {
        "dataset": dataset,
        "upload_job": upload_job,
        "surveys": surveys,
        "page": page,
        "bldg_orderby_cols": bldg_orderby_cols,
        "orderby_field": orderby_field,
        "orderby_dir": orderby_dir,
        "user_bldg_cols": user_bldg_cols,
        "default_bldg_cols": default_bldg_cols,
        "geocoding_filter": geocoding_filter,
        "total_buildings": total_buildings,
        "geocoded_buildings": geocoded_buildings,
        "failed_geocoding": failed_geocoding,
    }

    template_name = "buildings/new_dataset/dataset_detail.html"

    # Handle HTMX requests for pagination
    if request.htmx:
        rendered_block = render_block_to_string(
            template_name,
            "page-and-paging-controls",
            context=context,
            request=request,
        )
        return HttpResponse(content=rendered_block)

    return render(request, template_name, context)
