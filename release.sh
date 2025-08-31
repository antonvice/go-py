#!/bin/bash

# A robust script to automate the release process using semantic versioning.
# Usage: ./release.sh patch|minor|major

# Exit immediately if a command exits with a non-zero status.
set -e

# --- 1. Get the type of version bump ---
BUMP_TYPE=$1

if [[ "$BUMP_TYPE" != "patch" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "major" ]]; then
  echo "Error: Invalid or no bump type specified."
  echo "Usage: ./release.sh <patch|minor|major>"
  exit 1
fi

echo "🚀 Preparing a '$BUMP_TYPE' release..."

# --- 2. Run Linters & Tests ---
echo "🛡️ Running checks and tests..."
black --check .
isort --check .
pytest
echo "✅ All checks passed!"

# --- 3. Bump Version, Commit, and Tag ---
# The tool will now automatically figure out the current version,
# increment it, update the files, commit, and tag.
echo "🔖 Bumping version, committing, and tagging..."
bump-my-version bump "$BUMP_TYPE"

# --- 4. Push to trigger release workflow ---
echo "📤 Pushing commit and tag to GitHub..."
git push && git push --tags

echo "🎉 Successfully triggered release workflow!"
echo "Check the GitHub Actions tab for the publish progress."