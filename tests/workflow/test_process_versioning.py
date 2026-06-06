from django.urls import path, reverse
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Permission

from viewflow import this
from viewflow.workflow import Flow, flow
from viewflow.workflow.models import Process, Task
from viewflow.workflow.status import STATUS


@override_settings(ROOT_URLCONF=__name__)
class TestProcessVersioning(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="admin", password="admin")
        cls.user = User.objects.create_user(username="user", password="user")
        cls.user.user_permissions.add(
            Permission.objects.get(codename="view_versionedprocess")
        )

    def test_process_created_with_default_version(self):
        process = VersionedFlow.start.run()

        self.assertEqual(process.version, 1)
        self.assertEqual(process.flow_class, VersionedFlow)

    def test_process_created_with_custom_version(self):
        VersionedFlowV2 = VersionedFlow.upgrade_version(2)

        process = VersionedFlowV2.start.run()

        self.assertEqual(process.version, 2)
        self.assertEqual(process.flow_class, VersionedFlowV2)

    def test_old_version_processes_not_affected_by_upgrade(self):
        old_process = VersionedFlow.start.run()
        self.assertEqual(old_process.version, 1)

        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        new_process = VersionedFlowV2.start.run()
        self.assertEqual(new_process.version, 2)

        old_process.refresh_from_db()
        self.assertEqual(old_process.version, 1)

    def test_version_filter_on_process_list(self):
        v1_process = VersionedFlow.start.run()
        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        v2_process = VersionedFlowV2.start.run()

        v1_processes = Process.objects.filter(
            flow_class=VersionedFlow,
            version=1,
        )
        v2_processes = Process.objects.filter(
            flow_class=VersionedFlow,
            version=2,
        )

        self.assertIn(v1_process, v1_processes)
        self.assertNotIn(v2_process, v1_processes)

        self.assertIn(v2_process, v2_processes)
        self.assertNotIn(v1_process, v2_processes)

    def test_version_filter_on_task_list(self):
        v1_process = VersionedFlow.start.run()
        v1_task = v1_process.task_set.first()

        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        v2_process = VersionedFlowV2.start.run()
        v2_task = v2_process.task_set.first()

        v1_tasks = Task.objects.filter(process__version=1)
        v2_tasks = Task.objects.filter(process__version=2)

        self.assertIn(v1_task, v1_tasks)
        self.assertNotIn(v2_task, v1_tasks)

        self.assertIn(v2_task, v2_tasks)
        self.assertNotIn(v1_task, v2_tasks)

    def test_tasks_from_different_versions_not_conflict(self):
        v1_process = VersionedFlow.start.run()
        v1_tasks = list(v1_process.task_set.all())

        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        v2_process = VersionedFlowV2.start.run()
        v2_tasks = list(v2_process.task_set.all())

        v1_task_ids = {task.pk for task in v1_tasks}
        v2_task_ids = {task.pk for task in v2_tasks}

        self.assertEqual(len(v1_task_ids & v2_task_ids), 0)

    def test_flow_version_attribute(self):
        self.assertEqual(VersionedFlow.version, 1)

        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        self.assertEqual(VersionedFlowV2.version, 2)

    def test_flow_version_auto_increment(self):
        VersionedFlow.version = 1

        VersionedFlowV2 = VersionedFlow.upgrade_version()
        self.assertEqual(VersionedFlowV2.version, 2)

        VersionedFlowV3 = VersionedFlow.upgrade_version()
        self.assertEqual(VersionedFlowV3.version, 3)


@override_settings(ROOT_URLCONF=__name__)
class TestVersionedFlowViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="admin", password="admin")
        cls.user = User.objects.create_user(username="user", password="user")
        cls.user.user_permissions.add(
            Permission.objects.get(codename="view_versionedprocess")
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_process_list_version_filter(self):
        v1_process = VersionedFlow.start.run()
        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        v2_process = VersionedFlowV2.start.run()

        response = self.client.get("/versioned/flows/")
        self.assertEqual(response.status_code, 200)

        response_v1 = self.client.get("/versioned/flows/?version=1")
        self.assertEqual(response_v1.status_code, 200)

        response_v2 = self.client.get("/versioned/flows/?version=2")
        self.assertEqual(response_v2.status_code, 200)

    def test_task_list_version_filter(self):
        VersionedFlow.start.run()
        VersionedFlowV2 = VersionedFlow.upgrade_version(2)
        VersionedFlowV2.start.run()

        response = self.client.get("/versioned/tasks/")
        self.assertEqual(response.status_code, 200)

        response_v1 = self.client.get("/versioned/tasks/?version=1")
        self.assertEqual(response_v1.status_code, 200)

        response_v2 = self.client.get("/versioned/tasks/?version=2")
        self.assertEqual(response_v2.status_code, 200)


@override_settings(ROOT_URLCONF=__name__)
class TestMigrateFlowsCommand(TestCase):
    def test_migrate_flows_dry_run(self):
        from django.core.management import call_command
        from io import StringIO

        v1_process = VersionedFlow.start.run()
        self.assertEqual(v1_process.version, 1)

        out = StringIO()
        call_command(
            "migrate_flows",
            "tests/workflow.VersionedFlow",
            "--from-version=1",
            "--to-version=2",
            "--dry-run",
            stdout=out,
        )

        v1_process.refresh_from_db()
        self.assertEqual(v1_process.version, 1)

        self.assertIn("DRY RUN", out.getvalue())

    def test_migrate_flows_actual_migration(self):
        from django.core.management import call_command

        v1_process = VersionedFlow.start.run()
        self.assertEqual(v1_process.version, 1)

        call_command(
            "migrate_flows",
            "tests/workflow.VersionedFlow",
            "--from-version=1",
            "--to-version=2",
        )

        v1_process.refresh_from_db()
        self.assertEqual(v1_process.version, 2)

    def test_migrate_flows_specific_pks(self):
        from django.core.management import call_command

        v1_process1 = VersionedFlow.start.run()
        v1_process2 = VersionedFlow.start.run()

        call_command(
            "migrate_flows",
            "tests/workflow.VersionedFlow",
            "--from-version=1",
            "--to-version=2",
            "--process-pks",
            str(v1_process1.pk),
        )

        v1_process1.refresh_from_db()
        v1_process2.refresh_from_db()

        self.assertEqual(v1_process1.version, 2)
        self.assertEqual(v1_process2.version, 1)


class VersionedProcess(Process):
    class Meta:
        proxy = True


class VersionedFlow(Flow):
    process_class = VersionedProcess

    start = flow.StartHandle().Next(this.end)
    end = flow.End()


urlpatterns = [
    path("versioned/", flow.FlowAppViewset(VersionedFlow).urls),
]
