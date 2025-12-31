#!/bin/bash

# Release automation script for Contact Energy integration
# Usage: ./release.sh x.y.z
# This script automates the release process by:
# - Updating version numbers in all relevant files
# - Creating a git commit with staged changes
# - Creating a git tag and GitHub release
# - Pushing changes to the repository

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate version number argument
if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo "Usage: $0 x.y.z"
    exit 1
fi

VERSION=$1

# Validate version format (x.y.z)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use x.y.z (e.g., 0.0.2)${NC}"
    exit 1
fi

echo -e "${YELLOW}Release script started for version ${VERSION}${NC}"

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
    # Find and replace version in badge (format: ![Version](https://img.shields.io/badge/version-x.y.z-blue.svg))
    sed -i "s/img.shields.io\/badge\/version-[0-9]*\.[0-9]*\.[0-9]*-blue/img.shields.io\/badge\/version-${VERSION}-blue/" README.md
    echo -e "${GREEN}✓ README.md version badge updated${NC}"
else
    echo -e "${YELLOW}⚠ README.md version badge not found in expected format${NC}"
fi

# Step 3: Update manifest.json version
echo -e "${YELLOW}Step 3: Updating manifest.json${NC}"
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"${VERSION}\"/" custom_components/contact_energy/manifest.json
echo -e "${GREEN}✓ manifest.json updated${NC}"

# Step 4: Update HACS.json version
echo -e "${YELLOW}Step 4: Updating HACS.json${NC}"
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"${VERSION}\"/" HACS.json
echo -e "${GREEN}✓ HACS.json updated${NC}"

# Stage all modified files before commit
git add -A

# Step 5: Commit all files
echo -e "${YELLOW}Step 5: Creating git commit${NC}"
git commit -m "Release v${VERSION}"
echo -e "${GREEN}✓ Commit created${NC}"

# Step 6: Create and push git tag
echo -e "${YELLOW}Step 6: Creating git tag${NC}"
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
echo -e "${GREEN}✓ Tag created${NC}"

# Step 7: Push commit and tag to repository
echo -e "${YELLOW}Step 7: Pushing to repository${NC}"
git push origin main
git push origin "v${VERSION}"
echo -e "${GREEN}✓ Pushed to repository${NC}"

# Step 8: Create GitHub release with changelog
echo -e "${YELLOW}Step 8: Creating GitHub release${NC}"
# Extract changelog entry for this version using sed (more reliable than awk)
# Finds content between version header and next header, excluding the headers themselves
CHANGELOG_ENTRY=$(sed -n "/^## \[ ${VERSION} \]/,/^## \[/p" Changelog.md | sed '1d;$d')

# Trim leading/trailing whitespace
CHANGELOG_ENTRY=$(echo "$CHANGELOG_ENTRY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

if [ -z "$CHANGELOG_ENTRY" ]; then
    echo -e "${YELLOW}⚠ Could not extract changelog entry, using default${NC}"
    CHANGELOG_ENTRY="Release v${VERSION}"
fi

# Create GitHub release using gh CLI with changelog content as release notes
gh release create "v${VERSION}" --title "Release v${VERSION}" --notes "$CHANGELOG_ENTRY"
echo -e "${GREEN}✓ GitHub release created${NC}"

echo -e "${GREEN}Release v${VERSION} completed successfully!${NC}"
