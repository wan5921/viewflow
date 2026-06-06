from django.urls import path, include
from viewflow.workflow import flow
from .flows import LeaveFlow


urlpatterns = [
    path('', flow.FlowAppViewset(LeaveFlow).urls),
]
