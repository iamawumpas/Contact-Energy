#!/bin/bash

# Release automation script for Contact Energy integration
# Usage: ./release.sh x.y.z
# This script automates the release process by:
# - Pausing to let agent write changelog entry
# - Updating version numbers in all relevant files
# - Creating a git commit with staged changes
# - Creating a git tag and GitHub release with changelog
# - Pushing everything to the repository

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Contact Energy Integration Release Script           ║${NC}"
echo -e "${GREEN}║                   Version ${VERSION}                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Clean up any stale sentinel files from previous runs
echo -e "${BLUE}[Step 1/8]${NC} ${YELLOW}Cleaning up stale sentinel files...${NC}"
rm -f .changelog_ready
rm -f .agent_changelog_complete
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Step 2: Instruct the agent to write the changelog
echo -e "${BLUE}[Step 2/8]${NC} ${YELLOW}Waiting for changelog entry...${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}║  ACTION REQUIRED: Ask the agent to write the changelog  ║${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Please ask the agent to:"
echo "  1) Write the changelog entry for version ${VERSION} in Changelog.md"
echo "  2) Use the format: ## [ ${VERSION} ]"
echo "  3) Include sections: ### Added, ### Fixed, ### Changed (as needed)"
echo "  4) When finished, create the file: .agent_changelog_complete"
echo ""
echo "After the agent completes these steps, this script will continue automatically."
echo ""
echo -e "${BLUE}Polling for completion (checking every 3 seconds)...${NC}"
echo ""

# Wait loop: poll for sentinel file and changelog entry
WAIT_COUNT=0
while true; do
    # Check if sentinel exists and changelog has the version header
    if [ -f .agent_changelog_complete ] && grep -q "^## \[ ${VERSION} \]" Changelog.md; then
        echo ""
        echo -e "${GREEN}✓ Changelog entry detected for version ${VERSION}${NC}"
        rm -f .agent_changelog_complete
        break
    fi

    # Show a progress indicator every 3 seconds
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
    
    # Safety timeout after 5 minutes
    if [ $WAIT_COUNT -ge 100 ]; then
        echo ""
        echo -e "${RED}Error: Timed out waiting for changelog (5 minutes)${NC}"
        echo "The agent may not have completed the changelog entry."
        exit 1
    fi

    sleep 3
done
echo ""

# Step 3: Update version numbers in all files
echo -e "${BLUE}[Step 3/8]${NC} ${YELLOW}Updating version numbers...${NC}"

# Update README.md with version badge
echo -n "  - README.md badge... "
if grep -q "img.shields.io/badge/version" README.md; then
    # Find and replace version in badge (format: ![Version](https://img.shields.io/badge/version-x.y.z-blue.svg))
    sed -i "s/img.shields.io\/badge\/version-[0-9]*\.[0-9]*\.[0-9]*-blue/img.shields.io\/badge\/version-${VERSION}-blue/" README.md
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (badge not found)${NC}"
fi

# Update manifest.json version
echo -n "  - manifest.json... "
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"${VERSION}\"/" custom_components/contact_energy/manifest.json
echo -e "${GREEN}✓${NC}"

# Update HACS.json version
echo -n "  - HACS.json... "
sed -i "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"${VERSION}\"/" HACS.json
echo -e "${GREEN}✓${NC}"

echo -e "${GREEN}✓ All version numbers updated${NC}"
echo ""

# Step 4: Stage all modified files
echo -e "${BLUE}[Step 4/8]${NC} ${YELLOW}Staging changes...${NC}"
git add -A
echo -e "${GREEN}✓ All changes staged${NC}"
echo ""

# Step 5: Create git commit
echo -e "${BLUE}[Step 5/8]${NC} ${YELLOW}Creating git commit...${NC}"
git commit -m "Release v${VERSION}"
echo -e "${GREEN}✓ Commit created: Release v${VERSION}${NC}"
echo ""

# Step 6: Create git tag
echo -e "${BLUE}[Step 6/8]${NC} ${YELLOW}Creating git tag...${NC}"
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
echo -e "${GREEN}✓ Tag created: v${VERSION}${NC}"
echo ""

# Step 7: Extract changelog and create GitHub release
echo -e "${BLUE}[Step 7/8]${NC} ${YELLOW}Creating GitHub release...${NC}"

# Extract changelog entry for this version
# Finds content between version header and next header, excluding the headers themselves
CHANGELOG_ENTRY=$(sed -n "/^## \[ ${VERSION} \]/,/^## \[/p" Changelog.md | sed '1d;$d')

# Trim leading/trailing whitespace
CHANGELOG_ENTRY=$(echo "$CHANGELOG_ENTRY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

if [ -z "$CHANGELOG_ENTRY" ]; then
    echo -e "${YELLOW}⚠ Could not extract changelog entry, using default message${NC}"
    CHANGELOG_ENTRY="Release v${VERSION}"
else
    echo -e "${GREEN}✓ Changelog entry extracted (${#CHANGELOG_ENTRY} characters)${NC}"
fi

# Create GitHub release using gh CLI with changelog content as release notes
gh release create "v${VERSION}" --title "Release v${VERSION}" --notes "$CHANGELOG_ENTRY"
echo -e "${GREEN}✓ GitHub release created${NC}"
echo ""

# Step 8: Push to repository
echo -e "${BLUE}[Step 8/8]${NC} ${YELLOW}Pushing to repository...${NC}"
git push origin main
git push origin "v${VERSION}"
echo -e "${GREEN}✓ Pushed commit and tag to origin/main${NC}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Release v${VERSION} completed successfully!          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Summary:"
echo "  • Version ${VERSION} committed and tagged"
echo "  • GitHub release created with changelog"
echo "  • All changes pushed to main branch"
echo ""
