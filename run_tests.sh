
#!/bin/bash
echo "=== Running tests with coverage ==="
export DJANGO_SETTINGS_MODULE=tests.settings

# 检查是否安装了 pytest-cov
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo "Installing pytest and pytest-cov..."
    pip install pytest pytest-django pytest-cov coverage
fi

# 运行我们的新测试
echo "Running the new tests..."
python -m pytest tests/workflow/test_nodes__if.py tests/workflow/test_activation_extended.py -v

# 运行完整的覆盖率测试
echo "Running coverage tests..."
python -m pytest tests/workflow/ --cov=viewflow.flows --cov-report=term-missing --cov-fail-under=90

echo "=== Test run complete ==="
