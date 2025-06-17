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
from buildings.views.new_dataset.forms import DatasetOnboardingForm

@login_required(login_url="account_login")
def new_dataset(request):
    """
    View to handle the creation of a new dataset.
    """
    template = 'buildings/new_dataset/new_dataset.html'

    form = DatasetOnboardingForm(user=request.user, data=request.POST)

    if request.method == 'POST':
        if form.is_valid():
            # Handle form submission for creating a new dataset
            pass  # Replace with actual logic

    # Render the form for creating a new dataset
    return render(request, template, {"form": form})