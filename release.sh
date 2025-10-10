#!/bin/bash

# Contact Energy Integration Release Script
# Automated version bumping and release preparation
# 
# Usage:
#   ./release.sh                           # Auto-increment patch version, auto-generate changelog
#   ./release.sh 0.3.13                   # Use specific version, auto-generate changelog  
#   ./release.sh 0.3.13 "Title" "Desc"    # Fully automated with version and changelog

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current version from manifest.json
CURRENT_VERSION=$(grep '"version"' custom_components/contact_energy/manifest.json | sed 's/.*"v\([^"]*\)".*/\1/')
echo -e "${YELLOW}Current version: v${CURRENT_VERSION}${NC}"

# Check command line arguments
AUTO_MODE=false
if [ $# -eq 1 ]; then
    # Version number provided
    NEW_VERSION="$1"
    echo -e "${GREEN}New version: v${NEW_VERSION}${NC}"
    CHANGELOG_TITLE=""
    CHANGELOG_DESC=""
    AUTO_MODE=true
    echo -e "${YELLOW}Running in automated mode with version v${NEW_VERSION}${NC}"
elif [ $# -eq 3 ]; then
    # Version, title, and description provided
    NEW_VERSION="$1"
    CHANGELOG_TITLE="$2"
    CHANGELOG_DESC="$3"
    AUTO_MODE=true
    echo -e "${GREEN}New version: v${NEW_VERSION}${NC}"
    echo -e "${YELLOW}Using provided changelog: $CHANGELOG_TITLE${NC}"
    echo -e "${YELLOW}Running in automated mode${NC}"
else
    # No arguments - auto-increment patch version
    IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
    NEW_PATCH=$((patch + 1))
    NEW_VERSION="${major}.${minor}.${NEW_PATCH}"
    echo -e "${GREEN}New version: v${NEW_VERSION}${NC}"
fi

# Confirm with user only if not in auto mode
if [ "$AUTO_MODE" = false ]; then
    read -p "Proceed with version bump to v${NEW_VERSION}? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Release cancelled${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Proceeding with automated version bump to v${NEW_VERSION}${NC}"
fi

# Update version in manifest.json
echo -e "${YELLOW}Updating manifest.json...${NC}"
sed -i "s/\"version\": \"v${CURRENT_VERSION}\"/\"version\": \"v${NEW_VERSION}\"/" custom_components/contact_energy/manifest.json

# Update version in README.md
echo -e "${YELLOW}Updating README.md...${NC}"
# Replace '**Version:** <anything>' with the new version, case-insensitive match for 'Version'
sed -i -E "s/^\*\*Version:\*\* .*/**Version:** ${NEW_VERSION}/I" README.md
# Also replace HTML header variant '<strong>version:</strong> X.Y.Z' inside the README header table
# This is resilient to publish flows that transform Markdown/HTML differently
sed -i -E "s|(<strong>[Vv]ersion:</strong> )[0-9]+\.[0-9]+\.[0-9]+|\1${NEW_VERSION}|" README.md

# Update version in info.md
echo -e "${YELLOW}Updating info.md...${NC}"
sed -i "s/version: ${CURRENT_VERSION}/version: ${NEW_VERSION}/" info.md

# Update version in hacs.json
echo -e "${YELLOW}Updating hacs.json...${NC}"
sed -i "s/\"version\": \"${CURRENT_VERSION}\"/\"version\": \"${NEW_VERSION}\"/" hacs.json

# Generate automatic changelog entry
if [ "$AUTO_MODE" = false ]; then
    echo -e "${YELLOW}Enter changelog entry for v${NEW_VERSION}:${NC}"
    read -p "Title: " CHANGELOG_TITLE
    read -p "Description: " CHANGELOG_DESC
elif [ -z "$CHANGELOG_TITLE" ]; then
    # Auto mode but no changelog provided - generate automatically
    echo -e "${YELLOW}Generating automatic changelog for v${NEW_VERSION}${NC}"
    
    # Get recent commits since last tag to auto-generate changelog
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [ -n "$LAST_TAG" ]; then
        # Get commits since last tag
        RECENT_COMMITS=$(git log --oneline "${LAST_TAG}..HEAD" --no-merges | head -5)
        if [ -n "$RECENT_COMMITS" ]; then
            CHANGELOG_TITLE="Version ${NEW_VERSION} - Bug fixes and improvements"
            CHANGELOG_DESC="Recent changes:
$(echo "$RECENT_COMMITS" | sed 's/^[a-f0-9]* /- /')"
        else
            CHANGELOG_TITLE="Version ${NEW_VERSION} - Minor update"
            CHANGELOG_DESC="- Version bump and maintenance updates"
        fi
    else
        CHANGELOG_TITLE="Version ${NEW_VERSION} - Initial release"
        CHANGELOG_DESC="- First release of Contact Energy integration"
    fi
    
    echo -e "${GREEN}Auto-generated changelog:${NC}"
    echo -e "${YELLOW}Title:${NC} $CHANGELOG_TITLE"
    echo -e "${YELLOW}Description:${NC}"
    echo "$CHANGELOG_DESC"
else
    echo -e "${YELLOW}Using provided changelog for v${NEW_VERSION}${NC}"
fi

# Update CHANGELOG.md
echo -e "${YELLOW}Updating CHANGELOG.md...${NC}"
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << EOF
## v${NEW_VERSION} - $(date +%Y-%m-%d)
${CHANGELOG_TITLE}

${CHANGELOG_DESC}

EOF
cat CHANGELOG.md >> "$TEMP_FILE"
mv "$TEMP_FILE" CHANGELOG.md

# Generate release notes
echo -e "${YELLOW}Generating RELEASE_NOTES.txt...${NC}"
cat > RELEASE_NOTES.txt << EOF
## v${NEW_VERSION} - $(date +%Y-%m-%d)
${CHANGELOG_TITLE}

${CHANGELOG_DESC}

EOF

# Commit changes
echo -e "${YELLOW}Committing changes...${NC}"
git add -A
git commit -m "Version bump to v${NEW_VERSION}

- ${CHANGELOG_TITLE}
- Updated version across all metadata files"

echo -e "${GREEN}✅ Release v${NEW_VERSION} prepared successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Push changes: git push origin main"
echo "2. Create a GitHub release (tag v${NEW_VERSION}) using RELEASE_NOTES.txt, or run: gh release create v${NEW_VERSION} -t 'v${NEW_VERSION} - ${CHANGELOG_TITLE}' -F RELEASE_NOTES.txt"
echo "3. HACS will automatically detect the new release"

echo -e "${GREEN}Release notes saved to RELEASE_NOTES.txt${NC}"