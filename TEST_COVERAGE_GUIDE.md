
# Test Coverage Guide for viewflow.flows

## Overview
This guide describes the comprehensive tests created to achieve 90%+ coverage for `viewflow.flows` module.

## Test Files Created

### 1. `tests/workflow/test_nodes__if.py`
Tests for the If node functionality including:
- ✅ Normal flow with condition=True
- ✅ Normal flow with condition=False
- ✅ Mocking `Activation.create_next` to avoid database writes
- ✅ Testing `TransitionNotAllowed` exception on invalid transitions
- ✅ Testing on_error callback (exception_guard)

### 2. `tests/workflow/test_activation_extended.py`
Extended tests for Activation class including:
- ✅ Mocking Activation objects
- ✅ Testing helper functions (parent_tasks_completed, process_not_canceled)
- ✅ Testing exception_guard context manager
- ✅ Testing IfActivation with both True/False conditions
- ✅ Comprehensive use of `unittest.mock.patch`

## Configuration Files Updated

### `setup.cfg`
Added coverage configuration:
- `[coverage:run]` - Configures source directory and omits
- `[coverage:report]` - Configures report options

### `pytest.ini`
Created pytest configuration for Django test discovery.

## How to Run Tests

### Option 1: Using Django's test runner
```bash
python manage.py test tests/workflow/test_nodes__if.py tests/workflow/test_activation_extended.py -v 2
```

### Option 2: Using pytest with coverage
```bash
# Install requirements first
pip install pytest pytest-django pytest-cov coverage

# Run with coverage
pytest tests/workflow/test_nodes__if.py tests/workflow/test_activation_extended.py \
    --cov=viewflow.flows \
    --cov-report=term-missing \
    --cov-fail-under=90
```

### Option 3: Using tox (as configured in the project)
```bash
tox -e py312-dj60
```

## Key Features Tested

### 1. Activation Object Mocking
- Uses `unittest.mock.Mock` to create mock Task and Process objects
- Tests Activation initialization without requiring database setup
- Covers exception handling in `exception_guard`

### 2. Transition Testing
- Tests valid transitions through normal flow
- Tests invalid transitions and verifies `TransitionNotAllowed` is raised
- Covers state machine validation

### 3. If Condition Coverage
- Tests both True and False branches of If node
- Verifies correct paths are taken based on condition
- Tests `IfActivation` class directly

### 4. Error Handling
- Tests exception_guard behavior
- Verifies error states (STATUS.ERROR)
- Tests exception propagation vs suppression

### 5. Mocking Database Operations
- Uses `@mock.patch` to avoid actual database writes
- Mocks `create_next` method
- Allows testing flow logic independently of persistence layer

## Coverage Goals

The tests are designed to cover:
- `viewflow.workflow.activation` - Activation class and helpers
- `viewflow.workflow.nodes.if_gate` - If node and IfActivation
- `viewflow.fsm` - TransitionNotAllowed and state machine
- `viewflow.workflow.flow` - Flow class and node integration

## Test Structure

Each test follows this pattern:
1. Set up mock objects (Task, Process, FlowTask)
2. Initialize Activation instance
3. Perform test actions
4. Assert expected results
5. Verify side effects (status changes, data updates, etc.)

## Notes

- The tests use Django's TestCase for database-related tests
- Mock-heavy tests use unittest.TestCase for speed
- All tests are independent and can run in any order
- Fixtures are kept minimal to maintain test isolation
