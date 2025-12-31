#!/bin/bash

# Feature branch automation script for Contact Energy integration
# Usage: ./feature.sh x.y.z-beta.n [branch-name]
# This script automates the feature release process by:
# - Updating version numbers in all relevant files
# - Creating a git commit on the feature branch
# - Creating a git tag and GitHub pre-release
# - Pushing changes to the repository

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate version number argument
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo "Usage: $0 x.y.z-beta.n [branch-name]"
    echo "Example: $0 1.4.0-beta.1 feature/usage-data-v1.4"
    exit 1
fi

VERSION=$1
BRANCH=${2:-$(git branch --show-current)}

# Validate version format (x.y.z-beta.n or x.y.z-alpha.n)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+-(beta|alpha)\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use x.y.z-beta.n or x.y.z-alpha.n (e.g., 1.4.0-beta.1)${NC}"
    exit 1
fi

# Validate we're on a feature branch
if [[ $BRANCH == "main" ]] || [[ $BRANCH == "master" ]]; then
    echo -e "${RED}Error: Cannot run feature.sh on main/master branch. Use release.sh instead.${NC}"
    exit 1
fi

echo -e "${YELLOW}Feature release script started for version ${VERSION} on branch ${BRANCH}${NC}"

# Step 1: Instruct the agent to write the changelog
echo -e "${YELLOW}Step 1: Changelog generation${NC}"
echo "Please instruct the agent to write the changelog entry for version ${VERSION}"
echo "Run this command and provide the changelog details:"
echo ""
echo -e "${GREEN}Ask the agent to write the changelog for version ${VERSION}${NC}"
echo ""
read -p "Press Enter after the agent has updated Changelog.md: "

# Step 2: Update README.md with version badge
echo -e "${YELLOW}Step 2: Updating README.md${NC}"
if grep -q "img.shields.io/badge/version" README.md; then
    # Replace version in badge, preserving beta/alpha suffix
    sed -i "s/img.shields.io\/badge\/version-[0-9]*\.[0-9]*\.[0-9]*\(-[a-z]*\.[0-9]*\)\?-blue/img.shields.io\/badge\/version-${VERSION}-blue/" README.md
    echo -e "${GREEN}✓ README.md version badge updated${NC}"
else
    echo -e "${YELLOW}⚠ README.md version badge not found in expected format${NC}"
fi

# Step 3: Update manifest.json version
echo -e "${YELLOW}Step 3: Updating manifest.json${NC}"
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\(-[a-z]*\.[0-9]*\)\?\"/\"version\": \"${VERSION}\"/" custom_components/contact_energy/manifest.json
echo -e "${GREEN}✓ manifest.json updated${NC}"

# Step 4: Update HACS.json version
echo -e "${YELLOW}Step 4: Updating HACS.json${NC}"
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\(-[a-z]*\.[0-9]*\)\?\"/\"version\": \"${VERSION}\"/" HACS.json
echo -e "${GREEN}✓ HACS.json updated${NC}"

# Stage all modified files before commit
git add -A

# Step 5: Commit all files
echo -e "${YELLOW}Step 5: Creating git commit${NC}"
git commit -m "Feature release v${VERSION}"
echo -e "${GREEN}✓ Commit created${NC}"

# Step 6: Create and push git tag
echo -e "${YELLOW}Step 6: Creating git tag${NC}"
# Delete local tag if it exists
git tag -d "v${VERSION}" 2>/dev/null || true
git tag -a "v${VERSION}" -m "Feature release version ${VERSION}"
echo -e "${GREEN}✓ Tag created${NC}"

# Step 7: Push commit and tag to repository
echo -e "${YELLOW}Step 7: Pushing to repository${NC}"
git push origin "$BRANCH"
git push origin "v${VERSION}" --force
echo -e "${GREEN}✓ Pushed to repository${NC}"

# Step 8: Create GitHub pre-release with changelog
echo -e "${YELLOW}Step 8: Creating GitHub pre-release${NC}"
# Extract changelog entry for this version using sed
# Finds content between version header and next header, excluding the headers themselves
CHANGELOG_ENTRY=$(sed -n "/^## \[ ${VERSION} \]/,/^## \[/p" Changelog.md | sed '1d;$d')

# Trim leading/trailing whitespace
CHANGELOG_ENTRY=$(echo "$CHANGELOG_ENTRY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

if [ -z "$CHANGELOG_ENTRY" ]; then
    echo -e "${YELLOW}⚠ Could not extract changelog entry, using default${NC}"
    CHANGELOG_ENTRY="Feature release v${VERSION} - Pre-release for testing"
fi

# Delete remote release if it exists
gh release delete "v${VERSION}" -y 2>/dev/null || true

# Create GitHub pre-release using gh CLI with changelog content as release notes
gh release create "v${VERSION}" --target "$BRANCH" --prerelease --title "v${VERSION} - Feature Testing" --notes "## ⚠️ Pre-release for Testing

$CHANGELOG_ENTRY"
echo -e "${GREEN}✓ GitHub pre-release created${NC}"

echo -e "${GREEN}Feature release v${VERSION} completed successfully!${NC}"
echo -e "${YELLOW}Branch: ${BRANCH}${NC}"
echo -e "${YELLOW}Remember: This is a pre-release for testing. Merge to main and use release.sh for stable releases.${NC}"
