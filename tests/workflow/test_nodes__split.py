from django.test import TestCase

from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.status import STATUS, PROCESS


class Test(TestCase):
    def test_split_creates_all_parallel_tasks(self):
        process = TestSplitWorkflow.start.run()

        task_a = process.task_set.filter(flow_task=TestSplitWorkflow.branch_a).first()
        task_b = process.task_set.filter(flow_task=TestSplitWorkflow.branch_b).first()
        task_c = process.task_set.filter(flow_task=TestSplitWorkflow.branch_c).first()

        self.assertIsNotNone(task_a)
        self.assertIsNotNone(task_b)
        self.assertIsNotNone(task_c)

        self.assertEqual(process.task_set.count(), 5)

    def test_join_waits_for_all_async_tasks(self):
        process = TestSplitAsyncWorkflow.start.run()

        task_a = process.task_set.filter(
            flow_task=TestSplitAsyncWorkflow.branch_a
        ).first()
        task_b = process.task_set.filter(
            flow_task=TestSplitAsyncWorkflow.branch_b
        ).first()
        task_c = process.task_set.filter(
            flow_task=TestSplitAsyncWorkflow.branch_c
        ).first()

        join_task = process.task_set.filter(
            flow_task=TestSplitAsyncWorkflow.join
        ).first()
        self.assertIsNotNone(join_task)
        self.assertEqual(join_task.status, STATUS.STARTED)

        TestSplitAsyncWorkflow.branch_a.run(task_a)
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.STARTED)

        TestSplitAsyncWorkflow.branch_b.run(task_b)
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.STARTED)

        TestSplitAsyncWorkflow.branch_c.run(task_c)
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.DONE)

        process.refresh_from_db()
        self.assertEqual(process.status, PROCESS.DONE)
        self.assertEqual(process.task_set.count(), 7)

    def test_split_condition_skip_branch(self):
        process = TestSplitConditionWorkflow.start.run()

        task_a = process.task_set.filter(
            flow_task=TestSplitConditionWorkflow.branch_a
        ).first()
        task_b = process.task_set.filter(
            flow_task=TestSplitConditionWorkflow.branch_b
        ).first()

        self.assertIsNotNone(task_a)
        self.assertIsNone(task_b)

        self.assertEqual(process.task_set.count(), 4)


class TestSplitWorkflow(flow.Flow):
    start = flow.StartHandle().Next(this.split)

    split = (
        flow.Split()
        .Next(this.branch_a)
        .Next(this.branch_b)
        .Next(this.branch_c)
    )

    branch_a = flow.Function(this.func).Next(this.end)
    branch_b = flow.Function(this.func).Next(this.end)
    branch_c = flow.Function(this.func).Next(this.end)

    end = flow.End()

    def func(self, activation):
        pass


class TestSplitAsyncWorkflow(flow.Flow):
    start = flow.StartHandle().Next(this.split)

    split = (
        flow.Split()
        .Next(this.branch_a)
        .Next(this.branch_b)
        .Next(this.branch_c)
    )

    branch_a = flow.Handle(this.handler).Next(this.join)
    branch_b = flow.Handle(this.handler).Next(this.join)
    branch_c = flow.Handle(this.handler).Next(this.join)

    join = flow.Join().Next(this.end)

    end = flow.End()

    def handler(self, activation):
        pass


class TestSplitConditionWorkflow(flow.Flow):
    start = flow.StartHandle().Next(this.split)

    split = flow.Split().Next(this.branch_a, case=lambda act: True).Next(
        this.branch_b, case=lambda act: False
    )

    branch_a = flow.Function(this.func).Next(this.end)
    branch_b = flow.Function(this.func).Next(this.end)

    end = flow.End()

    def func(self, activation):
        pass