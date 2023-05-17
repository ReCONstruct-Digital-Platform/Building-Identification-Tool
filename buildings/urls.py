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
    path('all_buildings', views.all_buildings, name='all_buildings'),
    path('classify', views.classify_home, name="classify_home"),
    path('classify/<int:building_id>', views.classify, name="classify"),
    path('register', views.register, name="register"),
    path('login', views.login_page, name="login"),
    path('logout', views.logout_page, name="logout"),
    path('redeploy_server', views.redeploy_server, name="redeploy_server"),
]
