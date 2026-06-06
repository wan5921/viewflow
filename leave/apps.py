import os
from django.apps import AppConfig


class LeaveConfig(AppConfig):
    name = 'leave'
    path = os.path.dirname(os.path.abspath(__file__))