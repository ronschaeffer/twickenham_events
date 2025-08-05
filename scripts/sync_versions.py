#!/usr/bin/env python3
"""
Universal Version Synchronization Script

This script ensures version consistency across all project files:
- pyproject.toml (source of truth)
- __init__.py files
- Home Assistant device definitions
- Documentation files

Usage:
    python scripts/sync_versions.py
    python scripts/sync_versions.py --check  # Check only, don't update
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys


class VersionSync:
    """Universal version synchronization for Python projects."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.version = self._get_pyproject_version()
        self.git_version = self._get_git_version()

    def _get_pyproject_version(self) -> str:
        """Get version from pyproject.toml (source of truth)."""
        if not self.pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found in {self.project_root}")

        content = self.pyproject_path.read_text()

        # Try Poetry format first: version = "x.y.z"
        match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)

        # Try PEP 621 format: version = "x.y.z"
        match = re.search(r'^\[project\].*?^version = "([^"]+)"', content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1)

        raise ValueError("Version not found in pyproject.toml")

    def _get_git_version(self) -> str:
        """Get git-based version for development builds."""
        try:
            # Get short commit hash
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                stderr=subprocess.DEVNULL,
            ).decode().strip()

            # Check if dirty (uncommitted changes)
            try:
                subprocess.check_output(
                    ["git", "diff-index", "--quiet", "HEAD", "--"],
                    cwd=self.project_root,
                    stderr=subprocess.DEVNULL,
                )
                dirty = ""
            except subprocess.CalledProcessError:
                dirty = "-dirty"

            return f"{self.version}-{git_hash}{dirty}"

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback if not in git repo
            return self.version

    def find_init_files(self) -> list[Path]:
        """Find all __init__.py files that should have version."""
        init_files = []

        # Look in src/ directory (modern layout)
        src_dir = self.project_root / "src"
        if src_dir.exists():
            for init_file in src_dir.rglob("__init__.py"):
                # Only update main package __init__.py files
                if init_file.parent.name != "__pycache__":
                    init_files.append(init_file)

        # Look in direct package directories (legacy layout)
        for path in self.project_root.iterdir():
            if path.is_dir() and not path.name.startswith('.') and path.name not in ['src', 'tests', 'docs']:
                init_file = path / "__init__.py"
                if init_file.exists():
                    init_files.append(init_file)

        return init_files

    def find_ha_config_files(self) -> list[Path]:
        """Find Home Assistant configuration files with device versions."""
        ha_files = []

        # Common HA config file patterns
        patterns = [
            "config/ha_entities.yaml",
            "config/ha_*.yaml",
            "ha_card/*.yaml",
        ]

        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                # Skip files in .venv, .git, __pycache__ etc
                if not any(part.startswith('.') for part in file_path.parts):
                    ha_files.extend([file_path])

        # Also look for Python files with device definitions
        for py_file in self.project_root.rglob("*.py"):
            # Skip sync_versions.py to prevent self-modification
            if py_file.name == "sync_versions.py":
                continue
            if not any(part.startswith('.') for part in py_file.parts):
                if any(keyword in py_file.read_text() for keyword in ["sw_version", "device_version"]):
                    ha_files.append(py_file)

        return list(set(ha_files))  # Remove duplicates

    def update_init_file(self, init_path: Path, check_only: bool = False) -> bool:
        """Update version in __init__.py file."""
        if not init_path.exists():
            return False

        # Skip sync_versions.py to prevent self-modification
        if init_path.name == "sync_versions.py":
            return False

        content = init_path.read_text()

        # Pattern to match __version__ = "x.y.z"
        version_pattern = r'^__version__ = ["\'][^"\']*["\']'

        if not re.search(version_pattern, content, re.MULTILINE):
            # No version found, skip
            return False

        new_content = re.sub(
            version_pattern,
            f'__version__ = "{self.version}"',
            content,
            flags=re.MULTILINE
        )

        if content != new_content:
            if not check_only:
                init_path.write_text(new_content)
                print(f"✅ Updated {init_path.relative_to(self.project_root)}: {self.version}")
            else:
                print(f"⚠️  Version mismatch in {init_path.relative_to(self.project_root)}")
            return True

        return False

    def update_ha_config_file(self, ha_path: Path, check_only: bool = False) -> bool:
        """Update sw_version in Home Assistant config files."""
        if not ha_path.exists():
            return False

        try:
            content = ha_path.read_text()
        except UnicodeDecodeError:
            # Skip binary files
            return False

        # Pattern to match sw_version: "x.y.z" or sw_version="x.y.z"
        sw_version_patterns = [
            r'(\s*sw_version:\s*)["\']?[^"\'\n]*["\']?',  # YAML format
            r'(sw_version\s*=\s*)["\'][^"\']*["\']',      # Python format
        ]

        updated = False
        new_content = content

        for pattern in sw_version_patterns:
            if re.search(pattern, content):
                if ha_path.suffix in ['.yaml', '.yml']:
                    replacement = rf'\1"{self.version}"'
                else:
                    replacement = rf'\1"{self.version}"'
                new_content = re.sub(pattern, replacement, new_content)
                updated = True
                break

        if updated and content != new_content:
            if not check_only:
                ha_path.write_text(new_content)
                print(f"✅ Updated {ha_path.relative_to(self.project_root)}: {self.git_version}")
            else:
                print(f"⚠️  HA version mismatch in {ha_path.relative_to(self.project_root)}")
            return True

        return False

    def sync_all(self, check_only: bool = False) -> dict[str, int]:
        """Synchronize versions in all relevant files."""
        results = {
            'init_files': 0,
            'ha_files': 0,
            'errors': 0
        }

        print(f"🔄 {'Checking' if check_only else 'Syncing'} versions from pyproject.toml: {self.version}")
        print(f"🔄 Git version: {self.git_version}")
        print()

        # Update __init__.py files
        for init_file in self.find_init_files():
            try:
                if self.update_init_file(init_file, check_only):
                    results['init_files'] += 1
            except Exception as e:
                print(f"❌ Error updating {init_file}: {e}")
                results['errors'] += 1

        # Update HA config files
        for ha_file in self.find_ha_config_files():
            try:
                if self.update_ha_config_file(ha_file, check_only):
                    results['ha_files'] += 1
            except Exception as e:
                print(f"❌ Error updating {ha_file}: {e}")
                results['errors'] += 1

        return results


def main():
    parser = argparse.ArgumentParser(description='Sync versions across project files')
    parser.add_argument('--check', action='store_true', help='Check only, do not update')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(), help='Project root directory')

    args = parser.parse_args()

    try:
        sync = VersionSync(args.project_root)
        results = sync.sync_all(check_only=args.check)

        print()
        if args.check:
            if results['init_files'] + results['ha_files'] + results['errors'] == 0:
                print("✅ All versions are synchronized!")
            else:
                print(f"⚠️  Found {results['init_files'] + results['ha_files']} version mismatches")
                if results['errors'] > 0:
                    print(f"❌ {results['errors']} errors occurred")
                sys.exit(1)
        else:
            print(f"✅ Updated {results['init_files']} __init__.py files")
            print(f"✅ Updated {results['ha_files']} HA config files")
            if results['errors'] > 0:
                print(f"❌ {results['errors']} errors occurred")
                sys.exit(1)
            print("🎉 Version synchronization complete!")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
