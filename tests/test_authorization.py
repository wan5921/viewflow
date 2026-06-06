from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from viewflow.authorization import has_permission, AuthorizationMixin
from viewflow.workflow import STATUS
from viewflow.workflow.activation import Activation, has_manage_permission
from viewflow.workflow.models import Process, Task


class TestHasPermissionFunction(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "test")
        self.process = Process.objects.create(status=STATUS.NEW)
        self.task = Task.objects.create(
            process=self.process,
            status=STATUS.NEW,
        )

    def test_has_permission_no_owner_permission(self):
        activation = Activation(self.task)
        self.assertTrue(has_permission(activation, self.user))

    def test_has_permission_none_user(self):
        activation = Activation(self.task)
        self.assertFalse(has_permission(activation, None))

    def test_has_permission_with_owner_permission(self):
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.create(
            codename="can_approve_test",
            name="Can approve test",
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)

        self.task.owner_permission = "auth.can_approve_test"
        self.task.save()

        activation = Activation(self.task)
        self.assertTrue(has_permission(activation, self.user))

    def test_has_permission_with_owner_permission_denied(self):
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.create(
            codename="can_approve_test2",
            name="Can approve test2",
            content_type=content_type,
        )

        self.task.owner_permission = "auth.can_approve_test2"
        self.task.save()

        activation = Activation(self.task)
        self.assertFalse(has_permission(activation, self.user))


class TestAuthorizationMixin(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "test")
        self.process = Process.objects.create(status=STATUS.NEW)
        self.task = Task.objects.create(
            process=self.process,
            status=STATUS.NEW,
        )

    def test_mixin_has_permission(self):
        activation = Activation(self.task)
        self.assertTrue(activation.has_permission(self.user))

    def test_mixin_has_permission_none_user(self):
        activation = Activation(self.task)
        self.assertFalse(activation.has_permission(None))

    def test_mixin_has_permission_with_owner_permission(self):
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.create(
            codename="can_approve_mixin",
            name="Can approve mixin",
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)

        self.task.owner_permission = "auth.can_approve_mixin"
        self.task.save()

        activation = Activation(self.task)
        self.assertTrue(activation.has_permission(self.user))

    def test_mixin_has_permission_with_owner_permission_denied(self):
        content_type = ContentType.objects.get_for_model(User)
        Permission.objects.create(
            codename="can_approve_mixin2",
            name="Can approve mixin2",
            content_type=content_type,
        )

        self.task.owner_permission = "auth.can_approve_mixin2"
        self.task.save()

        activation = Activation(self.task)
        self.assertFalse(activation.has_permission(self.user))


class TestActivationInheritsAuthorizationMixin(TestCase):
    def test_activation_is_instance_of_authorization_mixin(self):
        self.assertTrue(issubclass(Activation, AuthorizationMixin))

    def test_activation_has_permission_method(self):
        self.assertTrue(hasattr(Activation, "has_permission"))

    def test_activation_has_manage_permission_method(self):
        self.assertTrue(hasattr(Activation, "has_manage_permission"))


class TestBackwardCompatibility(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "test")
        self.process = Process.objects.create(status=STATUS.NEW)
        self.task = Task.objects.create(
            process=self.process,
            status=STATUS.NEW,
        )

    def test_has_manage_permission_function_exists(self):
        activation = Activation(self.task)
        result = has_manage_permission(activation, self.user)
        self.assertIsInstance(result, bool)

    def test_has_manage_permission_calls_mixin(self):
        activation = Activation(self.task)

        class FakeFlowInstance:
            called = False

            def has_manage_permission(self, user):
                FakeFlowInstance.called = True
                return True

        activation.flow_class = type(
            "FakeFlowClass",
            (),
            {"instance": FakeFlowInstance()},
        )()

        has_manage_permission(activation, self.user)
        self.assertTrue(FakeFlowInstance.called)