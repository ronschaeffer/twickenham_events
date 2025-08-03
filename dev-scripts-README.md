# Python Multi-Project Development Scripts

This directory contains development automation scripts for the Python multi-project workspace.

## Available Scripts

### 🧪 `run-all-tests.sh`

**Alias:** `dev-test` (if sourced in shell)

Runs pytest for all projects in the workspace. Each project uses its own virtual environment.

```bash
./run-all-tests.sh
# or with alias:
dev-test
```

### 🎨 `format-all.sh`

**Alias:** `dev-format` (if sourced in shell)

Formats all Python code using Ruff for all projects. Runs both `ruff check --fix` and `ruff format`.

```bash
./format-all.sh
# or with alias:
dev-format
```

### 📊 `project-status.sh`

**Alias:** `dev-status` (if sourced in shell)

Shows comprehensive status information for all projects including:

- Python environment details
- Installed packages (Ruff, PyTest, etc.)
- Git status
- Configuration files status
- Workspace configuration

```bash
./project-status.sh
# or with alias:
dev-status
```

### 🚀 `new-project.sh`

**Alias:** `new-project` (if sourced in shell)

Creates a new Python project with standard structure including:

- Directory structure (src/, tests/, docs/, config/)
- pyproject.toml with modern Python packaging
- VS Code settings configured for Ruff
- Git repository initialization
- Basic .gitignore
- Sample code and tests

```bash
./new-project.sh my_awesome_project
# or with alias:
new-project my_awesome_project
```

## Quick Setup

To enable shell aliases, add these lines to your `~/.zshrc`:

```bash
# Development Scripts Aliases
alias dev-test="/home/ron/projects/.dev-scripts/run-all-tests.sh"
alias dev-format="/home/ron/projects/.dev-scripts/format-all.sh"
alias dev-status="/home/ron/projects/.dev-scripts/project-status.sh"
alias new-project="/home/ron/projects/.dev-scripts/new-project.sh"
```

Then reload your shell:

```bash
source ~/.zshrc
```

## Features

- ✅ **Multi-project aware**: Works with the entire workspace
- ✅ **Virtual environment detection**: Automatically uses each project's .venv
- ✅ **Colorized output**: Easy to read status and results
- ✅ **Error handling**: Graceful handling of missing dependencies or projects
- ✅ **Standardized**: Consistent structure across all scripts

## Integration

These scripts integrate seamlessly with:

- VS Code Python extension
- Ruff formatter and linter
- PyTest testing framework
- Git version control
- Poetry/pip package management

## Development Environment

Current workspace supports:

- **Twickenham Events**: Event processing and MQTT publishing
- **MQTT Publisher**: Generic MQTT publishing library
- **Future projects**: Easily add new projects to the workspace

---

Happy coding! 🐍✨
