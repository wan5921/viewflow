from unittest import mock
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import TestCase, override_settings

from viewflow.fsm import TransitionNotAllowed
from viewflow.workflow import STATUS, PROCESS
from viewflow.workflow.activation import (
    Activation,
    has_manage_permission,
    leading_tasks_canceled,
    parent_tasks_completed,
    process_not_cancelled,
)
from viewflow.workflow.nodes.if_gate import IfActivation, If
from viewflow.workflow.token import Token


class _TestActivation(Activation):
    """Concrete activation for testing the base Activation class."""

    @Activation.status.transition(source=STATUS.NEW)
    def activate(self):
        pass

    @Activation.status.transition(source=STATUS.DONE)
    def create_next(self):
        return []


def _make_task(status=STATUS.NEW, process=None, flow_task=None, token="start"):
    """Create a mock Task object."""
    task = MagicMock()
    task.status = status
    task.process = process or MagicMock()
    task.flow_task = flow_task or MagicMock()
    task.token = Token(token)
    task.previous = MagicMock()
    task.leading = MagicMock()
    task.owner = None
    task.owner_permission = None
    task.owner_permission_obj = None
    task.data = {}
    task.seed = None
    task.artifact = None
    task.started = None
    task.finished = None
    task.created = None
    task.assigned = None
    return task


def _make_process(status=PROCESS.NEW, flow_class=None):
    """Create a mock Process object."""
    process = MagicMock()
    process.status = status
    process.flow_class = flow_class
    process.pk = 1
    process.finished = None
    process.coerced = process
    return process


def _make_flow_class():
    """Create a mock flow class."""
    fc = MagicMock()
    fc.process_class = MagicMock()
    fc.task_class = MagicMock()
    fc.instance = MagicMock()
    fc.instance.has_manage_permission = MagicMock(return_value=True)
    fc.lock = MagicMock()
    fc.lock.return_value = MagicMock()
    return fc


def _make_flow_task(flow_class=None):
    """Create a mock flow task."""
    ft = MagicMock()
    ft.flow_class = flow_class or _make_flow_class()
    return ft


class TestActivationTransitions(TestCase):
    """Test normal and illegal transitions of the Activation state machine."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = _make_flow_task(self.flow_class)
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        self.activation = _TestActivation(self.task)

    # --- Normal transitions ---

    def test_activate_can_proceed_when_new(self):
        self.assertTrue(self.activation.activate.can_proceed())

    def test_activate_can_proceed(self):
        self.activation.activate()
        self.assertEqual(self.task.status, STATUS.NEW)

    def test_complete_can_proceed_when_new(self):
        self.assertTrue(self.activation.complete.can_proceed())

    def test_complete_transitions_to_done(self):
        self.activation.complete()
        self.assertEqual(self.task.status, STATUS.DONE)

    def test_create_next_can_proceed_when_done(self):
        self.activation.complete()
        self.assertTrue(self.activation.create_next.can_proceed())

    def test_activate_next_can_proceed_when_done(self):
        self.activation.complete()
        self.assertTrue(self.activation.activate_next.can_proceed())

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    def test_activate_next_with_no_next_tasks(self):
        self.activation.complete()
        self.activation.activate_next()

    def test_undo_can_proceed_when_done(self):
        self.activation.complete()
        self.assertTrue(self.activation.undo.can_proceed())

    def test_undo_transitions_to_canceled(self):
        self.activation.complete()
        self.activation.undo()
        self.assertEqual(self.task.status, STATUS.CANCELED)

    def test_revive_can_proceed_when_canceled(self):
        self.task.status = STATUS.CANCELED
        self.assertTrue(self.activation.revive.can_proceed())

    def test_revive_can_proceed_when_error(self):
        self.task.status = STATUS.ERROR
        self.assertTrue(self.activation.revive.can_proceed())

    def test_get_outgoing_transitions_new(self):
        transitions = self.activation.get_outgoing_transitions()
        self.assertEqual(len(transitions), 2)

    def test_get_outgoing_transitions_done(self):
        self.activation.complete()
        transitions = self.activation.get_outgoing_transitions()
        self.assertEqual(len(transitions), 3)

    def test_get_outgoing_transitions_canceled(self):
        self.task.status = STATUS.CANCELED
        transitions = self.activation.get_outgoing_transitions()
        self.assertEqual(len(transitions), 1)

    # --- Illegal transitions (TransitionNotAllowed) ---

    def test_complete_not_allowed_when_done(self):
        self.activation.complete()
        with self.assertRaises(TransitionNotAllowed):
            self.activation.complete()

    def test_activate_not_allowed_when_done(self):
        self.activation.complete()
        with self.assertRaises(TransitionNotAllowed):
            self.activation.activate()

    def test_activate_next_not_allowed_when_new(self):
        with self.assertRaises(TransitionNotAllowed):
            self.activation.activate_next()

    def test_create_next_not_allowed_when_new(self):
        with self.assertRaises(TransitionNotAllowed):
            self.activation.create_next()

    def test_undo_not_allowed_when_new(self):
        with self.assertRaises(TransitionNotAllowed):
            self.activation.undo()

    def test_revive_not_allowed_when_new(self):
        with self.assertRaises(TransitionNotAllowed):
            self.activation.revive()

    def test_revive_not_allowed_when_done(self):
        self.activation.complete()
        with self.assertRaises(TransitionNotAllowed):
            self.activation.revive()

    # --- Transition conditions ---

    def test_undo_fails_when_leading_tasks_not_canceled(self):
        self.activation.complete()
        self.activation.task.leading.exclude.return_value.exclude.return_value.count.return_value = 1
        with self.assertRaises(TransitionNotAllowed):
            self.activation.undo()

    def test_undo_succeeds_when_leading_tasks_canceled(self):
        self.activation.complete()
        self.activation.task.leading.exclude.return_value.exclude.return_value.count.return_value = 0
        self.activation.undo()
        self.assertEqual(self.task.status, STATUS.CANCELED)


class TestActivationExceptionGuard(TestCase):
    """Test error handling / exception_guard (on_error callback)."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = _make_flow_task(self.flow_class)
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        self.activation = _TestActivation(self.task)

    def test_exception_guard_catches_exception(self):
        with mock.patch(
            "viewflow.workflow.activation.context.propagate_exception", False
        ):
            with mock.patch(
                "viewflow.workflow.activation.task_failed.send"
            ) as mock_send:
                guard = self.activation.exception_guard()
                with guard:
                    raise ValueError("test error")
                self.assertEqual(self.task.status, STATUS.ERROR)
                self.assertTrue(mock_send.called)

    def test_exception_guard_propagates_when_enabled(self):
        with mock.patch(
            "viewflow.workflow.activation.context.propagate_exception", True
        ):
            with mock.patch(
                "viewflow.workflow.activation.task_failed.send"
            ) as mock_send:
                guard = self.activation.exception_guard()
                with self.assertRaises(ValueError):
                    with guard:
                        raise ValueError("test error")
                self.assertFalse(mock_send.called)

    def test_exception_guard_stores_exception_data(self):
        with mock.patch(
            "viewflow.workflow.activation.context.propagate_exception", False
        ):
            with mock.patch(
                "viewflow.workflow.activation.task_failed.send"
            ) as mock_send:
                guard = self.activation.exception_guard()
                with guard:
                    raise ValueError("test error")
                self.assertIn("_exception", self.task.data)
                self.assertEqual(
                    self.task.data["_exception"]["title"], "test error"
                )

    def test_on_error_callback_via_signal(self):
        with mock.patch(
            "viewflow.workflow.activation.context.propagate_exception", False
        ):
            with mock.patch(
                "viewflow.workflow.activation.task_failed.send"
            ) as mock_send:
                guard = self.activation.exception_guard()
                with guard:
                    raise RuntimeError("on_error test")
                self.assertEqual(self.task.status, STATUS.ERROR)
                mock_send.assert_called_once()


class TestActivationWithMockPatch(TestCase):
    """Test Activation using mock.patch to avoid database writes."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = _make_flow_task(self.flow_class)
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        self.activation = _TestActivation(self.task)

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    @patch("viewflow.workflow.activation.task_finished.send")
    def test_complete_with_mocked_atomic(self, mock_send):
        self.activation.complete()
        self.assertEqual(self.task.status, STATUS.DONE)

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    def test_activate_next_with_mocked_create_next(self):
        self.activation.complete()
        with patch.object(
            _TestActivation, "create_next", return_value=[]
        ) as mock_create_next:
            self.activation.activate_next()
            self.assertTrue(mock_create_next.called)

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    def test_activate_next_with_mocked_chain(self):
        self.activation.complete()
        mock_next_activation = MagicMock()
        mock_next_activation.type = "node"
        mock_next_activation.activate.can_proceed.return_value = True
        mock_next_activation.complete.can_proceed.return_value = True
        mock_next_activation.create_next.can_proceed.return_value = False

        with patch.object(
            _TestActivation, "create_next", return_value=[mock_next_activation]
        ):
            self.activation.activate_next()
            mock_next_activation.activate.assert_called_once()
            mock_next_activation.complete.assert_called_once()

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    def test_activate_next_with_join_activation(self):
        self.activation.complete()
        mock_join_activation = MagicMock()
        mock_join_activation.type = "join"
        mock_join_activation.activate.can_proceed.return_value = True
        mock_join_activation.complete.can_proceed.return_value = True
        mock_join_activation.create_next.can_proceed.return_value = False

        with patch.object(
            _TestActivation, "create_next", return_value=[mock_join_activation]
        ):
            self.activation.activate_next()
            mock_join_activation.activate.assert_called_once()
            mock_join_activation.complete.assert_called_once()

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    def test_undo_with_mocked_save(self):
        self.activation.complete()
        self.activation.task.leading.exclude.return_value.exclude.return_value.count.return_value = 0
        self.activation.undo()
        self.assertEqual(self.task.status, STATUS.CANCELED)

    @patch("viewflow.workflow.activation.connection.in_atomic_block", True)
    @patch("viewflow.workflow.activation.task_finished.send")
    def test_complete_uses_mock_not_real_db(self, mock_send):
        self.activation.complete()
        self.task.save.assert_called_once()
        self.assertEqual(self.task.status, STATUS.DONE)


class TestHelperFunctions(TestCase):
    """Test helper functions used in transition conditions."""

    def test_parent_tasks_completed_all_done(self):
        task = MagicMock()
        task.previous.values.return_value = [
            {"status": STATUS.DONE},
            {"status": STATUS.DONE},
        ]
        self.assertTrue(parent_tasks_completed(MagicMock(task=task)))

    def test_parent_tasks_completed_not_all_done(self):
        task = MagicMock()
        task.previous.values.return_value = [
            {"status": STATUS.DONE},
            {"status": STATUS.NEW},
        ]
        self.assertFalse(parent_tasks_completed(MagicMock(task=task)))

    def test_leading_tasks_canceled_true(self):
        activation = MagicMock()
        activation.task.leading.exclude.return_value.exclude.return_value.count.return_value = 0
        self.assertTrue(leading_tasks_canceled(activation))

    def test_leading_tasks_canceled_false(self):
        activation = MagicMock()
        activation.task.leading.exclude.return_value.exclude.return_value.count.return_value = 3
        self.assertFalse(leading_tasks_canceled(activation))

    def test_process_not_cancelled_true(self):
        activation = MagicMock()
        activation.process.status = PROCESS.NEW
        self.assertTrue(process_not_cancelled(activation))

    def test_process_not_cancelled_false(self):
        activation = MagicMock()
        activation.process.status = PROCESS.CANCELED
        self.assertFalse(process_not_cancelled(activation))

    def test_has_manage_permission_true(self):
        activation = MagicMock()
        activation.flow_class.instance.has_manage_permission.return_value = True
        self.assertTrue(has_manage_permission(activation, MagicMock()))

    def test_has_manage_permission_false(self):
        activation = MagicMock()
        activation.flow_class.instance.has_manage_permission.return_value = False
        self.assertFalse(has_manage_permission(activation, MagicMock()))


class TestIfActivation(TestCase):
    """Test IfActivation conditional branches (True/False)."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = MagicMock()
        self.flow_task.flow_class = self.flow_class
        self.flow_task._condition = MagicMock()
        self.flow_task._on_true = MagicMock()
        self.flow_task._on_false = MagicMock()
        self.flow_task._on_true_data = None
        self.flow_task._on_false_data = None
        self.flow_task._on_true_seed = None
        self.flow_task._on_false_seed = None
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        self.activation = IfActivation(self.task)

    # --- if_cond: True branch ---

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_activate_condition_true(self, mock_atomic):
        self.flow_task._condition.return_value = True
        self.activation.activate()
        self.assertTrue(self.activation._condition_result)

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_condition_true(self, mock_atomic):
        self.activation._condition_result = True
        self.flow_task._on_true._create = MagicMock()
        self.flow_task._on_false._create = MagicMock()

        result = list(self.activation.create_next())
        self.assertEqual(len(result), 1)
        self.flow_task._on_true._create.assert_called_once()
        self.flow_task._on_false._create.assert_not_called()

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_condition_true_no_next_node(self, mock_atomic):
        self.activation._condition_result = True
        self.flow_task._on_true = None
        self.flow_task._on_false._create = MagicMock()

        result = list(self.activation.create_next())
        self.assertEqual(len(result), 0)

    # --- if_cond: False branch ---

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_activate_condition_false(self, mock_atomic):
        self.flow_task._condition.return_value = False
        self.activation.activate()
        self.assertFalse(self.activation._condition_result)

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_condition_false(self, mock_atomic):
        self.activation._condition_result = False
        self.flow_task._on_true._create = MagicMock()
        self.flow_task._on_false._create = MagicMock()

        result = list(self.activation.create_next())
        self.assertEqual(len(result), 1)
        self.flow_task._on_false._create.assert_called_once()
        self.flow_task._on_true._create.assert_not_called()

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_condition_false_no_next_node(self, mock_atomic):
        self.activation._condition_result = False
        self.flow_task._on_false = None
        self.flow_task._on_true._create = MagicMock()

        result = list(self.activation.create_next())
        self.assertEqual(len(result), 0)

    # --- Illegal transitions for IfActivation ---

    def test_activate_not_allowed_when_not_new(self):
        self.task.status = STATUS.DONE
        with self.assertRaises(TransitionNotAllowed):
            self.activation.activate()

    def test_create_next_not_allowed_when_not_done(self):
        with self.assertRaises(TransitionNotAllowed):
            list(self.activation.create_next())

    # --- IfActivation cancel transition ---

    def test_cancel_can_proceed_when_error(self):
        self.task.status = STATUS.ERROR
        self.assertTrue(self.activation.cancel.can_proceed())

    def test_cancel_transitions_to_canceled(self):
        self.task.status = STATUS.ERROR
        self.activation.cancel()
        self.assertEqual(self.task.status, STATUS.CANCELED)

    def test_cancel_not_allowed_when_new(self):
        with self.assertRaises(TransitionNotAllowed):
            self.activation.cancel()

    # --- IfActivation with data sources ---

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_with_data_sources_true(self, mock_atomic):
        self.activation._condition_result = True
        self.flow_task._on_true_data = MagicMock(return_value={"key": "val"})
        self.flow_task._on_true._create = MagicMock()

        list(self.activation.create_next())
        self.flow_task._on_true_data.assert_called_once_with(self.activation)

    @patch("viewflow.workflow.nodes.if_gate.transaction.atomic")
    def test_create_next_with_seed_sources_false(self, mock_atomic):
        self.activation._condition_result = False
        self.flow_task._on_false_seed = MagicMock(return_value="seed_val")
        self.flow_task._on_false._create = MagicMock()

        list(self.activation.create_next())
        self.flow_task._on_false_seed.assert_called_once_with(self.activation)


class TestActivationEqualityHashing(TestCase):
    """Test Activation __eq__ and __hash__ methods."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = _make_flow_task(self.flow_class)
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )

    def test_equal_same_task(self):
        a1 = _TestActivation(self.task)
        a2 = _TestActivation(self.task)
        self.assertEqual(a1, a2)

    def test_not_equal_different_task(self):
        a1 = _TestActivation(self.task)
        other_task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        a2 = _TestActivation(other_task)
        self.assertNotEqual(a1, a2)

    def test_not_equal_different_type(self):
        a1 = _TestActivation(self.task)
        self.assertNotEqual(a1, "not an activation")

    def test_hash_equal_for_same_task(self):
        a1 = _TestActivation(self.task)
        a2 = _TestActivation(self.task)
        self.assertEqual(hash(a1), hash(a2))

    def test_hash_different_for_different_task(self):
        a1 = _TestActivation(self.task)
        other_task = _make_task(
            status=STATUS.NEW, process=self.process, flow_task=self.flow_task
        )
        a2 = _TestActivation(other_task)
        self.assertNotEqual(hash(a1), hash(a2))


class TestReviveTransition(TestCase):
    """Test revive transition with mocked database operations."""

    def setUp(self):
        self.flow_class = _make_flow_class()
        self.flow_task = _make_flow_task(self.flow_class)
        self.process = _make_process(flow_class=self.flow_class)
        self.task = _make_task(
            status=STATUS.CANCELED, process=self.process, flow_task=self.flow_task
        )
        self.activation = _TestActivation(self.task)

    @patch.object(Activation, "_activate_next")
    def test_revive_creates_new_task_and_activates(self, mock_activate_next):
        self.activation.revive()
        self.assertEqual(self.task.status, STATUS.REVIVED)
        mock_activate_next.assert_called_once()