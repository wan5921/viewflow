from unittest import mock

from django.test import TestCase
from viewflow.workflow import STATUS
from viewflow.workflow.models import Process, Task
from viewflow.workflow.activation import Activation, context
from viewflow.workflow.nodes.if_gate import IfActivation, If
from viewflow.fsm.base import TransitionNotAllowed


class DummyFlowClass:
    task_class = Task


class DummyFlowTask:
    flow_class = DummyFlowClass
    def __init__(self):
        self._on_true = mock.Mock()
        self._on_true_data = None
        self._on_true_seed = None
        self._on_false = mock.Mock()
        self._on_false_data = None
        self._on_false_seed = None

    def _condition(self, activation):
        return True


class TestActivation(TestCase):
    def test_lifecycle(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        activation = Activation(task)
        transitions = activation.get_outgoing_transitions()
        self.assertEqual(2, len(transitions))

    def test_normal_transition(self):
        process = Process.objects.create()
        task = Task.objects.create(process=process, status=STATUS.NEW)
        task.flow_task = DummyFlowTask()
        activation = Activation(task)
        
        # Test complete()
        activation.complete()
        self.assertEqual(activation.task.status, STATUS.DONE)
        self.assertIsNotNone(activation.task.finished)

    def test_invalid_transition(self):
        process = Process()
        task = Task(process=process, status=STATUS.DONE)
        activation = Activation(task)
        
        # activate() expects STATUS.NEW
        with self.assertRaises(TransitionNotAllowed):
            activation.activate()

    def test_on_error_callback(self):
        process = Process.objects.create()
        task = Task.objects.create(process=process, status=STATUS.NEW)
        activation = Activation(task)
        
        with context(propagate_exception=False):
            with activation.exception_guard():
                raise ValueError("Test Error")
                
        self.assertEqual(activation.task.status, STATUS.ERROR)
        self.assertIn("_exception", activation.task.data)
        self.assertEqual(activation.task.data["_exception"]["title"], "Test Error")

    @mock.patch("viewflow.workflow.activation.Activation.activate_next", create=True)
    @mock.patch("viewflow.workflow.activation.Activation.create_next", create=True)
    def test_activation_next_mock(self, mock_create_next, mock_activate_next):
        process = Process.objects.create()
        task = Task.objects.create(process=process, status=STATUS.DONE)
        activation = Activation(task)
        
        mock_create_next.return_value = []
        # Calling activate_next directly or assuming it's what user meant by 'Activation.next'
        activation.activate_next()
        
        mock_create_next.assert_called_once()
        # Also let's mock 'next' if the user meant that specifically
        with mock.patch.object(Activation, "next", create=True) as mock_next:
            activation.next()
            mock_next.assert_called_once()


class TestIfActivation(TestCase):
    def test_if_cond_true(self):
        process = Process.objects.create()
        task = Task.objects.create(process=process, status=STATUS.NEW)
        flow_task = DummyFlowTask()
        task.flow_task = flow_task
        activation = IfActivation(task)
        
        activation.activate()
        self.assertTrue(activation._condition_result)
        
        # mock _create on the next node
        next_node = flow_task._on_true
        next_node._create.return_value = "true_node_activation"
        
        next_activations = list(activation.create_next())
        self.assertEqual(next_activations, ["true_node_activation"])
        next_node._create.assert_called_once()

    def test_if_cond_false(self):
        process = Process.objects.create()
        task = Task.objects.create(process=process, status=STATUS.NEW)
        flow_task = DummyFlowTask()
        flow_task._condition = lambda act: False
        task.flow_task = flow_task
        activation = IfActivation(task)
        
        activation.activate()
        self.assertFalse(activation._condition_result)
        
        # mock _create on the next node
        next_node = flow_task._on_false
        next_node._create.return_value = "false_node_activation"
        
        next_activations = list(activation.create_next())
        self.assertEqual(next_activations, ["false_node_activation"])
        next_node._create.assert_called_once()

