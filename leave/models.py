from django.db import models
from django.utils.translation import gettext_lazy as _
from viewflow.workflow.models import Process


class LeaveRequest(Process):
    applicant = models.CharField(_("Applicant"), max_length=150)
    days = models.PositiveIntegerField(_("Days"))
    reason = models.TextField(_("Reason"))

    class Meta:
        verbose_name = _("Leave Request")
        verbose_name_plural = _("Leave Requests")

    def __str__(self):
        return f"{self.applicant} - {self.days} day(s)"