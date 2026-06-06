from django.contrib.auth.models import User
from viewflow import this
from viewflow.workflow import Flow, flow
from viewflow.workflow.flow.views import CreateProcessView, UpdateProcessView

from .models import LeaveRequest


class LeaveFlow(Flow):
    """请假审批流程"""
    process_class = LeaveRequest
    process_title = "请假申请"
    process_description = "员工请假审批流程"

    start = (
        flow.Start(
            CreateProcessView.as_view(
                fields=['applicant', 'days', 'reason'],
                template_name='leave/start_form.html'
            )
        )
        .Next(this.manager_approval)
    )

    manager_approval = (
        flow.View(
            UpdateProcessView.as_view(
                fields=['manager_approved'],
                template_name='leave/approval_form.html'
            )
        )
        .Permission('leave.can_approve_manager')
        .Next(this.manager_decision)
    )

    manager_decision = (
        flow.If(lambda activation: activation.process.manager_approved)
        .Then(this.hr_approval)
        .Else(this.end)
    )

    hr_approval = (
        flow.View(
            UpdateProcessView.as_view(
                fields=['hr_approved'],
                template_name='leave/approval_form.html'
            )
        )
        .Permission('leave.can_approve_hr')
        .Next(this.end)
    )

    end = flow.End()
