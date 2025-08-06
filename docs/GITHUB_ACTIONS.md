# GitHub Actions CI Configuration

This document explains the GitHub Actions workflows and their consistency with local development.

## 📋 Workflow Overview

### 1. **ci.yml** - Main CI Pipeline

- **Purpose**: Core continuous integration checks
- **Triggers**: Push to main/develop, Pull requests
- **Jobs**:
  - `lint`: Ruff linting and formatting checks (Python 3.11)
  - `test`: Full test suite across Python 3.9-3.12

### 2. **code-quality.yml** - Comprehensive Quality Checks

- **Purpose**: Detailed code analysis and pre-commit validation
- **Triggers**: Push to main/develop, Pull requests
- **Jobs**:
  - `pre-commit`: Runs all pre-commit hooks
  - `ruff-detailed`: Advanced Ruff analysis with statistics and security checks

### 3. **local-consistency.yml** - Development Environment Validation

- **Purpose**: Ensures CI matches local `make` commands exactly
- **Triggers**: Pull requests only
- **Jobs**:
  - `makefile-consistency`: Tests `make check` and `make ci-check` commands
  - Verifies `make fix` produces no changes (enforces pre-commit formatting)

### 4. **pr-summary.yml** - Pull Request Status Dashboard

- **Purpose**: Provides clear PR status and developer guidance
- **Triggers**: Pull requests only
- **Features**:
  - Summary report in GitHub UI
  - Code statistics and quality metrics
  - Clear instructions for fixing issues locally

## 🔄 Local vs CI Consistency

### Exact Command Matching

| Local Command                | CI Equivalent                                                 | GitHub Workflow         |
| ---------------------------- | ------------------------------------------------------------- | ----------------------- |
| `make check`                 | `poetry run ruff check . && poetry run ruff format --check .` | `ci.yml` lint job       |
| `make ci-check`              | Full lint + test suite                                        | `ci.yml` both jobs      |
| `make fix`                   | Auto-fix validation                                           | `local-consistency.yml` |
| `pre-commit run --all-files` | Pre-commit validation                                         | `code-quality.yml`      |

### Version Consistency

- **Ruff**: Pinned to `^0.12.0` in `pyproject.toml` (compatible with system 0.12.7)
- **Python**: Primary version 3.11 for consistency checks
- **Poetry**: Latest version across all workflows

## 🛠️ Developer Workflow

### Before Pushing Changes:

```bash
make fix        # Auto-fix all issues
make ci-check   # Run exact CI checks locally
```

### If CI Fails:

1. Check the **PR Summary** workflow for detailed feedback
2. Run `make fix` locally to auto-resolve most issues
3. For complex issues, check specific workflow logs:
   - **Linting issues**: Check `ci.yml` lint job
   - **Test failures**: Check `ci.yml` test job
   - **Pre-commit issues**: Check `code-quality.yml`

### Status Checks Required for Merge:

- ✅ **CI / Lint & Format Check**
- ✅ **CI / Test Suite** (Python 3.11)
- ✅ **Code Quality / Pre-commit Checks**
- ✅ **Local Development Consistency / Verify Makefile Commands**

## 🎯 Home Assistant Compatibility

All workflows use the **Home Assistant-compatible Ruff configuration**:

- **Security checks**: S102, S103, S307
- **Code quality**: Complexity limits, proper logging
- **Modern Python**: f-strings, type hints, proper imports
- **Testing standards**: Pytest best practices

## 🚨 Troubleshooting

### "Files were modified by make fix"

- **Cause**: Code not properly formatted before commit
- **Solution**: Run `make fix` locally and commit changes

### "Ruff version mismatch"

- **Cause**: Local ruff version differs from CI
- **Solution**: Run `poetry install --with dev` to sync versions

### "Pre-commit hook failures"

- **Cause**: Pre-commit hooks not installed or bypassed
- **Solution**: Run `make install-hooks` and ensure hooks run

## 📊 Quality Metrics

The CI tracks these quality indicators:

- **Linting errors**: Zero tolerance policy
- **Code formatting**: Consistent with Black/Ruff standards
- **Test coverage**: Tracked via pytest-cov
- **Security issues**: Detected via Ruff security rules
- **Complexity**: Monitored but not enforced strictly

All metrics align with Home Assistant development standards while remaining practical for this project's scope.
