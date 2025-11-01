"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from buildings.views import views, api
from buildings.views.survey_details import survey_details
from buildings.views.new_dataset import new_dataset

# This sets the application namespace
app_name = "buildings"

urlpatterns = [
    path("test_react_1", views.test_react_1, name="test_react_1"),
    path("test_react_2", views.test_react_2, name="test_react_2"),
    path("", views.index, name="index"),
    path("profile", views.profile, name="profile"),
    path(
        "building/<str:building_slug>", views.building_details, name="building_details"
    ),
    path("datasets", views.datasets, name="datasets"),
    path("datasets/<str:dataset_slug>", views.dataset, name="dataset"),
    path("new_dataset", new_dataset.new_dataset, name="new_dataset"),
    path(
        "dataset_upload_success/<int:job_id>/",
        new_dataset.dataset_upload_success,
        name="dataset_upload_success",
    ),
    path(
        "dataset/<str:dataset_slug>/", new_dataset.dataset_detail, name="dataset_detail"
    ),
    path("results/", views.survey_results_no_slug, name="results"),
    path(
        "results/survey/<str:survey_slug>", views.survey_results, name="survey_results"
    ),
    path("surveys", views.surveys, name="surveys"),
    path("surveys/new_survey", views.new_survey, name="new_survey"),
    path(
        "surveys/<str:survey_slug>/details",
        survey_details.survey_details,
        name="survey_details",
    ),
    path(
        "surveys/<str:survey_slug>/survey",
        views.do_survey_redirect,
        name="do_survey_redirect",
    ),
    path(
        "surveys/<str:survey_slug>/<str:building_slug>",
        views.do_survey,
        name="do_survey",
    ),
    # HTMX APIs
    path(
        "render_question_preview",
        survey_details.render_question_preview,
        name="render_question_preview",
    ),
    # API only URLs
    path("excel", api.gen_excel, name="gen_excel"),
    path(
        "update_user_survey_column_settings",
        api.update_user_survey_column_settings,
        name="update_user_survey_column_settings",
    ),
    path("upload_imgs/<str:building_id>", api.upload_imgs, name="upload_imgs"),
]
