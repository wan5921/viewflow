from unittest.mock import MagicMock, PropertyMock, patch

from django.contrib.auth.models import User, Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from viewflow.authorization import AuthorizationMixin
from viewflow.workflow import STATUS
from viewflow.workflow.activation import Activation, has_manage_permission
from viewflow.workflow.models import Process, Task


class MockFlowClass:
    class instance:
        @staticmethod
        def has_manage_permission(user, obj=None):
            return user.is_superuser


class MockFlowTask:
    flow_class = MockFlowClass
    _owner_permission_obj = None


class TestHasPermission(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username="superuser", password="test", is_superuser=True
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="test", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="test"
        )
        self.anonymous_user = type(
            "AnonymousUser", (), {"is_authenticated": False}
        )()

        self.process = Process()
        self.task = Task(process=self.process, status=STATUS.NEW)
        self.task.flow_task = MockFlowTask()
        self.activation = Activation(self.task)

    def test_unauthenticated_user_denied(self):
        self.assertFalse(self.activation.has_permission(self.anonymous_user))

    def test_none_user_denied(self):
        self.assertFalse(self.activation.has_permission(None))

    def test_explicit_perm_granted(self):
        perm = Permission.objects.first()
        if perm:
            codename = f"{perm.content_type.app_label}.{perm.codename}"
            self.assertFalse(
                self.activation.has_permission(self.staff_user, perm=codename)
            )
            self.staff_user.user_permissions.add(perm)
            self.staff_user = User.objects.get(pk=self.staff_user.pk)
            self.assertTrue(
                self.activation.has_permission(self.staff_user, perm=codename)
            )

    def test_owner_permission_denied_for_regular_user(self):
        self.task.owner_permission = "tests.test_perm"
        self.assertFalse(self.activation.has_permission(self.regular_user))

    def test_owner_permission_granted_for_superuser(self):
        self.task.owner_permission = "tests.test_perm"
        self.assertTrue(self.activation.has_permission(self.superuser))

    def test_no_owner_permission_allows_any_authenticated_user(self):
        self.task.owner_permission = None
        self.assertTrue(self.activation.has_permission(self.regular_user))

    def test_callable_owner_permission_obj(self):
        self.task.owner_permission = "tests.test_perm"
        self.task.flow_task = MockFlowTask()
        self.task.flow_task._owner_permission_obj = lambda process: None
        self.assertTrue(self.activation.has_permission(self.superuser))


class TestHasManagePermission(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username="superuser", password="test", is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="test"
        )

        self.process = Process()
        self.task = Task(process=self.process, status=STATUS.NEW)
        self.task.flow_task = MockFlowTask()
        self.activation = Activation(self.task)

    def test_superuser_has_manage_permission(self):
        self.assertTrue(self.activation.has_manage_permission(self.superuser))

    def test_regular_user_no_manage_permission(self):
        self.assertFalse(self.activation.has_manage_permission(self.regular_user))

    def test_standalone_function_delegates_to_mixin(self):
        self.assertTrue(has_manage_permission(self.activation, self.superuser))
        self.assertFalse(has_manage_permission(self.activation, self.regular_user))

    def test_standalone_function_backward_compatible(self):
        result = has_manage_permission(self.activation, self.superuser)
        self.assertEqual(result, self.activation.has_manage_permission(self.superuser))


class TestPerform(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username="superuser", password="test", is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="test"
        )

    def test_unknown_transition_raises_value_error(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        task.flow_task = MockFlowTask()
        activation = Activation(task)

        with self.assertRaises(ValueError) as ctx:
            activation.perform("nonexistent_transition")
        self.assertIn("nonexistent_transition", str(ctx.exception))

    def test_permission_denied_when_user_lacks_perm(self):
        process = Process()
        task = Task(process=process, status=STATUS.DONE)
        task.flow_task = MockFlowTask()
        activation = Activation(task)

        mock_method = MagicMock()
        mock_method.has_perm = MagicMock(return_value=False)
        with patch.object(activation, "undo", mock_method):
            with self.assertRaises(PermissionDenied):
                activation.perform("undo", user=self.regular_user)

    def test_transition_executed_when_user_has_perm(self):
        process = Process()
        task = Task(process=process, status=STATUS.DONE)
        task.flow_task = MockFlowTask()
        activation = Activation(task)

        mock_method = MagicMock()
        mock_method.has_perm = MagicMock(return_value=True)
        with patch.object(activation, "undo", mock_method):
            activation.perform("undo", user=self.superuser)
            mock_method.assert_called_once()

    def test_transition_executed_without_user(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        task.flow_task = MockFlowTask()
        activation = Activation(task)

        mock_method = MagicMock()
        with patch.object(activation, "complete", mock_method):
            activation.perform("complete", user=None)
            mock_method.assert_called_once()

    def test_transition_without_has_perm_skips_check(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        task.flow_task = MockFlowTask()
        activation = Activation(task)

        mock_method = MagicMock(spec=[])
        with patch.object(activation, "complete", mock_method):
            activation.perform("complete", user=self.regular_user)
            mock_method.assert_called_once()


class TestAuthorizationMixinIntegration(TestCase):
    def test_activation_inherits_authorization_mixin(self):
        self.assertTrue(issubclass(Activation, AuthorizationMixin))

    def test_activation_has_permission_method(self):
        process = Process()
        task = Task(process=process, status=STATUS.NEW)
        activation = Activation(task)
        self.assertTrue(hasattr(activation, "has_permission"))
        self.assertTrue(hasattr(activation, "has_manage_permission"))
        self.assertTrue(hasattr(activation, "perform"))
        self.assertTrue(callable(activation.has_permission))
        self.assertTrue(callable(activation.has_manage_permission))
        self.assertTrue(callable(activation.perform))

    def test_import_from_workflow_package(self):
        from viewflow.workflow import AuthorizationMixin as ImportedMixin

        self.assertIs(ImportedMixin, AuthorizationMixin)

    def test_import_from_top_level_package(self):
        from viewflow.authorization import AuthorizationMixin as DirectImport

        self.assertIs(DirectImport, AuthorizationMixin)
