from typing import Any

from viewflow.this_object import ThisObject
from viewflow.utils import DEFAULT


def has_permission(user: Any, permission: str, obj: Any = None) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.has_perm(permission, obj=obj)


class AuthorizationMixin(object):
    def get_transition(self):
        current_state = self._state.get(self._instance)
        return self._descriptor.get_transition(current_state)

    def has_permission(self, user: Any) -> bool:
        transition = self.get_transition()
        if transition is None:
            return False

        permission = transition.permission
        if permission is DEFAULT:
            return False
        if permission is None:
            return True
        if callable(permission):
            return permission(self._instance, user)
        if isinstance(permission, ThisObject):
            return permission.resolve(self._instance)(user)
        if isinstance(permission, str):
            return has_permission(user, permission)
        raise ValueError(f'Unknown permission type {type(permission)}')

    def has_perm(self, user: Any) -> bool:
        return self.has_permission(user)

    def perform(self, *args: Any, **kwargs: Any) -> Any:
        with self.Wrapper(self, kwargs=kwargs):
            return self._func(self._instance, *args, **kwargs)
