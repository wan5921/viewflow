from django.contrib.auth.models import AnonymousUser, Permission, User
from django.test import TestCase

from viewflow import fsm
from viewflow.authorization import has_permission


class ReviewState(object):
    NEW = 'new'
    PUBLISHED = 'published'


class Publication(object):
    stage = fsm.State(ReviewState, default=ReviewState.NEW)

    def __init__(self):
        self.performed = False

    @stage.transition(
        source=ReviewState.NEW,
        target=ReviewState.PUBLISHED,
        permission='auth.add_user',
    )
    def publish(self):
        self.performed = True


class Test(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission = Permission.objects.get(codename='add_user')
        cls.authorized_user = User.objects.create_user(username='authorized')
        cls.authorized_user.user_permissions.add(cls.permission)
        cls.unauthorized_user = User.objects.create_user(username='unauthorized')

    def test_has_permission_uses_django_auth_backend(self):
        self.assertTrue(has_permission(self.authorized_user, 'auth.add_user'))
        self.assertFalse(has_permission(self.unauthorized_user, 'auth.add_user'))
        self.assertFalse(has_permission(AnonymousUser(), 'auth.add_user'))

    def test_transition_bound_method_exposes_authorization_api(self):
        publication = Publication()

        self.assertTrue(publication.publish.has_permission(self.authorized_user))
        self.assertTrue(publication.publish.has_perm(self.authorized_user))
        self.assertFalse(publication.publish.has_permission(self.unauthorized_user))

    def test_transition_perform_keeps_call_api_compatible(self):
        publication = Publication()
        publication.publish.perform()

        self.assertTrue(publication.performed)
        self.assertEqual(publication.stage, ReviewState.PUBLISHED)

        publication = Publication()
        publication.publish()

        self.assertTrue(publication.performed)
        self.assertEqual(publication.stage, ReviewState.PUBLISHED)
