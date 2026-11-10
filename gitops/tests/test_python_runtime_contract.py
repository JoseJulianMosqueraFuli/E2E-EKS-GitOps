import re
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "filename", ["Dockerfile", "Dockerfile.monitoring", "Dockerfile.mlflow-server"]
)
def test_python_image_matches_project_and_ml_ci(filename):
    project = tomllib.loads((ROOT / "ml-platform/pyproject.toml").read_text())
    supported = SpecifierSet(project["project"]["requires-python"])
    dockerfile = (ROOT / "ml-platform" / filename).read_text()
    versions = re.findall(r"^FROM python:(\d+\.\d+\.\d+)-", dockerfile, re.MULTILINE)
    assert versions, f"{filename} must pin a Python patch version"

    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    setup = next(
        step
        for step in workflow["jobs"]["ml-platform-test"]["steps"]
        if step.get("uses", "").startswith("actions/setup-python@")
    )
    ci_version = Version(setup["with"]["python-version"])
    for version in versions:
        image_version = Version(version)
        assert image_version in supported, f"{filename}: {version} outside {supported}"
        assert image_version == ci_version, f"{filename}: image and ML CI Python versions differ"
