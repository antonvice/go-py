#!/bin/bash

# A robust script to automate the release process using bump-my-version.
# It ensures checks pass before releasing.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- 1. Get the new version number ---
VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Error: No version specified."
  echo "Usage: ./release.sh <new_version>"
  echo "Example: ./release.sh 0.2.0"
  exit 1
fi

echo "🚀 Preparing new release: v$VERSION"

# --- 2. Run Linters & Tests ---
echo "🛡️ Running checks and tests..."
black --check .
isort --check .
pytest
echo "✅ All checks passed!"

# --- 3. Bump Version, Commit, and Tag ---
echo "🔖 Bumping version, committing, and tagging..."
bump-my-version bump --new-version "$VERSION"

# --- 4. Push to trigger release workflow ---
echo "📤 Pushing commit and tag to GitHub..."
git push && git push --tags

echo "🎉 Successfully published version v$VERSION!"
echo "Check the GitHub Actions tab for the publish workflow."