from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from viewflow.workflow.models import Process


class LeaveRequest(Process):
    """请假申请模型"""
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("申请人"),
        related_name="leave_requests"
    )
    days = models.IntegerField(
        _("天数"),
        default=1
    )
    reason = models.TextField(
        _("原因"),
        blank=True
    )
    manager_approved = models.BooleanField(
        _("经理批准"),
        default=False
    )
    hr_approved = models.BooleanField(
        _("HR批准"),
        default=False
    )

    class Meta:
        verbose_name = _("请假申请")
        verbose_name_plural = _("请假申请列表")

    def __str__(self):
        return f"{self.applicant} - {self.days}天"
