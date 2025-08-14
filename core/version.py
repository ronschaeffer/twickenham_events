#!/usr/bin/env python3
"""
Utility to get dynamic version information for Home Assistant device registration.
"""

from pathlib import Path
import subprocess


def get_git_version() -> str:
    """Get version string based on Git commit hash, prefixed by project version.

    Example outputs:
    - <project_version>-<hash>
    - <project_version>-<hash>-dirty
    - <project_version>-dev (when git is unavailable)
    """
    base_version = get_project_version()
    try:
        # Get the short commit hash
        git_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=Path(__file__).parent.parent,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        # Check if there are uncommitted changes
        try:
            subprocess.check_output(
                ["git", "diff-index", "--quiet", "HEAD", "--"],
                cwd=Path(__file__).parent.parent,
                stderr=subprocess.DEVNULL,
            )
            # No uncommitted changes
            return f"{base_version}-{git_hash}"
        except subprocess.CalledProcessError:
            # Uncommitted changes detected
            return f"{base_version}-{git_hash}-dirty"

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not a git repository
        return f"{base_version}-dev"


def get_project_version() -> str:
    """Get version from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        # Python < 3.11, use toml package
        try:
            import toml as tomllib
        except ImportError:
            return "0.1.0"

    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (FileNotFoundError, KeyError):
        return "0.1.0"


def get_dynamic_version() -> str:
    """Get the best available version string."""
    # Prefer Git-based versioning for development tracking
    git_version = get_git_version()
    if not git_version.endswith("-dev"):
        return git_version

    # Fallback to project version
    return get_project_version()


if __name__ == "__main__":
    print(get_dynamic_version())
