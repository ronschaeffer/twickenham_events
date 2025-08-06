# Developer Setup & Linting Guide

This guide helps you avoid CI linting errors by setting up your development environment correctly.

## 🚀 Quick Setup

1. **Install dependencies:**

   ```bash
   poetry install --with dev
   ```

2. **Install pre-commit hooks:**

   ```bash
   make install-hooks
   ```

3. **Check everything works:**
   ```bash
   make ci-check
   ```

## 🔧 Available Commands

Use these commands to maintain code quality:

| Command         | Description                       | CI Equivalent                |
| --------------- | --------------------------------- | ---------------------------- |
| `make check`    | Run linting checks without fixing | GitHub Actions lint job      |
| `make fix`      | Auto-fix all linting issues       | -                            |
| `make format`   | Format code only                  | -                            |
| `make ci-check` | Run the same checks as CI         | Full GitHub Actions pipeline |
| `make clean`    | Clean cache files                 | -                            |

## 📝 Pre-Commit Workflow

### Before Every Commit:

```bash
make fix  # Auto-fix any issues
make check  # Verify everything is clean
```

### Or use the automated script:

```bash
./scripts/pre-commit-check.sh
```

## 🐛 Troubleshooting CI Failures

### "3 files would be reformatted" Error

This means your local formatting doesn't match CI. Fix it:

```bash
# Fix formatting locally
poetry run ruff format .

# Verify it matches CI expectations
poetry run ruff format --check .
```

### "Found X errors" Error

Run linting fixes:

```bash
# Auto-fix linting errors
poetry run ruff check . --fix

# Check for remaining issues
poetry run ruff check .
```

### Running the Exact Same Checks as CI

```bash
make ci-check
```

This runs the identical commands that CI uses.

## 🛠️ Editor Setup

### VS Code

Your `.vscode/settings.json` is already configured for:

- Auto-formatting on save
- Ruff linting and formatting
- Consistent line endings

### Other Editors

Make sure your editor:

- Uses Ruff for Python formatting and linting
- Trims trailing whitespace
- Adds final newlines
- Uses the config from `pyproject.toml`

## 🔍 Configuration Files

- **`pyproject.toml`** - Ruff configuration (line length, rules, etc.)
- **`.pre-commit-config.yaml`** - Pre-commit hooks
- **`Makefile`** - Convenient commands
- **`.vscode/settings.json`** - VS Code editor settings

## 💡 Pro Tips

1. **Always run `make fix` before committing**
2. **Use `make ci-check` to test locally before pushing**
3. **Enable "Format on Save" in your editor**
4. **Pre-commit hooks will catch most issues automatically**
5. **Check GitHub Actions status for detailed CI feedback**

## 🔗 Related Documentation

- [GitHub Actions CI Configuration](GITHUB_ACTIONS.md) - Detailed CI setup and troubleshooting
- [Home Assistant Development Standards](https://developers.home-assistant.io/) - Coding standards we follow

## 🆘 Still Having Issues?

If you're still getting CI failures:

1. Run `make clean` to clear caches
2. Run `make fix` to fix all issues
3. Run `make ci-check` to verify
4. If it still fails, check if your Poetry version matches CI

The key is ensuring your local environment matches the CI environment exactly!
