
from django.test import TestCase
from unittest import mock
from viewflow import this
from viewflow.workflow import flow, STATUS
from viewflow.workflow.activation import Activation
from viewflow.fsm import TransitionNotAllowed
from viewflow.workflow.models import Process, Task


class TestIfNode(TestCase):
    """测试 If 节点的各种场景"""

    def test_if_condition_true(self):
        """测试条件为 True 时的正常流转"""
        process = IfTestFlow.start.run(condition=True)
        self.assertEqual(process.status, STATUS.DONE)
        
        tasks = process.task_set.all().order_by('created')
        self.assertEqual(len(tasks), 4)  # start, if, true_task, end
        
        if_task = tasks[1]
        self.assertEqual(if_task.flow_task, IfTestFlow.check_condition)
        self.assertEqual(if_task.status, STATUS.DONE)
        
        true_task = tasks[2]
        self.assertEqual(true_task.flow_task, IfTestFlow.true_task)
        self.assertEqual(true_task.status, STATUS.DONE)

    def test_if_condition_false(self):
        """测试条件为 False 时的正常流转"""
        process = IfTestFlow.start.run(condition=False)
        self.assertEqual(process.status, STATUS.DONE)
        
        tasks = process.task_set.all().order_by('created')
        self.assertEqual(len(tasks), 4)  # start, if, false_task, end
        
        if_task = tasks[1]
        self.assertEqual(if_task.flow_task, IfTestFlow.check_condition)
        self.assertEqual(if_task.status, STATUS.DONE)
        
        false_task = tasks[2]
        self.assertEqual(false_task.flow_task, IfTestFlow.false_task)
        self.assertEqual(false_task.status, STATUS.DONE)

    @mock.patch('viewflow.workflow.activation.Activation.create_next')
    def test_mock_create_next(self, mock_create_next):
        """使用 mock 模拟 Activation.create_next 避免数据库写入"""
        mock_create_next.return_value = []
        
        process = IfTestFlow.start.run(condition=True)
        
        # 验证 create_next 被调用
        self.assertTrue(mock_create_next.called)
        self.assertGreater(mock_create_next.call_count, 0)

    def test_transition_not_allowed(self):
        """测试非法的状态转换"""
        process = IfTestFlow.start.run(condition=True)
        task = process.task_set.filter(flow_task=IfTestFlow.true_task).first()
        activation = Activation(task)
        
        # 尝试从 DONE 状态执行 activate，这应该抛出 TransitionNotAllowed
        with self.assertRaises(TransitionNotAllowed):
            activation.activate()

    def test_on_error_callback(self):
        """测试错误回调"""
        # 创建一个会在 activate 时抛出异常的流程
        process = ErrorTestFlow.start.run()
        
        task = process.task_set.filter(flow_task=ErrorTestFlow.error_task).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status, STATUS.ERROR)
        
        # 检查异常信息是否被记录
        self.assertIn('_exception', task.data)
        self.assertIn('title', task.data['_exception'])
        self.assertEqual(task.data['_exception']['title'], 'Test exception')


class IfTestProcess(Process):
    condition = None

    class Meta:
        proxy = True


class IfTestFlow(flow.Flow):
    process_class = IfTestProcess

    start = flow.StartHandle(this.start_process).Next(this.check_condition)

    check_condition = (
        flow.If(lambda activation: activation.process.condition)
        .Then(this.true_task)
        .Else(this.false_task)
    )

    true_task = flow.Function(this.on_true).Next(this.end)
    false_task = flow.Function(this.on_false).Next(this.end)

    end = flow.End()

    def start_process(self, activation, condition=True):
        activation.process.condition = condition
        return activation.process

    def on_true(self, activation):
        pass

    def on_false(self, activation):
        pass


class ErrorTestFlow(flow.Flow):
    start = flow.StartHandle().Next(this.error_task)
    error_task = flow.Function(this.raise_error).Next(this.end)
    end = flow.End()

    def raise_error(self, activation):
        raise Exception('Test exception')

