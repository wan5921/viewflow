from django.test import TestCase

from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.status import STATUS


class TestSplitWorkflow(flow.Flow):  # noqa: D101
    start = flow.StartHandle().Next(this.split)

    split = (
        flow.Split()
        .Next(
            this.worker,
            data_source=lambda act: [{"item": 1}, {"item": 2}, {"item": 3}]
        )
    )

    worker = flow.Handle(this.handler).Next(this.join)

    join = flow.Join().Next(this.end)

    end = flow.End()

    def handler(self, activation):
        pass


class Test(TestCase):  # noqa: D101
    def test_split_data_source(self):
        process = TestSplitWorkflow.start.run()
        
        worker_tasks = process.task_set.filter(flow_task=TestSplitWorkflow.worker)
        self.assertEqual(worker_tasks.count(), 3)
        
        # Verify that data was correctly passed
        data_items = set(task.data.get("item") for task in worker_tasks)
        self.assertEqual(data_items, {1, 2, 3})
