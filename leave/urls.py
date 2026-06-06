from django.urls import path

from viewflow.workflow.flow import FlowAppViewset

from .flows import LeaveFlow

app_name = 'leave'

urlpatterns = [
    path('', FlowAppViewset(LeaveFlow).urls),
]