from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


def index(_request):
    return HttpResponse("Viewflow demo is running.")


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
]
