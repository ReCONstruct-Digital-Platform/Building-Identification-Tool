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
from buildings.views.edit_survey import edit_survey
from django.views.generic import TemplateView

# This sets the application namespace
app_name = "buildings"

urlpatterns = [
    path("hello/", TemplateView.as_view(template_name="hello.html")),
    path("", views.index, name="index"),
    path("profile", views.profile, name="profile"),
    path("query/<str:dataset_slug>", views.query, name="query"),
    path("datasets", views.datasets, name="datasets"),
    path("datasets/<str:dataset_slug>", views.dataset, name="dataset"),
    path(
        "datasets/<str:dataset_slug>/newsurvey_questions",
        views.edit_survey_questions,
        name="newsurvey_questions",
    ),
    path(
        "results/survey/<str:survey_slug>", views.survey_results, name="survey_results"
    ),
    path("surveys", views.surveys, name="surveys"),
    path("surveys/new_survey", views.new_survey, name="new_survey"),
    path(
        "surveys/<str:survey_slug>/edit",
        edit_survey.edit_survey_questions,
        name="edit_survey",
    ),
    path(
        "render_question_preview",
        edit_survey.render_question_preview,
        name="render_question_preview",
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
    # API only URLs
    path("excel", api.gen_excel, name="gen_excel"),
    path(
        "update_user_survey_column_settings",
        api.update_user_survey_column_settings,
        name="update_user_survey_column_settings",
    ),
    path("upload_imgs/<str:building_id>", api.upload_imgs, name="upload_imgs"),
]
