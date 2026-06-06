from django.utils.translation import gettext_lazy as _

from viewflow import this
from viewflow.workflow import Flow, flow
from viewflow.workflow.flow import views

from .models import LeaveRequest


class LeaveFlow(Flow):
    process_class = LeaveRequest
    process_title = _("Leave Request")
    process_description = _("Employee leave request approval workflow")

    start = (
        flow.Start(views.CreateProcessView.as_view(
            fields=["applicant", "days", "reason"],
        ))
        .Annotation(
            title=_("New Leave Request"),
            description=_("Submit a new leave request"),
            summary_template=_("Leave request from {{ process.applicant }}"),
        )
        .Permission(auto_create=True)
        .Next(this.manager_approval)
    )

    manager_approval = (
        flow.View(views.UpdateProcessView.as_view(
            fields=["approved"],
        ))
        .Annotation(
            title=_("Manager Approval"),
            description=_("Review and approve the leave request"),
            summary_template=_("Manager review for {{ process.applicant }}"),
            result_template=_(
                "Manager {{ process.approved|yesno:'Approved,Rejected' }}"
            ),
        )
        .Permission(auto_create=True)
        .Next(this.hr_approval)
    )

    hr_approval = (
        flow.View(views.UpdateProcessView.as_view(
            fields=["approved"],
        ))
        .Annotation(
            title=_("HR Approval"),
            description=_("HR final approval of the leave request"),
            summary_template=_("HR review for {{ process.applicant }}"),
            result_template=_(
                "HR {{ process.approved|yesno:'Approved,Rejected' }}"
            ),
        )
        .Permission(auto_create=True)
        .Next(this.end)
    )

    end = flow.End()
