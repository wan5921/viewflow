from django.urls import path

from viewflow.urls import Site
from viewflow.workflow.flow import FlowAppViewset

from .flows import LeaveFlow


site = Site(
    viewsets=[
        FlowAppViewset(LeaveFlow, icon="event_note"),
    ]
)

urlpatterns = [
    path("leave/", site.urls),
]
