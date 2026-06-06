"""Authorization utilities for Viewflow."""

# Copyright (c) 2017-2020, Mikhail Podgurskiy
# All Rights Reserved.

# This work is dual-licensed under AGPL defined in file 'LICENSE' with
# LICENSE_EXCEPTION and the Commercial license defined in file 'COMM_LICENSE',
# which is part of this source code package.

from typing import Any, Callable, Optional, Union
from django.contrib.auth.models import User
from viewflow import this


def has_permission(
    permission: Union[str, Callable[[Any, User], bool]],
    obj: Optional[Any] = None,
) -> Callable[[Any, User], bool]:
    """
    Check if a user has the specified permission.
    
    Returns a callable that can be used as a permission check for FSM transitions.
    
    Args:
        permission: A permission string or a callable that returns a boolean.
        obj: An optional object to check the permission against.
        
    Returns:
        A callable that takes an instance and a user, and returns True if the user
        has the permission.
    """
    def check_permission(instance: Any, user: User) -> bool:
        if callable(permission):
            return permission(instance, user)
        elif isinstance(permission, this):
            resolved_perm = permission.resolve(instance)
            if callable(resolved_perm):
                return resolved_perm(user)
            return user.has_perm(resolved_perm, obj)
        else:
            return user.has_perm(permission, obj)
    
    return check_permission


class AuthorizationMixin:
    """
    Mixin that provides authorization utilities to flow nodes.
    
    This mixin centralizes permission checking logic for flow nodes.
    """
    
    def has_permission(
        self,
        permission: Union[str, Callable[[Any, User], bool]],
        obj: Optional[Any] = None,
    ) -> Callable[[Any, User], bool]:
        """
        Check if a user has the specified permission.
        
        This method is a convenience wrapper around the module-level `has_permission`
        function, making it easily accessible on nodes that inherit from this mixin.
        
        Args:
            permission: A permission string or a callable that returns a boolean.
            obj: An optional object to check the permission against.
            
        Returns:
            A callable that takes an instance and a user, and returns True if the user
            has the permission.
        """
        return has_permission(permission, obj)
    
    def check_owner_permission(
        self,
        user: User,
        task: Any,
    ) -> bool:
        """
        Check if a user has permission to act on a task based on ownership.
        
        This method checks:
        1. If the user is the owner of the task
        2. If the user has the required permission for the task
        
        Args:
            user: The user to check.
            task: The task to check permissions for.
            
        Returns:
            True if the user has permission, False otherwise.
        """
        from viewflow.utils import is_owner
        
        # Check if user is the task owner
        if is_owner(task.owner, user):
            return True
        
        # Check if user has the required permission
        if task.owner_permission:
            permission_obj = None
            if hasattr(self, '_owner_permission_obj') and self._owner_permission_obj:
                if callable(self._owner_permission_obj):
                    permission_obj = self._owner_permission_obj(task.process)
                else:
                    permission_obj = self._owner_permission_obj
            
            return user.has_perm(task.owner_permission, permission_obj) or \
                   user.has_perm(task.owner_permission)
        
        return False
    
    def check_manage_permission(
        self,
        user: User,
    ) -> bool:
        """
        Check if a user has management permissions for the flow.
        
        Args:
            user: The user to check.
            
        Returns:
            True if the user has management permission, False otherwise.
        """
        if hasattr(self, 'flow_class') and self.flow_class:
            return self.flow_class.instance.has_manage_permission(user)
        return False
