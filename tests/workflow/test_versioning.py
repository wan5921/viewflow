from django.test import TestCase
from django.urls import path
from django.test import override_settings
from django.contrib.auth.models import User
from django.core.management import call_command
from io import StringIO

from viewflow import this
from viewflow.workflow import Flow, flow, STATUS
from viewflow.workflow.models import Process, Task
from viewflow.workflow.fields import get_flow_ref


class TestVersioning(TestCase):
    def test_process_created_with_default_version(self):
        process = Process.objects.create(
            flow_class=VersioningFlowV1,
        )
        self.assertEqual(process.version, 1)

    def test_process_created_with_custom_version(self):
        process = Process.objects.create(
            flow_class=VersioningFlowV2,
            version=2,
        )
        self.assertEqual(process.version, 2)

    def test_start_handle_sets_version_from_flow(self):
        process = VersioningFlowV1.start.run()
        self.assertEqual(process.version, 1)

        process = VersioningFlowV2.start.run()
        self.assertEqual(process.version, 2)

    def test_v1_and_v2_tasks_dont_conflict(self):
        process_v1 = VersioningFlowV1.start.run()
        process_v2 = VersioningFlowV2.start.run()

        self.assertEqual(process_v1.flow_class, VersioningFlowV1)
        self.assertEqual(process_v1.version, 1)

        self.assertEqual(process_v2.flow_class, VersioningFlowV2)
        self.assertEqual(process_v2.version, 2)

        self.assertNotEqual(process_v1.pk, process_v2.pk)

        v1_tasks = Task.objects.filter(process=process_v1)
        v2_tasks = Task.objects.filter(process=process_v2)

        self.assertEqual(v1_tasks.count(), 2)
        self.assertEqual(v2_tasks.count(), 2)

        v1_task_pks = set(v1_tasks.values_list("pk", flat=True))
        v2_task_pks = set(v2_tasks.values_list("pk", flat=True))
        self.assertTrue(v1_task_pks.isdisjoint(v2_task_pks))

    def test_migrate_flows_command(self):
        process = VersioningFlowV1.start.run()
        self.assertEqual(process.version, 1)
        self.assertEqual(process.flow_class, VersioningFlowV1)

        task_count_before = Task.objects.filter(process=process).count()

        out = StringIO()
        call_command(
            "migrate_flows",
            get_flow_ref(VersioningFlowV1),
            get_flow_ref(VersioningFlowV2),
            stdout=out,
        )

        process.refresh_from_db()
        self.assertEqual(process.version, 2)
        self.assertEqual(process.flow_class, VersioningFlowV2)

        task_count_after = Task.objects.filter(process=process).count()
        self.assertEqual(task_count_before, task_count_after)

    def test_migrate_flows_dry_run(self):
        process = VersioningFlowV1.start.run()
        self.assertEqual(process.version, 1)

        out = StringIO()
        call_command(
            "migrate_flows",
            get_flow_ref(VersioningFlowV1),
            get_flow_ref(VersioningFlowV2),
            dry_run=True,
            stdout=out,
        )

        process.refresh_from_db()
        self.assertEqual(process.version, 1)
        self.assertEqual(process.flow_class, VersioningFlowV1)


@override_settings(ROOT_URLCONF=__name__)
class TestVersioningFlowViewset(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="admin", password="admin")

    def test_process_list_filter_by_version(self):
        self.assertTrue(self.client.login(username="admin", password="admin"))

        VersioningFlowV1.start.run()
        VersioningFlowV2.start.run()

        response = self.client.get("/v1/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/v1/flows/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/v1/flows/?version=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 1)

        response = self.client.get("/v1/flows/?version=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 0)

        response = self.client.get("/v2/flows/?version=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 1)


class VersioningFlowV1(Flow):
    version = 1

    start = flow.StartHandle().Next(this.end)
    end = flow.End()


class VersioningFlowV2(Flow):
    version = 2

    start = flow.StartHandle().Next(this.end)
    end = flow.End()


urlpatterns = [
    path("v1/", flow.FlowViewset(VersioningFlowV1).urls),
    path("v2/", flow.FlowViewset(VersioningFlowV2).urls),
]