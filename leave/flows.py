from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.flow import views

from .models import LeaveRequest


class LeaveFlow(flow.Flow):
    process_class = LeaveRequest
    process_title = 'Leave Request'
    process_description = 'Employee leave request workflow'

    start = (
        flow.Start(
            views.CreateProcessView.as_view(
                fields=['applicant', 'days', 'reason'],
            )
        )
        .Next(this.manager_approval)
    )

    manager_approval = (
        flow.View(
            views.UpdateProcessView.as_view(
                fields=['applicant', 'days', 'reason'],
            )
        )
        .Permission(auto_create=True)
        .Next(this.hr_approval)
    )

    hr_approval = (
        flow.View(
            views.UpdateProcessView.as_view(
                fields=['applicant', 'days', 'reason'],
            )
        )
        .Permission(auto_create=True)
        .Next(this.end)
    )

    end = flow.End()