from django.utils.translation import gettext_lazy as _

from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.flow.views import CreateProcessView, UpdateProcessView

from .models import LeaveRequest


class LeaveFlow(flow.Flow):
    process_class = LeaveRequest
    process_title = _("Leave requests")
    process_description = _("Leave approval process")
    process_summary_template = "{{ process.applicant }} · {{ process.days }} day(s)"
    process_result_template = "{{ process.applicant }} · {{ process.days }} day(s)"

    start = (
        flow.Start(
            CreateProcessView.as_view(fields=["applicant", "days", "reason"])
        )
        .Annotation(
            title=_("Submit leave request"),
            description=_("Create a leave request and start the approval workflow"),
        )
        .Permission(auto_create=True)
        .Next(this.manager_approval)
    )

    manager_approval = (
        flow.View(UpdateProcessView.as_view(fields=[]))
        .Annotation(
            title=_("Manager approval"),
            description=_("Manager reviews the leave request"),
        )
        .Permission(auto_create=True)
        .Next(this.hr_approval)
    )

    hr_approval = (
        flow.View(UpdateProcessView.as_view(fields=[]))
        .Annotation(
            title=_("HR approval"),
            description=_("HR completes the leave approval"),
        )
        .Permission(auto_create=True)
        .Next(this.end)
    )

    end = flow.End()
