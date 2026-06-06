from django.test import TestCase, override_settings
from django.urls import path
from django.contrib.auth.models import User
from viewflow import this
from viewflow.workflow import flow, Flow
from viewflow.workflow.models import Process, Task

class TestFlowV1(Flow):
    process_title = "Test Flow"
    version = 1

    start = flow.StartHandle().Next(this.end)
    end = flow.End()


class TestFlowV2(Flow):
    process_title = "Test Flow"
    version = 2

    start = flow.StartHandle().Next(this.end)
    end = flow.End()

urlpatterns = [
    path('flow1/', flow.FlowAppViewset(TestFlowV1).urls),
    path('flow2/', flow.FlowAppViewset(TestFlowV2).urls),
]

@override_settings(ROOT_URLCONF=__name__)
class TestFlowVersionConflict(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@admin.com", "admin")
        self.client.login(username="admin", password="admin")

    def test_version_isolation(self):
        # Create a process with version 1
        process_v1 = TestFlowV1.start.run()
        self.assertEqual(process_v1.version, 1)

        # Create a process with version 2
        process_v2 = TestFlowV2.start.run()
        self.assertEqual(process_v2.version, 2)

        # Ensure that filtering works
        v1_count = Process.objects.filter(version=1).count()
        v2_count = Process.objects.filter(version=2).count()
        
        self.assertEqual(v1_count, 1)
        self.assertEqual(v2_count, 1)

        # Check tasks are isolated
        v1_tasks = Task.objects.filter(process__version=1)
        v2_tasks = Task.objects.filter(process__version=2)

        self.assertEqual(v1_tasks.count(), 2) # Start, End
        self.assertEqual(v2_tasks.count(), 2)

    def test_flow_initialization_with_version(self):
        class DynamicFlow(Flow):
            start = flow.StartHandle().Next(this.end)
            end = flow.End()

        flow_instance = DynamicFlow(version=3)
        self.assertEqual(flow_instance.version, 3)

        process = flow_instance.start.run()
        self.assertEqual(process.version, 3)

    def test_api_viewset_isolation(self):
        TestFlowV1.start.run()
        TestFlowV2.start.run()
        
        # Test flow1 inbox/queue
        response1 = self.client.get("/flow1/flows/")
        self.assertEqual(200, response1.status_code)
        
        # Test flow2 inbox/queue
        response2 = self.client.get("/flow2/flows/")
        self.assertEqual(200, response2.status_code)
        
        # Filter by version using ?version=
        response = self.client.get("/flow1/flows/?version=1")
        self.assertEqual(200, response.status_code)
