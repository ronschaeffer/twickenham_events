"""Tests for version functionality."""

from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from core.version import get_dynamic_version, get_git_version, get_project_version


def _read_pyproject_version() -> str:
    """Read version directly from pyproject.toml for ground-truth in tests."""
    try:
        import tomllib
    except ImportError:  # pragma: no cover - Python < 3.11
        import toml as tomllib  # type: ignore[no-redef]

    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def test_get_project_version():
    """Test that project version can be read from pyproject.toml."""
    version = get_project_version()
    assert version == _read_pyproject_version()


def test_get_git_version_success():
    """Test Git version when Git is available."""
    # This test will only pass if we're in a Git repo
    try:
        git_version = get_git_version()
        # Should be in format: <base>-<hash> or <base>-<hash>-dirty
        base = _read_pyproject_version()
        assert git_version.startswith(f"{base}-")
        assert len(git_version.split("-")) >= 2
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # If Git is not available, should fallback
        pytest.skip("Git not available in test environment")


@patch("subprocess.check_output", side_effect=FileNotFoundError("git not found"))
def test_get_git_version_no_git(mock_subprocess):
    """Test Git version fallback when Git is not available."""
    git_version = get_git_version()
    assert git_version == f"{_read_pyproject_version()}-dev"


@patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git"))
def test_get_git_version_git_error(mock_subprocess):
    """Test Git version fallback when Git command fails."""
    git_version = get_git_version()
    assert git_version == f"{_read_pyproject_version()}-dev"


def test_get_dynamic_version():
    """Test dynamic version selection logic."""
    version = get_dynamic_version()
    # Should be either Git-based or project version
    assert version.startswith(_read_pyproject_version())


@patch("subprocess.check_output", side_effect=FileNotFoundError("git not found"))
def test_get_dynamic_version_fallback(mock_subprocess):
    """Test dynamic version falls back to project version when Git fails."""
    version = get_dynamic_version()
    assert version == _read_pyproject_version()


def test_get_dynamic_version_format():
    """Test that dynamic version has expected format."""
    version = get_dynamic_version()

    # Should be one of these formats:
    # - <base> (project version)
    # - <base>-dev (git unavailable)
    # - <base>-<hash> (clean git)
    # - <base>-<hash>-dirty (dirty git)

    base = _read_pyproject_version()
    assert version.startswith(base)
    if "-" in version:
        parts = version.split("-")
        assert len(parts) >= 2
        if len(parts) == 2:
            # Either <base>-dev or <base>-<hash>
            assert parts[1] in ["dev"] or len(parts[1]) == 7  # Git short hash
        elif len(parts) == 3:
            # <base>-<hash>-dirty
            assert len(parts[1]) == 7  # Git short hash
            assert parts[2] == "dirty"
