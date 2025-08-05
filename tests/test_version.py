"""Tests for version functionality."""

import subprocess
from unittest.mock import patch

import pytest

from core.version import get_dynamic_version, get_git_version, get_project_version


def test_get_project_version():
    """Test that project version can be read from pyproject.toml."""
    version = get_project_version()
    assert version == "0.1.0"


def test_get_git_version_success():
    """Test Git version when Git is available."""
    # This test will only pass if we're in a Git repo
    try:
        git_version = get_git_version()
        # Should be in format: 0.1.0-<hash> or 0.1.0-<hash>-dirty
        assert git_version.startswith("0.1.0-")
        assert len(git_version.split("-")) >= 2
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # If Git is not available, should fallback
        pytest.skip("Git not available in test environment")


@patch("subprocess.check_output", side_effect=FileNotFoundError("git not found"))
def test_get_git_version_no_git(mock_subprocess):
    """Test Git version fallback when Git is not available."""
    git_version = get_git_version()
    assert git_version == "0.1.0-dev"


@patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git"))
def test_get_git_version_git_error(mock_subprocess):
    """Test Git version fallback when Git command fails."""
    git_version = get_git_version()
    assert git_version == "0.1.0-dev"


def test_get_dynamic_version():
    """Test dynamic version selection logic."""
    version = get_dynamic_version()
    # Should be either Git-based or project version
    assert version.startswith("0.1.0")


@patch("subprocess.check_output", side_effect=FileNotFoundError("git not found"))
def test_get_dynamic_version_fallback(mock_subprocess):
    """Test dynamic version falls back to project version when Git fails."""
    version = get_dynamic_version()
    assert version == "0.1.0"


def test_get_dynamic_version_format():
    """Test that dynamic version has expected format."""
    version = get_dynamic_version()

    # Should be one of these formats:
    # - 0.1.0 (project version)
    # - 0.1.0-dev (git unavailable)
    # - 0.1.0-<hash> (clean git)
    # - 0.1.0-<hash>-dirty (dirty git)

    assert version.startswith("0.1.0")
    if "-" in version:
        parts = version.split("-")
        assert len(parts) >= 2
        if len(parts) == 2:
            # Either 0.1.0-dev or 0.1.0-<hash>
            assert parts[1] in ["dev"] or len(parts[1]) == 7  # Git short hash
        elif len(parts) == 3:
            # 0.1.0-<hash>-dirty
            assert len(parts[1]) == 7  # Git short hash
            assert parts[2] == "dirty"
