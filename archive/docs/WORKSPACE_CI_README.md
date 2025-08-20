# Workspace CI Standards

This repository contains battle-tested CI/CD standards extracted from debugging and fixing multiple CI failures. The goal is to apply these learnings once and propagate them across all projects in your multi-root workspace.

## 🎯 What Problems This Solves

Based on our debugging session, these are the key issues that repeatedly cause CI failures:

1. **Python Version Compatibility**: Modern syntax like `dict | None` breaks on Python 3.9
2. **Poetry Configuration**: Incomplete dependency specifications cause build failures
3. **CI Pipeline Inconsistency**: Different Python versions across projects
4. **Code Quality Variance**: Inconsistent linting/formatting rules

## 🚀 Quick Start

### For Existing Projects

```bash
# Extract working CI standards to another project
./scripts/workspace-ci-manager.sh extract ../my-other-project

# Scan your workspace for all projects
./scripts/workspace-ci-manager.sh scan

# Validate all projects for compliance
./scripts/workspace-ci-manager.sh validate

# Fix Python 3.9 compatibility issues automatically
./scripts/workspace-ci-manager.sh fix-compatibility

# Update all projects with latest standards
./scripts/workspace-ci-manager.sh update-all
```

### For New Projects

```bash
# Create a new project with standards pre-applied
./scripts/workspace-ci-manager.sh new-project my-awesome-service
```

## 📋 Standards Applied

### 1. Python Compatibility (3.9+)
- ✅ Uses `Optional[Dict[str, Any]]` instead of `dict | None`
- ✅ Imports from `typing` module for compatibility
- ✅ Ruff configured with `target-version = "py39"`

### 2. Poetry Configuration
- ✅ Dual dependency format: `[project.dependencies]` + `[tool.poetry.dependencies]`
- ✅ Python version: `python = "^3.9"`
- ✅ Standard dev dependencies: pytest, ruff, pre-commit

### 3. GitHub Actions CI
- ✅ Python matrix: 3.9, 3.10, 3.11, 3.12
- ✅ Poetry workflow with caching
- ✅ Coverage reporting
- ✅ Consistent test commands

### 4. Code Quality
- ✅ Ruff linting with compatibility rules
- ✅ Pre-commit hooks for consistency
- ✅ Automatic formatting
- ✅ Codespell for documentation

## 🔧 Key Configurations

### pyproject.toml Template
```toml
[project]
dependencies = [
    # Sync with [tool.poetry.dependencies]
]

[tool.poetry.dependencies]
python = "^3.9"
# Sync with [project.dependencies]

[tool.ruff]
target-version = "py39"  # Critical for compatibility!
ignore = ["UP006", "UP007", "UP035"]  # Allow older typing syntax
```

### GitHub Actions Matrix
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```

## 💡 Usage Patterns

### Daily Development
```bash
# Before committing (in any project)
poetry run ruff check .
poetry run pytest
pre-commit run --all-files
```

### Adding New Dependencies
```bash
# Add to Poetry
poetry add requests

# Sync to PEP 621 format in pyproject.toml
# [project.dependencies] = ["requests>=2.31.0"]
```

### Monthly Maintenance
```bash
# Validate all projects
./scripts/workspace-ci-manager.sh validate

# Fix any compatibility issues
./scripts/workspace-ci-manager.sh fix-compatibility
```

## 🔍 Troubleshooting

### CI Fails on Python 3.9
```bash
# Common cause: Modern union syntax
# Fix automatically:
./scripts/workspace-ci-manager.sh fix-compatibility

# Or manually replace:
# dict | None  →  Optional[Dict[str, Any]]
# list | None  →  Optional[List[Any]]
```

### Poetry Lock Issues
```bash
# Ensure dependencies are in both sections:
[project.dependencies]
[tool.poetry.dependencies]

# Regenerate lock file:
poetry lock --no-update
```

### Pre-commit Failures
```bash
# Run locally to fix issues:
pre-commit run --all-files

# Update hooks:
pre-commit autoupdate
```

## 📚 Documentation

- [Complete Multi-Project Strategy](docs/MULTIPROJECT_CI_STRATEGY.md)
- [Migration Guide](CI_MIGRATION_GUIDE.md) (created when extracting to projects)

## 🎯 Benefits

1. **One-Time Fix**: Debug CI issues once, apply everywhere
2. **Consistency**: All projects follow same standards
3. **Reliability**: Proven configurations that actually work
4. **Efficiency**: Automated tools for propagation and maintenance
5. **Flexibility**: Project-specific overrides when needed

## 🤝 Contributing

When you discover new CI issues or improvements:

1. Fix them in one project first
2. Update the templates in this repository
3. Propagate to all projects: `./scripts/workspace-ci-manager.sh update-all`
4. Update documentation

This ensures the entire workspace benefits from every debugging session!
