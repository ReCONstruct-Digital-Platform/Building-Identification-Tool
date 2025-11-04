import copy
import logging
from uuid import uuid4
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext_lazy as _
from buildings.models.newmodels import Survey, DatasetOnboardingJob, Dataset, Building
from buildings.utils import b2
from buildings.views.new_dataset.forms import DatasetOnboardingForm


log = logging.getLogger(__name__)


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
            job.status = DatasetOnboardingJob.Status.PENDING

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
                job.csv_file_location = filename

            # Store column mapping information in a JSON format that can be used
            # for processing the CSV later
            column_mapping = {
                "address": form.cleaned_data.get("address_column"),
                "ext_id": form.cleaned_data.get("external_id"),
                "admin_area_level_1": form.cleaned_data.get("state_column"),
                "postal_code": form.cleaned_data.get("zip_column"),
                "street_name": form.cleaned_data.get("street_name_column"),
                "street_num": form.cleaned_data.get("street_num_column"),
                "muni": form.cleaned_data.get("muni_column"),
                "submuni": form.cleaned_data.get("submuni_column"),
                "const_year": form.cleaned_data.get("const_year_column"),
                "num_floors": form.cleaned_data.get("num_floors_column"),
                "floor_area": form.cleaned_data.get("floor_area_column"),
            }

            # Remove any mappings that are None or empty
            column_mapping = {k: v for k, v in column_mapping.items() if v}

            # Add coordinate mappings if provided
            if form.cleaned_data.get("has_coordinates") == "True":
                column_mapping.update(
                    {
                        "lat": form.cleaned_data.get("lat_column"),
                        "lng": form.cleaned_data.get("lng_column"),
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
        "integer": "integer",
        "double": "double",
        "boolean": "radio",
        "date": "text",
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

    # Generate CSV download URL if available
    csv_download_url = None
    if upload_job and upload_job.csv_file_location:
        from buildings.utils.b2 import create_presigned_url

        csv_download_url = create_presigned_url(
            upload_job.csv_file_location, content_type="text/csv"
        )

    # Get buildings from the dataset
    buildings = Building.objects.filter(
        dataset=dataset, geocoding_error__isnull=True, has_streetview=True
    )

    # Calculate summary statistics
    total_buildings = buildings.count()
    failed_geocoding = Building.objects.filter(
        dataset=dataset, geocoding_error__isnull=False
    ).count()
    failed_streetview = Building.objects.filter(
        dataset=dataset, has_streetview=False
    ).count()

    context = {
        "dataset": dataset,
        "upload_job": upload_job,
        "surveys": surveys,
        "total_buildings": total_buildings,
        "failed_geocoding": failed_geocoding,
        "failed_streetview": failed_streetview,
        "csv_download_url": csv_download_url,
    }

    template_name = "buildings/new_dataset/dataset_detail.html"

    return render(request, template_name, context)
