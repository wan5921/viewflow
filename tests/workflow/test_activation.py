from types import SimpleNamespace
from unittest import mock

from django.db import transaction
from django.test import TestCase

from viewflow.fsm import TransitionNotAllowed
from viewflow.workflow import PROCESS, STATUS
from viewflow.workflow.activation import Activation
from viewflow.workflow.models import Process, Task
from viewflow.workflow.nodes.if_gate import IfActivation
from viewflow.workflow.signals import task_failed


class HashableNamespace(SimpleNamespace):
    __hash__ = object.__hash__


class DummyActivation(Activation):
    @Activation.status.super()
    def activate(self):
        self.task.started = "started"

    @Activation.status.transition(source=STATUS.DONE)
    def create_next(self):
        yield from getattr(self, "_next_activations", [])


class ErrorActivation(Activation):
    @Activation.status.super()
    def activate(self):
        with self.exception_guard():
            raise RuntimeError("boom")

    @Activation.status.transition(source=STATUS.DONE)
    def create_next(self):
        yield from ()


class Test(TestCase):  # noqa: D101
    def test_lifecycle(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        activation = Activation(task)
        transitions = activation.get_outgoing_transitions()
        self.assertEqual(2, len(transitions))

    def test_activation_normal_flow_uses_mocked_activate_next(self):
        activation = DummyActivation(self._make_task())
        next_activation = DummyActivation(self._make_task())
        activation._next_activations = [next_activation]

        with transaction.atomic():
            activation.complete()
            with mock.patch.object(DummyActivation, "_activate_next") as activate_next:
                activation.activate_next()

        activate_next.assert_called_once_with({next_activation})
        self.assertEqual(activation.task.status, STATUS.DONE)
        activation.task.save.assert_called_once_with()

    def test_activation_illegal_transition_raises_transition_not_allowed(self):
        activation = DummyActivation(self._make_task())

        with self.assertRaises(TransitionNotAllowed):
            activation.activate_next()

    def test_activation_exception_guard_triggers_on_error_callback(self):
        task = self._make_task()
        activation = ErrorActivation(task)
        on_error = mock.Mock()

        def receiver(sender, **kwargs):
            on_error(sender=sender, **kwargs)

        task_failed.connect(receiver, weak=False)
        try:
            activation.activate()
        finally:
            task_failed.disconnect(receiver)

        self.assertEqual(task.status, STATUS.ERROR)
        self.assertIsNotNone(task.finished)
        self.assertIn("boom", task.data["_exception"]["title"])
        task.save.assert_called_once_with()
        on_error.assert_called_once()
        self.assertIs(on_error.call_args.kwargs["task"], task)

    def test_if_activation_true_branch(self):
        true_node = mock.Mock()
        true_node._create = mock.Mock(return_value="true-activation")
        false_node = mock.Mock()
        false_node._create = mock.Mock(return_value="false-activation")
        flow_task = self._make_if_flow_task(
            condition=lambda activation: True,
            true_node=true_node,
            false_node=false_node,
        )
        activation = IfActivation(self._make_task(flow_task=flow_task))

        activation.activate()
        with transaction.atomic():
            activation.complete()
            next_activations = list(activation.create_next())

        self.assertEqual(["true-activation"], next_activations)
        true_node._create.assert_called_once_with(
            activation,
            activation.task.token,
            data={"branch": True},
            seed="seed-true",
        )
        false_node._create.assert_not_called()

    def test_if_activation_false_branch(self):
        true_node = mock.Mock()
        true_node._create = mock.Mock(return_value="true-activation")
        false_node = mock.Mock()
        false_node._create = mock.Mock(return_value="false-activation")
        flow_task = self._make_if_flow_task(
            condition=lambda activation: False,
            true_node=true_node,
            false_node=false_node,
        )
        activation = IfActivation(self._make_task(flow_task=flow_task))

        activation.activate()
        with transaction.atomic():
            activation.complete()
            next_activations = list(activation.create_next())

        self.assertEqual(["false-activation"], next_activations)
        false_node._create.assert_called_once_with(
            activation,
            activation.task.token,
            data={"branch": False},
            seed="seed-false",
        )
        true_node._create.assert_not_called()

    def _make_task(self, status=STATUS.NEW, flow_task=None):
        process = HashableNamespace(status=PROCESS.NEW)
        process.coerced = process

        if flow_task is None:
            flow_class = HashableNamespace(
                instance=HashableNamespace(has_manage_permission=lambda user: True)
            )
            flow_task = HashableNamespace(flow_class=flow_class)

        return HashableNamespace(
            process=process,
            flow_task=flow_task,
            status=status,
            data={},
            token="start",
            started=None,
            finished=None,
            seed=None,
            artifact=None,
            save=mock.Mock(),
        )

    def _make_if_flow_task(self, condition, true_node, false_node):
        flow_class = HashableNamespace(
            instance=HashableNamespace(has_manage_permission=lambda user: True)
        )
        return HashableNamespace(
            flow_class=flow_class,
            _condition=condition,
            _on_true=true_node,
            _on_true_data=lambda activation: {"branch": True},
            _on_true_seed=lambda activation: "seed-true",
            _on_false=false_node,
            _on_false_data=lambda activation: {"branch": False},
            _on_false_seed=lambda activation: "seed-false",
        )
