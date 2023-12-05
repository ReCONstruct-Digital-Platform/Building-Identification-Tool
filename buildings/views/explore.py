import logging
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect


log = logging.getLogger(__name__)


def index(request):
    template = 'buildings/index.html'
    context = {}

    rendered_content = render(request, template, context)
    return HttpResponse(content=rendered_content)
