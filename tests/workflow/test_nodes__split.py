from django.test import TestCase

from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.status import STATUS


class Test(TestCase):  # noqa: D101
    def test_split_with_data_source(self):
        """Test Split node with data_source creates multiple tasks."""
        process = TestDataSourceWorkflow.start.run()

        # Check that 3 tasks were created by data_source
        data_tasks = process.task_set.filter(flow_task=TestDataSourceWorkflow.data_task)
        self.assertEqual(data_tasks.count(), 3)

        # Check task data is correctly set
        task_data_list = []
        for task in data_tasks:
            task_data_list.append(task.data)
            self.assertTrue('item_id' in task.data)
        
        item_ids = [t['item_id'] for t in task_data_list]
        self.assertEqual(sorted(item_ids), [1, 2, 3])
        
        # Complete all tasks and check join works
        for task in data_tasks:
            TestDataSourceWorkflow.data_task.run(task)
        
        join_task = process.task_set.filter(flow_task=TestDataSourceWorkflow.join).first()
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.DONE)
        
        process.refresh_from_db()
        self.assertEqual(process.status, STATUS.DONE)

    def test_split_mixed(self):
        """Test Split with both regular next and data_source."""
        process = TestMixedSplitWorkflow.start.run()
        
        # Check that 1 regular task and 2 data tasks were created
        regular_tasks = process.task_set.filter(flow_task=TestMixedSplitWorkflow.regular_task)
        data_tasks = process.task_set.filter(flow_task=TestMixedSplitWorkflow.data_task)
        
        self.assertEqual(regular_tasks.count(), 1)
        self.assertEqual(data_tasks.count(), 2)


class TestDataSourceWorkflow(flow.Flow):  # noqa: D101
    start = flow.StartHandle().Next(this.split)

    split = (
        flow.Split()
        .Next(this.data_task, data_source=this.get_data_list)
    )

    data_task = flow.Function(this.process_data).Next(this.join)
    join = flow.Join().Next(this.end)
    end = flow.End()

    def get_data_list(self, activation):
        return [{'item_id': 1}, {'item_id': 2}, {'item_id': 3}]
    
    def process_data(self, activation):
        pass


class TestMixedSplitWorkflow(flow.Flow):  # noqa: D101
    start = flow.StartHandle().Next(this.split)

    split = (
        flow.Split()
        .Next(this.regular_task)
        .Next(this.data_task, data_source=this.get_two_items)
    )

    regular_task = flow.Function(this.do_something).Next(this.join)
    data_task = flow.Function(this.process_data).Next(this.join)
    join = flow.Join().Next(this.end)
    end = flow.End()

    def get_two_items(self, activation):
        return [{'name': 'A'}, {'name': 'B'}]
    
    def do_something(self, activation):
        pass
    
    def process_data(self, activation):
        pass
