from django.contrib.auth.models import Permission, User
from django.test import TestCase

from viewflow import this
from viewflow.authorization import has_permission
from viewflow.fsm import State

from .fsm.test_fsm__basics import ReviewState


class Publication(object):
    stage = State(ReviewState, default=ReviewState.NEW)

    @stage.transition(
        source=ReviewState.NEW,
        target=ReviewState.APPROVED,
        permission="auth.add_user",
    )
    def approve(self):
        pass


class ModeratedPublication(object):
    stage = State(ReviewState, default=ReviewState.NEW)

    @stage.transition(
        source=ReviewState.NEW,
        target=ReviewState.APPROVED,
        permission=this.can_approve,
    )
    def approve(self):
        pass

    def can_approve(self, user):
        return State.CONDITION(user.is_staff, unmet="Only staff users can approve")


class Test(TestCase):
    def setUp(self):
        self.authorized_user = User.objects.create_user(username="authorized")
        self.staff_user = User.objects.create_user(username="staff", is_staff=True)
        self.unprivileged_user = User.objects.create_user(username="unprivileged")
        self.authorized_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="auth", codename="add_user")
        )

    def test_helper_uses_django_permission_lookup(self):
        self.assertTrue(has_permission(self.authorized_user, "auth.add_user"))
        self.assertFalse(has_permission(self.unprivileged_user, "auth.add_user"))

    def test_transition_supports_django_permission_name(self):
        publication = Publication()
        transition = next(iter(Publication.approve.get_transitions()))

        self.assertTrue(transition.has_permission(publication, self.authorized_user))
        self.assertTrue(transition.has_perm(publication, self.authorized_user))
        self.assertTrue(publication.approve.has_permission(self.authorized_user))
        self.assertTrue(publication.approve.has_perm(self.authorized_user))

        self.assertFalse(transition.has_permission(publication, self.unprivileged_user))
        self.assertFalse(transition.has_perm(publication, self.unprivileged_user))
        self.assertFalse(publication.approve.has_permission(self.unprivileged_user))
        self.assertFalse(publication.approve.has_perm(self.unprivileged_user))

    def test_callable_permission_api_remains_compatible(self):
        publication = ModeratedPublication()
        transition = next(iter(ModeratedPublication.approve.get_transitions()))

        self.assertTrue(transition.has_permission(publication, self.staff_user))
        self.assertTrue(transition.has_perm(publication, self.staff_user))
        self.assertTrue(publication.approve.has_permission(self.staff_user))
        self.assertTrue(publication.approve.has_perm(self.staff_user))

        self.assertFalse(transition.has_permission(publication, self.unprivileged_user))
        self.assertFalse(transition.has_perm(publication, self.unprivileged_user))
        self.assertFalse(publication.approve.has_permission(self.unprivileged_user))
        self.assertFalse(publication.approve.has_perm(self.unprivileged_user))
