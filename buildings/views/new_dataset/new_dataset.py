import json

from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext_lazy as _
from buildings.models.newmodels import Survey, DatasetOnboardingJob
from buildings.models.newsurveys import DynamicSurveyForm
from buildings.views.new_dataset.forms import DatasetOnboardingForm

@login_required(login_url="account_login")
def new_dataset(request):
    """
    View to handle the creation of a new dataset.
    """
    template = 'buildings/new_dataset/new_dataset.html'

    form = DatasetOnboardingForm(data=request.POST)

    if request.method == 'POST':
        if form.is_valid():
            # Create a new dataset onboarding job
            job = form.save(commit=False)
            job.created_by = request.user

            # Store CSV file location
            if "csv_file" in request.FILES:
                # In a real implementation, you would save the file to a storage location
                # and store the path in job.csv_file_location
                job.csv_file_location = "temp_location"  # Placeholder

            # Save the job
            job.save()

            # Store column mapping information in a JSON format that can be used
            # for processing the CSV later
            column_mapping = {
                "address": form.cleaned_data.get("address_column"),
                "state": form.cleaned_data.get("state_column"),
                "zip": form.cleaned_data.get("zip_column"),
            }

            # Add coordinate mappings if provided
            if form.cleaned_data.get("has_coordinates") == "yes":
                column_mapping.update(
                    {
                        "lat": form.cleaned_data.get("lat_column"),
                        "lng": form.cleaned_data.get("lng_column"),
                    }
                )

            # Add building detail mappings if provided
            if form.cleaned_data.get("has_building_details") == "yes":
                column_mapping.update(
                    {
                        "street_name": form.cleaned_data.get("street_name_column"),
                        "street_num": form.cleaned_data.get("street_num_column"),
                        "street_num_2": form.cleaned_data.get("street_num_2_column"),
                        "muni": form.cleaned_data.get("muni_column"),
                        "submuni": form.cleaned_data.get("submuni_column"),
                        "admin_area_level_1": form.cleaned_data.get(
                            "state_column"
                        ),  # Reuse state column
                        "postal_code": form.cleaned_data.get(
                            "zip_column"
                        ),  # Reuse zip column
                        "const_year": form.cleaned_data.get("const_year_column"),
                        "num_floors": form.cleaned_data.get("num_floors_column"),
                        "floor_area": form.cleaned_data.get("floor_area_column"),
                    }
                )

            # Process unmapped columns and their data types
            attrs_schema = {}
            if form.cleaned_data.get("unmapped_columns"):
                try:
                    unmapped_columns = json.loads(
                        form.cleaned_data.get("unmapped_columns")
                    )
                    for column, data_type in unmapped_columns.items():
                        # Add to column mapping with attrs__ prefix to indicate it's a dynamic attribute
                        column_mapping[f"attrs__{column}"] = column

                        # Add to schema definition
                        attrs_schema[column] = {
                            "type": data_type,
                            "label": {"en": column},  # Use column name as label
                        }
                except json.JSONDecodeError:
                    # Handle invalid JSON
                    pass

            # Store the schema for attrs fields
            job.attrs_schema = attrs_schema

            # Store the complete column mapping in the job
            job.column_mapping = column_mapping
            job.save()

            # Redirect to a success page or dataset list
            return redirect("buildings:index")  # Replace with appropriate URL

    # Render the form for creating a new dataset
    return render(request, template, {"form": form})
