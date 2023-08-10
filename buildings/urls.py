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
from . import views

# This sets the application namespace
app_name = 'buildings'

urlpatterns = [
    path('', views.index, name="index"),
    # path('all_buildings', views.all_buildings, name='all_buildings'),
    path('survey', views.survey, name="survey"),
    path('survey/v1/<str:eval_unit_id>', views.survey_v1, name="survey_v1"),
    path('register', views.register, name="register"),
    path('login', views.login_page, name="login"),
    path('logout', views.logout_page, name="logout"),
    path('upload_imgs/<str:eval_unit_id>', views.upload_imgs, name="upload_imgs"),
    path('redeploy_server', views.redeploy_server, name="redeploy_server"),
]
