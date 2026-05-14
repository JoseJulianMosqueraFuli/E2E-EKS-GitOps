# GitOps Implementation Tests

This directory contains property-based tests and unit tests for the GitOps implementation.

## Test Structure

- `test_gitops_controller_health.py`: Property-based tests for GitOps controller health (Property 1)
- Additional test files will be added as implementation progresses

## Running Tests

### Prerequisites

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install test dependencies with Poetry
poetry install

# Or using pip (alternative)
pip install -r requirements.txt

# Ensure you have access to a Kubernetes cluster with GitOps controllers installed
kubectl cluster-info
```

### Run All Tests

```bash
# Using Poetry (recommended)
poetry run pytest

# Run only property-based tests
poetry run pytest -m property

# Run only unit tests
poetry run pytest -m unit

# Run with verbose output
poetry run pytest -v

# Or using pytest directly (if installed globally)
pytest
```

### Run Specific Test File

```bash
# Using Poetry
poetry run pytest test_gitops_controller_health.py

# Run with Hypothesis statistics
poetry run pytest test_gitops_controller_health.py --hypothesis-show-statistics

# Or using pytest directly
pytest test_gitops_controller_health.py
```

### Test Configuration

Tests are configured to run with:

- Minimum 100 iterations per property test (as per design requirements)
- Timeout of 600 seconds for long-running tests
- Detailed logging for debugging

## Property-Based Testing

Property-based tests use [Hypothesis](https://hypothesis.readthedocs.io/) to generate test cases automatically. Each property test:

1. Generates random but valid test inputs
2. Runs the test with those inputs
3. Verifies the property holds for all generated inputs
4. Reports any counterexamples that violate the property

## Test Markers

- `@pytest.mark.property`: Property-based tests
- `@pytest.mark.unit`: Unit tests for specific scenarios
- `@pytest.mark.integration`: Integration tests requiring full cluster
- `@pytest.mark.slow`: Tests that take a long time to run

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Ensure your CI environment has:

1. Access to a Kubernetes cluster (or use kind/k3s for testing)
2. GitOps controllers installed
3. Python 3.9+ with test dependencies

## Troubleshooting

### Connection Issues

If tests fail with connection errors:

```bash
# Verify cluster access
kubectl cluster-info

# Check kubeconfig
echo $KUBECONFIG

# Verify GitOps controllers are running
kubectl get pods -n flux-system
kubectl get pods -n argocd
```

### Test Failures

If property tests fail:

1. Review the counterexample provided by Hypothesis
2. Check if the failure indicates a real bug or a test issue
3. Adjust the test or fix the implementation accordingly

## Adding New Tests

When adding new property-based tests:

1. Follow the existing test structure
2. Use Hypothesis strategies for input generation
3. Configure tests to run minimum 100 iterations
4. Tag tests with appropriate markers
5. Reference the design document property being tested
6. Include validation of requirements in docstrings
