# Multi-Project CI Strategy & Standards

## Overview
This document outlines the standardized CI/CD approach for all projects in the workspace, based on lessons learned from the `twickenham_events` project CI debugging session.

## Key Issues Solved

### 1. **Python Version Compatibility**
- **Problem**: Modern Python syntax (e.g., `dict | None`) breaks CI on older Python versions
- **Solution**: Enforce Python 3.9+ compatible syntax across all projects
- **Standard**: Use `Optional[Dict[str, Any]]` instead of `dict | None`

### 2. **Poetry Configuration Consistency**
- **Problem**: Incomplete dependency specifications cause CI failures
- **Solution**: Dual dependency format for PEP 621 + Poetry compatibility
- **Standard**: Both `[project.dependencies]` and `[tool.poetry.dependencies]`

### 3. **CI Pipeline Standardization**
- **Problem**: Different Python version matrices across projects
- **Solution**: Standardized GitHub Actions workflows
- **Standard**: Python 3.9-3.12 matrix testing

### 4. **Code Quality Consistency**
- **Problem**: Different linting/formatting rules per project
- **Solution**: Shared configuration templates
- **Standard**: Common ruff + pre-commit configuration

## Implementation Strategy

### Phase 1: Workspace-Level Standards

#### A. Shared Configuration Repository
```
workspace-config/
├── templates/
│   ├── pyproject.toml.template
│   ├── .pre-commit-config.yaml.template
│   ├── .github/
│   │   └── workflows/
│   │       ├── ci.yml.template
│   │       └── code-quality.yml.template
│   └── ruff.toml.template
├── scripts/
│   ├── apply-standards.sh
│   ├── update-all-projects.sh
│   └── validate-compliance.sh
└── standards/
    ├── python-compatibility.md
    ├── dependency-management.md
    └── ci-requirements.md
```

#### B. Standardized Templates

**pyproject.toml.template**:
```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[project]
name = "{{PROJECT_NAME}}"
version = "{{VERSION}}"
description = "{{DESCRIPTION}}"
dependencies = [
    # Sync with [tool.poetry.dependencies]
    {{PROJECT_DEPENDENCIES}}
]

[tool.poetry]
name = "{{PROJECT_NAME}}"
version = "{{VERSION}}"
description = "{{DESCRIPTION}}"

[tool.poetry.dependencies]
python = "^3.9"
# Sync with [project.dependencies]
{{PROJECT_DEPENDENCIES}}

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-cov = "^4.0.0"
ruff = "^0.6.0"
pre-commit = "^3.5.0"

[tool.ruff]
target-version = "py39"  # Enforce Python 3.9+ compatibility
line-length = 88
select = ["E", "F", "W", "C", "I", "N", "UP"]
ignore = ["UP006", "UP007", "UP035"]  # Allow older typing syntax

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov={{PROJECT_NAME}}",
    "--cov-report=term-missing",
    "--cov-report=xml",
    "--tb=short"
]
```

**ci.yml.template**:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        virtualenvs-create: true
        virtualenvs-in-project: true

    - name: Install dependencies
      run: poetry install --with dev

    - name: Run tests
      run: |
        poetry run pytest --cov --cov-report=xml --cov-report=term-missing

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      if: matrix.python-version == '3.11'
```

#### C. Management Scripts

**apply-standards.sh**:
```bash
#!/bin/bash
# Apply workspace standards to a specific project

PROJECT_PATH=$1
if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <project-path>"
    exit 1
fi

echo "🔧 Applying workspace standards to $PROJECT_PATH..."

# Backup existing configurations
mkdir -p "$PROJECT_PATH/.backup"
cp "$PROJECT_PATH/pyproject.toml" "$PROJECT_PATH/.backup/" 2>/dev/null || true
cp "$PROJECT_PATH/.pre-commit-config.yaml" "$PROJECT_PATH/.backup/" 2>/dev/null || true

# Apply templates with project-specific substitutions
PROJECT_NAME=$(basename "$PROJECT_PATH")
sed "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" templates/pyproject.toml.template > "$PROJECT_PATH/pyproject.toml.new"

# Merge with existing project-specific settings
echo "📋 Manual review required for: $PROJECT_PATH/pyproject.toml.new"
echo "   Compare with existing configuration and merge manually"

# Apply GitHub Actions workflows
mkdir -p "$PROJECT_PATH/.github/workflows"
cp templates/.github/workflows/*.template "$PROJECT_PATH/.github/workflows/"
rename 's/\.template$//' "$PROJECT_PATH/.github/workflows/"*.template

echo "✅ Standards applied to $PROJECT_PATH"
```

**update-all-projects.sh**:
```bash
#!/bin/bash
# Update all projects in workspace with latest standards

WORKSPACE_ROOT=$(pwd)
PROJECTS_FILE="projects.list"

if [ ! -f "$PROJECTS_FILE" ]; then
    echo "📝 Creating projects list..."
    find . -name "pyproject.toml" -not -path "./workspace-config/*" | dirname > "$PROJECTS_FILE"
fi

echo "🚀 Updating all projects with latest standards..."

while read -r project; do
    echo "Processing: $project"
    ./scripts/apply-standards.sh "$project"
done < "$PROJECTS_FILE"

echo "✅ All projects updated"
```

### Phase 2: New Project Integration

#### Enhanced new-project Script

```bash
#!/bin/bash
# Enhanced new-project script with workspace standards

PROJECT_NAME=$1
PROJECT_TYPE=${2:-"python-project"}

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <project-name> [project-type]"
    echo "Types: python-project, mcp-server, vscode-extension, next-js, vite"
    exit 1
fi

echo "🏗️  Creating new project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Initialize with workspace standards
echo "📋 Applying workspace standards..."
../workspace-config/scripts/apply-standards.sh "$(pwd)"

# Project-type specific setup
case $PROJECT_TYPE in
    "python-project"|"mcp-server")
        poetry init --no-interaction --name "$PROJECT_NAME" --dependency python="^3.9"
        mkdir -p src tests
        ;;
    "vscode-extension")
        npm init -y
        mkdir -p src out
        ;;
    # ... other types
esac

# Initialize git and pre-commit
git init
pre-commit install

echo "✅ Project $PROJECT_NAME created with workspace standards"
```

### Phase 3: Continuous Compliance

#### Validation Script

**validate-compliance.sh**:
```bash
#!/bin/bash
# Validate all projects comply with workspace standards

ISSUES_FOUND=0

echo "🔍 Validating workspace compliance..."

for project in $(cat projects.list); do
    echo "Checking: $project"

    # Check Python version compatibility
    if grep -r "dict\s*|\s*\w" "$project"/*.py 2>/dev/null; then
        echo "❌ $project: Found Python 3.10+ union syntax"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi

    # Check pyproject.toml has both dependency formats
    if [ -f "$project/pyproject.toml" ]; then
        if ! grep -q "\[project.dependencies\]" "$project/pyproject.toml"; then
            echo "❌ $project: Missing [project.dependencies]"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        if ! grep -q "\[tool.poetry.dependencies\]" "$project/pyproject.toml"; then
            echo "❌ $project: Missing [tool.poetry.dependencies]"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi

    # Check CI workflow exists
    if [ ! -f "$project/.github/workflows/ci.yml" ]; then
        echo "❌ $project: Missing CI workflow"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done

if [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅ All projects compliant with workspace standards"
else
    echo "❌ Found $ISSUES_FOUND compliance issues"
    exit 1
fi
```

### Phase 4: Project-Specific Overrides

#### Override System

**project-overrides.yaml**:
```yaml
# Per-project customizations
projects:
  twickenham_events:
    python_versions: ["3.9", "3.10", "3.11", "3.12"]
    additional_dependencies:
      - "beautifulsoup4"
      - "requests"
    custom_ci_steps:
      - name: "Test specific functionality"
        run: "poetry run python -m core.twick_event --version"

  another_project:
    python_versions: ["3.10", "3.11", "3.12"]  # Override: no 3.9 support
    ruff_overrides:
      line-length: 100
```

#### Override Application Script

**apply-overrides.sh**:
```bash
#!/bin/bash
# Apply project-specific overrides

PROJECT_PATH=$1
PROJECT_NAME=$(basename "$PROJECT_PATH")

if yq eval ".projects.${PROJECT_NAME}" project-overrides.yaml > /dev/null 2>&1; then
    echo "📝 Applying overrides for $PROJECT_NAME..."

    # Apply Python version overrides
    PYTHON_VERSIONS=$(yq eval ".projects.${PROJECT_NAME}.python_versions" project-overrides.yaml)
    if [ "$PYTHON_VERSIONS" != "null" ]; then
        # Update CI workflow with custom Python versions
        echo "🐍 Custom Python versions: $PYTHON_VERSIONS"
    fi

    # Apply other overrides...
fi
```

## Implementation Timeline

### Week 1: Foundation
1. Create `workspace-config` repository
2. Develop standard templates
3. Create management scripts

### Week 2: Migration
1. Inventory existing projects
2. Apply standards to each project
3. Test CI pipelines

### Week 3: Automation
1. Integrate with new-project script
2. Set up compliance validation
3. Create override system

### Week 4: Documentation & Training
1. Document processes
2. Create troubleshooting guides
3. Train team on new workflows

## Benefits

1. **Consistency**: All projects follow same standards
2. **Efficiency**: Fix once, apply everywhere
3. **Maintainability**: Central updates propagate to all projects
4. **Quality**: Standardized CI/CD prevents issues
5. **Flexibility**: Project-specific overrides where needed

## Monitoring & Updates

- **Weekly**: Run compliance validation
- **Monthly**: Review and update standards
- **Per Release**: Update all projects with latest templates
- **As Needed**: Apply urgent fixes workspace-wide

This approach ensures that the debugging effort from `twickenham_events` benefits all current and future projects in your workspace.
