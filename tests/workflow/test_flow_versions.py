from io import StringIO

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import path

from viewflow import this
from viewflow.workflow import Flow, PROCESS, STATUS, flow
from viewflow.workflow.fields import get_flow_ref
from viewflow.workflow.flow import views
from viewflow.workflow.models import Process


class VersionedFlowProcess(Process):
    class Meta:
        proxy = True


class VersionedFlow(Flow):
    process_class = VersionedFlowProcess

    start = flow.StartHandle().Next(this.review)
    review = flow.View(views.UpdateProcessView.as_view(fields=[])).Next(this.end)
    end = flow.End()


urlpatterns = [
    path("", flow.FlowAppViewset(VersionedFlow).urls),
]


@override_settings(ROOT_URLCONF=__name__)
class TestFlowVersioning(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="user", password="user")
        cls.user.user_permissions.add(
            Permission.objects.get(codename=f"view_{VersionedFlowProcess._meta.model_name}")
        )

    def setUp(self):
        self.client.login(username="user", password="user")

    def create_review_task(self, version, *, status=STATUS.NEW, owner=None, finished=None):
        process = VersionedFlowProcess.objects.create(
            flow_class=VersionedFlow,
            version=version,
            status=PROCESS.STARTED,
            finished=finished,
        )
        return VersionedFlow.task_class.objects.create(
            process=process,
            flow_task=VersionedFlow.review,
            status=status,
            owner=owner,
            finished=finished,
        )

    def test_flow_upgrade_creates_new_cached_instance(self):
        default_flow = VersionedFlow.instance
        version_two = VersionedFlow(version=2)
        version_two_again = VersionedFlow(version=2)
        version_three = VersionedFlow.upgrade()

        self.assertEqual(default_flow.version, 1)
        self.assertEqual(version_two.version, 2)
        self.assertEqual(version_three.version, 3)
        self.assertIs(version_two, version_two_again)
        self.assertIsNot(default_flow, version_two)

    def test_queue_version_filter_keeps_tasks_separated(self):
        task_v1 = self.create_review_task(version=1)
        task_v2 = self.create_review_task(version=2)

        response = self.client.get("/queue/?version=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{task_v1.process_id}/{task_v1.pk}")
        self.assertNotContains(response, f"#{task_v2.process_id}/{task_v2.pk}")

        response = self.client.get("/queue/?version=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{task_v2.process_id}/{task_v2.pk}")
        self.assertNotContains(response, f"#{task_v1.process_id}/{task_v1.pk}")

    def test_migrate_flows_moves_active_processes_to_new_version(self):
        active_task = self.create_review_task(version=1)
        finished_task = self.create_review_task(version=1, finished=active_task.created)
        finished_task.process.status = PROCESS.DONE
        finished_task.process.save(update_fields=["status"])

        output = StringIO()
        call_command(
            "migrate_flows",
            get_flow_ref(VersionedFlow),
            "--from-version",
            "1",
            "--to-version",
            "2",
            stdout=output,
        )

        active_task.process.refresh_from_db()
        finished_task.process.refresh_from_db()

        self.assertEqual(active_task.process.version, 2)
        self.assertEqual(finished_task.process.version, 1)
        self.assertIn("Migrated 1 processes", output.getvalue())
