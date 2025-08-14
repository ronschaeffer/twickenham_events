#!/bin/bash
set -euo pipefail

# Semantic versioning release helper for twickenham_events
# Usage: ./release.sh [major|minor|patch] [--push]

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_usage() { echo "Usage: $0 [major|minor|patch] [--push]" >&2; }

# Parse args
BUMP_TYPE=""
PUSH=false
for arg in "$@"; do
  case "$arg" in
    --push) PUSH=true ;;
    --*) ;;
    *) [[ -z "$BUMP_TYPE" ]] && BUMP_TYPE=${arg#--} ;;
  esac
done

if [[ -z "$BUMP_TYPE" ]]; then
  print_usage; exit 1
fi
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
  print_error "Invalid bump type: $BUMP_TYPE"; print_usage; exit 1
fi

# Ensure Poetry is available
if ! command -v poetry >/dev/null 2>&1; then
  print_error "Poetry is not installed or not on PATH."; exit 1
fi
print_status "Poetry version: $(poetry --version)"
print_status "Validating pyproject with 'poetry check'..."
poetry check

# Git sanity checks
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  print_error "Not in a git repository"; exit 1
fi
if ! git diff-index --quiet HEAD --; then
  print_error "Working directory is not clean. Please commit or stash changes."; exit 1
fi

current_branch=$(git rev-parse --abbrev-ref HEAD)
print_status "Current branch: ${current_branch}"

current_version=$(poetry version --short)
print_status "Current version: ${current_version}"

print_status "Bumping ${BUMP_TYPE} version..."
poetry version "$BUMP_TYPE"
new_version=$(poetry version --short)
print_success "Version bumped to ${new_version}"

print_status "Synchronizing version across files..."
if command -v python3 &>/dev/null; then
  python3 scripts/sync_versions.py || true
else
  poetry run python scripts/sync_versions.py || true
fi

tag_name="v${new_version}"
print_status "Creating tag ${tag_name}"
# Include main files by default; commit all changes from bump/sync
git add -A
git commit -m "chore: bump version to ${new_version}"
git tag -a "${tag_name}" -m "Release ${tag_name}"
print_success "Created tag: ${tag_name}"

if $PUSH; then
  print_status "Pushing ${current_branch} and ${tag_name} to origin..."
  git push origin "$current_branch"
  git push origin "$tag_name"
  print_success "Pushed tag ${tag_name}"
else
  print_warning "Not pushing by default. To push now, re-run with --push"
  echo "git push origin ${current_branch} && git push origin ${tag_name}"
fi
