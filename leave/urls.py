from django.urls import path

from viewflow.contrib.auth import AuthViewset
from viewflow.urls import Site
from viewflow.workflow.flow import FlowAppViewset

from .flows import LeaveFlow


site = Site(
    title="Leave Flow Demo",
    viewsets=[
        FlowAppViewset(LeaveFlow, icon="event_note"),
    ],
)

urlpatterns = [
    path("accounts/", AuthViewset().urls),
    path("", site.urls),
]
