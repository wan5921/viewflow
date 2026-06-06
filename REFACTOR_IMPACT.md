# 重构影响说明

## 概述
本次重构主要是为了将权限校验逻辑从各个分散的地方集中到一个统一的模块中，提高代码的可维护性和复用性。

## 修改的文件

### 1. 新增文件
- **viewflow/authorization.py**：新增模块，包含以下内容：
  - `has_permission` 函数：用于统一的权限检查
  - `AuthorizationMixin` 类：提供权限检查的 mixin 类

### 2. 修改的文件
- **viewflow/__init__.py**：
  - 新增 `has_permission` 和 `AuthorizationMixin` 的导出，保持后向兼容性
- **viewflow/workflow/nodes/mixins.py**：
  - 更新 `NodePermissionMixin` 使其继承自 `AuthorizationMixin`
  - 新增对 `AuthorizationMixin` 的导入
- **viewflow/workflow/nodes/view.py**：
  - 更新 `can_unassign` 方法，使用 `AuthorizationMixin` 中的 `check_manage_permission` 方法
  - 新增对 `AuthorizationMixin` 的导入
- **viewflow/workflow/nodes/start.py**：
  - 新增对 `AuthorizationMixin` 的导入（为未来功能扩展做准备）

### 3. 新增测试文件
- **tests/test_authorization.py**：新增的测试用例，测试新增的授权模块功能

## 新增的模块职责

### AuthorizationMixin
这个 mixin 类主要提供以下功能：
1. **统一的权限检查接口**：
   - `has_permission()`：检查用户是否有特定权限，支持字符串权限和可调用对象
   - `check_owner_permission()`：检查用户是否有任务所有者权限
   - `check_manage_permission()`：检查用户是否有流程管理权限

2. **可复用的权限逻辑**：为所有需要权限检查的节点类提供统一的基类

### has_permission 函数
这个函数提供了一个统一的权限检查包装器，可以用于：
1. 直接检查 Django 权限字符串
2. 接受可调用的权限检查函数
3. 支持使用 `this` 对象进行延迟解析
4. 支持权限检查的对象级权限

## API 兼容性
本次重构完全保持了向后兼容性：
1. 所有现有的公共 API 保持不变
2. 所有现有的测试用例应该仍然可以正常通过
3. `NodePermissionMixin` 仍然是可用的，现在它继承自 `AuthorizationMixin`
4. 新增的功能是可选的，可以逐步采用

## 使用示例

### 示例 1：使用 has_permission 函数
```python
from viewflow import has_permission
from viewflow.fsm import State

class MyModel(object):
    state = State(['draft', 'published'])
    
    @state.transition(
        source='draft',
        target='published',
        permission=has_permission('myapp.can_publish')
    )
    def publish(self):
        pass
```

### 示例 2：使用 AuthorizationMixin
由于 `NodePermissionMixin` 已经继承自 `AuthorizationMixin`，所以所有使用 `NodePermissionMixin` 的节点类（如 `View` 和 `Start`）都可以自动使用这些功能：
```python
from viewflow.workflow import Flow
from viewflow.workflow.nodes import View

class MyFlow(Flow):
    approve = View(...).Permission('myapp.can_approve')
    
    # approve 节点现在可以使用 AuthorizationMixin 的所有方法
    # 比如 approve.has_permission(...)
```

## 优势
1. **代码复用**：权限检查逻辑集中在一个地方，减少重复代码
2. **统一接口**：所有权限检查都通过一致的接口进行
3. **可扩展性**：未来可以在 `AuthorizationMixin` 中添加更多权限相关功能
4. **可测试性**：权限逻辑更容易测试和维护
5. **向后兼容**：现有代码无需修改即可继续工作
