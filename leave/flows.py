from django.utils.translation import gettext_lazy as _

from viewflow import this
from viewflow.workflow import Flow, flow
from viewflow.workflow.flow import views

from .models import LeaveRequest


class LeaveFlow(Flow):
    process_class = LeaveRequest
    process_title = _('Leave request')
    process_description = _('Employee leave request approval flow')
    process_summary_template = _('{{ process.applicant }} requested {{ process.days }} day(s)')
    process_result_template = _('{{ process.applicant }} leave request completed')

    start = (
        flow.Start(views.CreateProcessView.as_view(fields=['applicant', 'days', 'reason']))
        .Annotation(
            title=_('Submit leave request'),
            description=_('Fill in the leave request form'),
            summary_template=_('{{ process.applicant }} is preparing a leave request'),
        )
        .Permission(auto_create=True)
        .Next(this.manager_approval)
    )

    manager_approval = (
        flow.View(views.UpdateProcessView.as_view(fields=[]))
        .Annotation(
            title=_('Manager approval'),
            description=_('Manager reviews the leave request'),
            summary_template=_('Waiting for manager approval'),
            result_template=_('Manager approval completed'),
        )
        .Permission(auto_create=True)
        .Next(this.hr_approval)
    )

    hr_approval = (
        flow.View(views.UpdateProcessView.as_view(fields=[]))
        .Annotation(
            title=_('HR approval'),
            description=_('HR reviews the leave request'),
            summary_template=_('Waiting for HR approval'),
            result_template=_('HR approval completed'),
        )
        .Permission(auto_create=True)
        .Next(this.end)
    )

    end = flow.End()
