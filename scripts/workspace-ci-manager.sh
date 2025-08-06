#!/bin/bash
# Workspace CI Standards Manager
# Manages CI standards across all projects in a multi-root workspace

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname "$SCRIPT_DIR")"
COMMAND="$1"
TARGET="$2"

show_help() {
    cat << EOF
Workspace CI Standards Manager

USAGE:
    $0 <command> [target]

COMMANDS:
    extract <project-path>     Extract CI standards from twickenham_events to target project
    scan                       Scan workspace for all projects
    validate                   Validate all projects for CI compliance
    update-all                 Update all projects with latest standards
    new-project <name>         Create new project with standards applied
    fix-compatibility          Fix Python 3.9 compatibility issues in all projects

EXAMPLES:
    $0 extract ../my-other-project
    $0 scan
    $0 validate
    $0 update-all
    $0 new-project my-new-service
    $0 fix-compatibility

EOF
}

scan_workspace() {
    echo "🔍 Scanning workspace for projects..."
    echo ""

    # Find all projects with pyproject.toml
    PROJECTS_FILE="$WORKSPACE_ROOT/.workspace-projects.list"
    find "$WORKSPACE_ROOT" -name "pyproject.toml" -not -path "*/node_modules/*" -not -path "*/.venv/*" | \
        xargs dirname | \
        sort > "$PROJECTS_FILE"

    echo "📁 Found $(wc -l < "$PROJECTS_FILE") projects:"
    while read -r project; do
        PROJECT_NAME=$(basename "$project")
        RELATIVE_PATH=$(realpath --relative-to="$WORKSPACE_ROOT" "$project")
        echo "  • $PROJECT_NAME ($RELATIVE_PATH)"
    done < "$PROJECTS_FILE"

    echo ""
    echo "📝 Project list saved to: $PROJECTS_FILE"
}

validate_compliance() {
    echo "🔍 Validating CI compliance across workspace..."
    echo ""

    PROJECTS_FILE="$WORKSPACE_ROOT/.workspace-projects.list"
    if [ ! -f "$PROJECTS_FILE" ]; then
        echo "📁 No project list found. Running scan first..."
        scan_workspace
    fi

    ISSUES_FOUND=0
    TOTAL_PROJECTS=0

    while read -r project; do
        TOTAL_PROJECTS=$((TOTAL_PROJECTS + 1))
        PROJECT_NAME=$(basename "$project")
        echo "🔍 Checking: $PROJECT_NAME"

        # Check 1: Python 3.10+ union syntax
        if find "$project" -name "*.py" -exec grep -l ":\s*\w*\s*|\s*\w*\s*=" {} \; 2>/dev/null | head -1 > /dev/null; then
            echo "  ❌ Found Python 3.10+ union syntax (dict | None)"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi

        # Check 2: pyproject.toml dual dependencies
        if [ -f "$project/pyproject.toml" ]; then
            HAS_PROJECT_DEPS=$(grep -c "\\[project.dependencies\\]" "$project/pyproject.toml" || echo "0")
            HAS_POETRY_DEPS=$(grep -c "\\[tool.poetry.dependencies\\]" "$project/pyproject.toml" || echo "0")

            if [ "$HAS_PROJECT_DEPS" -eq 0 ]; then
                echo "  ❌ Missing [project.dependencies] section"
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            fi
            if [ "$HAS_POETRY_DEPS" -eq 0 ]; then
                echo "  ❌ Missing [tool.poetry.dependencies] section"
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            fi

            # Check 3: Python version compatibility
            if ! grep -q 'python = "\\^3.9"' "$project/pyproject.toml"; then
                echo "  ⚠️  Python version may not be 3.9+ compatible"
            fi

            # Check 4: Ruff target version
            if ! grep -q 'target-version = "py39"' "$project/pyproject.toml"; then
                echo "  ⚠️  Ruff target-version not set to py39"
            fi
        fi

        # Check 5: CI workflow
        if [ ! -f "$project/.github/workflows/ci.yml" ]; then
            echo "  ❌ Missing CI workflow"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi

        # Check 6: Pre-commit configuration
        if [ ! -f "$project/.pre-commit-config.yaml" ]; then
            echo "  ⚠️  Missing pre-commit configuration"
        fi

        echo "  ✅ Validation complete"
        echo ""
    done < "$PROJECTS_FILE"

    echo "📊 VALIDATION SUMMARY"
    echo "===================="
    echo "Projects checked: $TOTAL_PROJECTS"
    echo "Issues found: $ISSUES_FOUND"

    if [ $ISSUES_FOUND -eq 0 ]; then
        echo "✅ All projects are compliant!"
        return 0
    else
        echo "❌ Compliance issues found. Run 'update-all' or 'fix-compatibility' to resolve."
        return 1
    fi
}

fix_compatibility() {
    echo "🔧 Fixing Python 3.9 compatibility issues across workspace..."
    echo ""

    PROJECTS_FILE="$WORKSPACE_ROOT/.workspace-projects.list"
    if [ ! -f "$PROJECTS_FILE" ]; then
        echo "📁 No project list found. Running scan first..."
        scan_workspace
    fi

    while read -r project; do
        PROJECT_NAME=$(basename "$project")
        echo "🔧 Processing: $PROJECT_NAME"

        # Find Python files with union syntax
        UNION_FILES=$(find "$project" -name "*.py" -exec grep -l ":\s*\w*\s*|\s*\w*\s*=" {} \; 2>/dev/null || true)

        if [ -n "$UNION_FILES" ]; then
            echo "  📝 Found files with union syntax:"
            echo "$UNION_FILES" | while read -r file; do
                echo "    • $(basename "$file")"
                # Create backup
                cp "$file" "$file.backup"

                # Fix common patterns
                sed -i 's/: dict | None/: Optional[Dict[str, Any]]/g' "$file"
                sed -i 's/: list | None/: Optional[List[Any]]/g' "$file"
                sed -i 's/: str | None/: Optional[str]/g' "$file"
                sed -i 's/-> dict | None/-> Optional[Dict[str, Any]]/g' "$file"
                sed -i 's/-> list | None/-> Optional[List[Any]]/g' "$file"
                sed -i 's/-> str | None/-> Optional[str]/g' "$file"

                # Check if imports need updating
                if ! grep -q "from typing import.*Optional" "$file"; then
                    # Add Optional to existing typing imports or create new import
                    if grep -q "from typing import" "$file"; then
                        sed -i '/from typing import/ s/$/, Optional/' "$file"
                    else
                        sed -i '1i from typing import Optional' "$file"
                    fi
                fi

                echo "    ✅ Fixed $(basename "$file")"
            done
        else
            echo "  ✅ No union syntax found"
        fi

        echo ""
    done

    echo "✅ Compatibility fixes applied to all projects"
    echo "💡 Review the changes and test each project before committing"
}

update_all() {
    echo "🚀 Updating all projects with latest CI standards..."
    echo ""

    PROJECTS_FILE="$WORKSPACE_ROOT/.workspace-projects.list"
    if [ ! -f "$PROJECTS_FILE" ]; then
        echo "📁 No project list found. Running scan first..."
        scan_workspace
    fi

    while read -r project; do
        if [ "$project" != "$SCRIPT_DIR" ]; then  # Skip twickenham_events itself
            PROJECT_NAME=$(basename "$project")
            echo "📦 Updating: $PROJECT_NAME"
            "$SCRIPT_DIR/scripts/extract-ci-standards.sh" "$project"
            echo ""
        fi
    done < "$PROJECTS_FILE"

    echo "✅ All projects updated with CI standards"
}

create_new_project() {
    PROJECT_NAME="$1"
    if [ -z "$PROJECT_NAME" ]; then
        echo "❌ Project name required"
        echo "Usage: $0 new-project <project-name>"
        exit 1
    fi

    PROJECT_PATH="$WORKSPACE_ROOT/$PROJECT_NAME"

    if [ -d "$PROJECT_PATH" ]; then
        echo "❌ Project directory already exists: $PROJECT_PATH"
        exit 1
    fi

    echo "🏗️  Creating new project: $PROJECT_NAME"
    echo "📁 Location: $PROJECT_PATH"

    # Create project directory
    mkdir -p "$PROJECT_PATH"
    cd "$PROJECT_PATH"

    # Initialize with Poetry
    poetry init --no-interaction --name "$PROJECT_NAME" --dependency python="^3.9"

    # Apply CI standards
    echo "📋 Applying CI standards..."
    "$SCRIPT_DIR/scripts/extract-ci-standards.sh" "$PROJECT_PATH"

    # Create basic project structure
    mkdir -p src tests
    echo "# $PROJECT_NAME" > README.md

    # Initialize git
    git init

    # Setup pre-commit (if template was copied)
    if [ -f ".pre-commit-config.yaml.template" ]; then
        mv ".pre-commit-config.yaml.template" ".pre-commit-config.yaml"
        poetry add --group dev pre-commit
        poetry run pre-commit install
    fi

    echo "✅ New project created with CI standards applied"
    echo "📝 Next steps:"
    echo "   1. cd $PROJECT_NAME"
    echo "   2. Review and customize pyproject.toml.template"
    echo "   3. Copy GitHub workflow templates"
    echo "   4. Start coding!"
}

# Main command dispatcher
case "$COMMAND" in
    "extract")
        if [ -z "$TARGET" ]; then
            echo "❌ Target project path required"
            echo "Usage: $0 extract <project-path>"
            exit 1
        fi
        "$SCRIPT_DIR/scripts/extract-ci-standards.sh" "$TARGET"
        ;;
    "scan")
        scan_workspace
        ;;
    "validate")
        validate_compliance
        ;;
    "fix-compatibility")
        fix_compatibility
        ;;
    "update-all")
        update_all
        ;;
    "new-project")
        create_new_project "$TARGET"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
