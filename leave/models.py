from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from viewflow.workflow.models import Process


class LeaveRequest(Process):
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        verbose_name=_("Applicant"),
    )
    days = models.PositiveIntegerField(_("Days"))
    reason = models.TextField(_("Reason"))

    class Meta:
        verbose_name = _("Leave request")
        verbose_name_plural = _("Leave requests")
