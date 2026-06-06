from django.core.exceptions import PermissionDenied


class AuthorizationMixin:
    """
    Mixin that provides authorization capabilities to Activation classes.

    Integrates with Django's permission system to centralize permission
    checking logic that was previously scattered across activation
    transitions and view wrappers.
    """

    def has_permission(self, user, perm=None, obj=None):
        """
        Check if the user has the specified permission using Django's permission system.

        If perm is provided, checks that specific permission directly.
        If perm is None, falls back to checking the task's owner_permission
        field, which is the permission assigned to the task by the flow definition.

        Args:
            user: The user instance to check permissions for.
            perm: Optional permission string (e.g., 'app_label.codename').
                  If None, checks the task's owner_permission.
            obj: Optional object for object-level permission check.

        Returns:
            bool: True if the user has the permission, False otherwise.
        """
        if user is None or not user.is_authenticated:
            return False

        if perm is not None:
            return user.has_perm(perm, obj=obj) or user.has_perm(perm)

        task = self.task
        if hasattr(task, "owner_permission") and task.owner_permission:
            owner_perm_obj = None
            flow_task = self.flow_task
            if (
                hasattr(flow_task, "_owner_permission_obj")
                and flow_task._owner_permission_obj
            ):
                owner_perm_obj = flow_task._owner_permission_obj
                if callable(owner_perm_obj):
                    owner_perm_obj = owner_perm_obj(task.process)

            return user.has_perm(
                task.owner_permission, obj=owner_perm_obj
            ) or user.has_perm(task.owner_permission)

        return True

    def has_manage_permission(self, user):
        """
        Check if the user has manage permission for this flow.

        Delegates to the flow class instance's has_manage_permission method,
        which checks Django's model-level manage permission.

        Args:
            user: The user instance to check permissions for.

        Returns:
            bool: True if the user has manage permission, False otherwise.
        """
        return self.flow_class.instance.has_manage_permission(user)

    def perform(self, transition_name, user=None):
        """
        Execute a transition with permission checking.

        This method centralizes the pattern of checking permissions before
        executing a transition. Previously, permission checks were done
        separately in view wrappers (wrap_task_view, wrap_start_view, etc.)
        and were not integrated into the activation layer.

        Args:
            transition_name: Name of the transition method to execute
                           (e.g., 'undo', 'cancel', 'revive').
            user: Optional user instance. If provided, the transition's
                  permission is checked before execution.

        Returns:
            The result of the transition method.

        Raises:
            PermissionDenied: If the user does not have permission for
                            the transition.
            ValueError: If the transition name is not found.
        """
        transition_method = getattr(self, transition_name, None)
        if transition_method is None:
            raise ValueError(f"Unknown transition: {transition_name}")

        if user is not None and hasattr(transition_method, "has_perm"):
            if not transition_method.has_perm(user):
                raise PermissionDenied(
                    f"User does not have permission to perform '{transition_name}'"
                )

        return transition_method()
