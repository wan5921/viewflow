"""Test for authorization module."""

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from viewflow import this
from viewflow.fsm import State
from viewflow.authorization import has_permission, AuthorizationMixin
from viewflow.workflow import Flow
from viewflow.workflow.nodes import View, Start
from viewflow.workflow.models import Process, Task


class _TestProcess(Process):
    class Meta:
        app_label = 'viewflow'
        permissions = [
            ('can_test_process', 'Can test process'),
        ]


class _TestTask(Task):
    class Meta:
        app_label = 'viewflow'


class _TestFlow(Flow):
    process_class = _TestProcess
    task_class = _TestTask

    start = Start(lambda *args, **kwargs: None).Permission(
        'viewflow.can_test_process'
    )

    test_view = View(lambda *args, **kwargs: None).Permission(
        'viewflow.can_test_process'
    )

    start.Next(test_view)


class _Publication(object):
    stage = State(['new', 'published'], default='new')

    @stage.transition(
        source='new',
        target='published',
        permission=has_permission('viewflow.can_test_process')
    )
    def publish(self):
        pass

    @stage.transition(
        source='new',
        target='published',
        permission=this.can_publish
    )
    def publish_with_this(self):
        pass

    def can_publish(self, user):
        return user.is_staff


class AuthorizationTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='password',
            email='superuser@example.com'
        )

        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='password',
            is_staff=True
        )

        self.user_with_permission = User.objects.create_user(
            username='user_with_perm',
            password='password'
        )

        self.user_without_permission = User.objects.create_user(
            username='user_without_perm',
            password='password'
        )

        # Assign permission to user_with_permission
        content_type = ContentType.objects.get_for_model(_TestProcess)
        permission = Permission.objects.get(
            content_type=content_type,
            codename='can_test_process'
        )
        self.user_with_permission.user_permissions.add(permission)

    def test_has_permission_string(self):
        """Test has_permission with a string permission."""
        check_perm = has_permission('viewflow.can_test_process')
        self.assertTrue(check_perm(None, self.user_with_permission))
        self.assertFalse(check_perm(None, self.user_without_permission))

    def test_has_permission_callable(self):
        """Test has_permission with a callable."""
        def custom_check(instance, user):
            return user.is_staff

        check_perm = has_permission(custom_check)
        self.assertTrue(check_perm(None, self.staff_user))
        self.assertFalse(check_perm(None, self.user_with_permission))

    def test_authorization_mixin_has_permission(self):
        """Test AuthorizationMixin's has_permission method."""
        mixin = AuthorizationMixin()
        check_perm = mixin.has_permission('viewflow.can_test_process')
        self.assertTrue(check_perm(None, self.user_with_permission))
        self.assertFalse(check_perm(None, self.user_without_permission))

    def test_authorization_mixin_check_manage_permission(self):
        """Test AuthorizationMixin's check_manage_permission method."""
        mixin = AuthorizationMixin()
        # Without flow_class, should return False
        self.assertFalse(mixin.check_manage_permission(self.superuser))

    def test_fsm_transition_with_has_permission(self):
        """Test FSM transition with has_permission."""
        pub = _Publication()
        self.assertTrue(pub.publish.has_perm(self.user_with_permission))
        self.assertFalse(pub.publish.has_perm(self.user_without_permission))

    def test_fsm_transition_with_this_permission(self):
        """Test FSM transition with this object permission."""
        pub = _Publication()
        self.assertTrue(pub.publish_with_this.has_perm(self.staff_user))
        self.assertFalse(pub.publish_with_this.has_perm(self.user_without_permission))

    def test_node_permission_mixin_inheritance(self):
        """Test that NodePermissionMixin inherits from AuthorizationMixin."""
        from viewflow.workflow.nodes.mixins import NodePermissionMixin
        self.assertTrue(issubclass(NodePermissionMixin, AuthorizationMixin))

    def test_view_node_permission_methods(self):
        """Test that View node has access to AuthorizationMixin methods."""
        # Create a flow to test View node
        flow = _TestFlow.instance
        
        # Check that View node has check_manage_permission method
        self.assertTrue(hasattr(flow.test_view, 'check_manage_permission'))
        self.assertTrue(hasattr(flow.test_view, 'has_permission'))

    def test_start_node_permission_methods(self):
        """Test that Start node has access to AuthorizationMixin methods."""
        # Create a flow to test Start node
        flow = _TestFlow.instance
        
        # Check that Start node has check_manage_permission method
        self.assertTrue(hasattr(flow.start, 'check_manage_permission'))
        self.assertTrue(hasattr(flow.start, 'has_permission'))
