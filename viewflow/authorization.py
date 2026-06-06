from collections.abc import Iterable
from typing import Any

from viewflow.utils import DEFAULT


class AuthorizationMixin:
    _state: Any
    _descriptor: Any
    _instance: object

    def has_permission(self, user: Any) -> bool:
        current_state = self._state.get(self._instance)
        transition = self._descriptor.get_transition(current_state)
        if transition:
            return transition.has_permission(self._instance, user)
        return False

    def has_perm(self, user: Any) -> bool:
        return self.has_permission(user)


def has_permission(user: Any, permission: Any, obj: Any = None) -> bool:
    if permission is DEFAULT:
        return False
    if permission is None:
        return True
    if isinstance(permission, str):
        return user.has_perm(permission, obj=obj)
    if isinstance(permission, Iterable) and not isinstance(permission, (str, bytes)):
        permissions = tuple(permission)
        if permissions and all(isinstance(item, str) for item in permissions):
            return user.has_perms(permissions, obj=obj)
    if callable(permission):
        return permission(user)
    return bool(permission)
