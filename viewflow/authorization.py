from typing import Any


def has_permission(activation: "Activation", user: Any) -> bool:
    """
    Check if the user has permission to access the activation's flow task.

    Uses Django's built-in permission system (user.has_perm) to determine
    whether the user is authorized.

    Args:
        activation (Activation): The current activation instance.
        user (Any): The user instance to check permissions for.

    Returns:
        bool: True if the user has permission, False otherwise.
    """
    if user is None:
        return False

    if activation.task.owner_permission:
        return user.has_perm(
            activation.task.owner_permission,
            obj=activation.task.owner_permission_obj,
        )

    if hasattr(activation.flow_task, "can_execute"):
        return activation.flow_task.can_execute(user, activation.task)

    return True


class AuthorizationMixin:
    """
    Mixin that provides centralized permission checking for flow activations.

    This mixin encapsulates permission check logic that was previously
    scattered across activation transition decorators, providing a single
    place to extend or override authorization behavior.
    """

    def has_permission(self, user: Any) -> bool:
        """
        Check if the given user has permission to access this activation.

        Delegates to the module-level ``has_permission`` function.

        Args:
            user (Any): The user to check.

        Returns:
            bool: True if the user is authorized, False otherwise.
        """
        return has_permission(self, user)

    def has_manage_permission(self, user: Any) -> bool:
        """
        Check if the given user has manage permission for this flow.

        Args:
            user (Any): The user to check.

        Returns:
            bool: True if the user has manage permission, False otherwise.
        """
        return self.flow_class.instance.has_manage_permission(user)