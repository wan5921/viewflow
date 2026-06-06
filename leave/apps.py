from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LeaveConfig(AppConfig):
    name = 'leave'
    verbose_name = _('请假审批')

    def ready(self):
        from . import flows
