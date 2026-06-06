from django.core.exceptions import PermissionDenied

def has_permission(user, permission, obj=None):
    """
    调用 Django 权限系统校验权限。
    """
    if not user or not user.is_active:
        return False
    return user.has_perm(permission, obj)

class AuthorizationMixin:
    """
    权限校验 Mixin。将原来的权限校验逻辑移至此处。
    """
    permission_required = None

    def check_permission(self, request, obj=None):
        if self.permission_required:
            if not has_permission(request.user, self.permission_required, obj):
                raise PermissionDenied(f"User does not have {self.permission_required} permission.")
        return True
    
    def perform(self, request, *args, **kwargs):
        """
        保留原有 API 兼容性，将权限校验移至此处。
        """
        self.check_permission(request)
        perform_func = getattr(super(), 'perform', None)
        if perform_func:
            return perform_func(request, *args, **kwargs)
