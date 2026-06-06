import pytest
from unittest.mock import Mock
from django.core.exceptions import PermissionDenied
from viewflow.authorization import has_permission, AuthorizationMixin

def test_has_permission():
    # 测试有权限的情况
    mock_user = Mock()
    mock_user.is_active = True
    mock_user.has_perm.return_value = True
    
    assert has_permission(mock_user, 'test.permission') is True
    mock_user.has_perm.assert_called_with('test.permission', None)
    
    # 测试无权限的情况
    mock_user.has_perm.return_value = False
    assert has_permission(mock_user, 'test.permission') is False

    # 测试用户未激活或不存在的情况
    mock_user.is_active = False
    assert has_permission(mock_user, 'test.permission') is False
    assert has_permission(None, 'test.permission') is False

class DummyActivation(AuthorizationMixin):
    permission_required = 'test.permission'
    def __init__(self):
        self.performed = False
        
    def perform(self, request, *args, **kwargs):
        super().perform(request, *args, **kwargs)
        self.performed = True

def test_authorization_mixin_success():
    activation = DummyActivation()
    mock_request = Mock()
    mock_request.user.is_active = True
    mock_request.user.has_perm.return_value = True
    
    activation.perform(mock_request)
    assert activation.performed is True

def test_authorization_mixin_denied():
    activation = DummyActivation()
    mock_request = Mock()
    mock_request.user.is_active = True
    mock_request.user.has_perm.return_value = False
    
    with pytest.raises(PermissionDenied):
        activation.perform(mock_request)
    assert activation.performed is False
