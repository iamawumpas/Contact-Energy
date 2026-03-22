# Release automation script for Contact Energy integration
# Usage: .\release.ps1 x.y.z
# This script automates the release process by:
# - Pausing to let agent write changelog entry
# - Updating version numbers in all relevant files
# - Creating a git commit with staged changes
# - Creating a git tag and GitHub release with changelog
# - Pushing everything to the repository

param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

# Set error action preference to stop on errors
$ErrorActionPreference = "Stop"

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput $Message -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput $Message -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput $Message -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput $Message -ForegroundColor Blue
}

# Validate version format (x.y.z)
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Error "Error: Invalid version format. Use x.y.z (e.g., 0.0.2)"
    exit 1
}

Write-Success "╔════════════════════════════════════════════════════════════╗"
Write-Success "║       Contact Energy Integration Release Script           ║"
Write-Success "║                   Version $Version                          ║"
Write-Success "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Step 1: Clean up any stale sentinel files from previous runs
Write-Info "[Step 1/9] " -NoNewline
Write-Warning "Cleaning up stale sentinel files..."
if (Test-Path ".changelog_ready") { Remove-Item ".changelog_ready" -Force }
if (Test-Path ".agent_changelog_complete") { Remove-Item ".agent_changelog_complete" -Force }
Write-Success "✓ Cleanup complete"
Write-Host ""

# Step 2: Instruct the agent to reread instructions
Write-Info "[Step 2/9] " -NoNewline
Write-Warning "Agent instruction review..."
Write-Host ""
Write-Warning "════════════════════════════════════════════════════════════"
Write-Warning "║  AGENT DIRECTIVE: Review instructions immediately      ║"
Write-Warning "════════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "REREAD these files NOW:"
Write-Host "  • .Agent_Instructions.md"
Write-Host "  • .API_Instructions_v2.md"
Write-Host ""
Write-Host "You MUST verify:"
Write-Host "  - Changelog entries ONLY when release.ps1 instructs (this moment)"
Write-Host "  - No autonomous changelog entries for minor edits"
Write-Host "  - Current authorization levels and workflow expectations"
Write-Host ""

# Step 3: Instruct the agent to write the changelog
Write-Info "[Step 3/9] " -NoNewline
Write-Warning "Waiting for changelog entry..."
Write-Host ""
Write-Warning "════════════════════════════════════════════════════════════"
Write-Warning "║  AGENT DIRECTIVE: Write changelog entry NOW            ║"
Write-Warning "════════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "WRITE changelog entry:"
Write-Host "  1) Edit Changelog.md with entry for version $Version"
Write-Host "  2) Use format: ## [ $Version ]"
Write-Host "  3) Include sections: ### Added, ### Fixed, ### Changed (as needed)"
Write-Host "  4) Create sentinel file: New-Item .agent_changelog_complete -ItemType File"
Write-Host ""
Write-Host "The script will continue automatically after completion."
Write-Host ""
Write-Info "Polling for completion (checking every 3 seconds, 45s timeout)..."
Write-Host ""

# Wait loop: poll for sentinel file and changelog entry
$waitCount = 0
$maxWaitCount = 15  # 45 seconds / 3 seconds per check
while ($true) {
    # Check if sentinel exists and changelog has the version header
    if ((Test-Path ".agent_changelog_complete") -and 
        (Test-Path "Changelog.md") -and 
        ((Get-Content "Changelog.md" -ErrorAction SilentlyContinue) -match "^## \[ $([regex]::Escape($Version)) \]")) {
        Write-Host ""
        Write-Success "✓ Changelog entry detected for version $Version"
        if (Test-Path ".agent_changelog_complete") { Remove-Item ".agent_changelog_complete" -Force }
        break
    }

    # Show a progress indicator every 3 seconds
    $waitCount++
    Write-Host "." -NoNewline
    
    # Safety timeout after 45 seconds
    if ($waitCount -ge $maxWaitCount) {
        Write-Host ""
        Write-Error "Error: Timed out waiting for changelog (45 seconds)"
        Write-Host "The agent may not have completed the changelog entry."
        exit 1
    }

    Start-Sleep -Seconds 3
}
Write-Host ""

# Step 4: Update version numbers in all files
Write-Info "[Step 4/9] " -NoNewline
Write-Warning "Updating version numbers..."

# Update README.md with version badge
Write-Host "  - README.md badge... " -NoNewline
if (Test-Path "README.md") {
    $readmeContent = Get-Content "README.md" -Raw
    if ($readmeContent -match "img\.shields\.io/badge/version") {
        $readmeContent = $readmeContent -replace "img\.shields\.io/badge/version-\d+\.\d+\.\d+-blue", "img.shields.io/badge/version-$Version-blue"
        Set-Content "README.md" $readmeContent -NoNewline
        Write-Success "✓"
    } else {
        Write-Warning "⚠ (badge not found)"
    }
} else {
    Write-Warning "⚠ (README.md not found)"
}

# Update manifest.json version
Write-Host "  - manifest.json... " -NoNewline
$manifestPath = "custom_components/contact_energy/manifest.json"
if (Test-Path $manifestPath) {
    $manifestContent = Get-Content $manifestPath -Raw
    $manifestContent = $manifestContent -replace '"version":\s*"\d+\.\d+\.\d+"', '"version": "' + $Version + '"'
    Set-Content $manifestPath $manifestContent -NoNewline
    Write-Success "✓"
} else {
    Write-Warning "⚠ (manifest.json not found)"
}

# Update HACS.json version
Write-Host "  - HACS.json... " -NoNewline
if (Test-Path "HACS.json") {
    $hacsContent = Get-Content "HACS.json" -Raw
    $hacsContent = $hacsContent -replace '"version":\s*"\d+\.\d+\.\d+"', '"version": "' + $Version + '"'
    Set-Content "HACS.json" $hacsContent -NoNewline
    Write-Success "✓"
} else {
    Write-Warning "⚠ (HACS.json not found)"
}

Write-Success "✓ All version numbers updated"
Write-Host ""

# Step 5: Stage all modified files
Write-Info "[Step 5/9] " -NoNewline
Write-Warning "Staging changes..."
try {
    git add -A
    Write-Success "✓ All changes staged"
} catch {
    Write-Error "Failed to stage changes: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# Step 6: Create git commit
Write-Info "[Step 6/9] " -NoNewline
Write-Warning "Creating git commit..."
try {
    git commit -m "Release v$Version"
    Write-Success "✓ Commit created: Release v$Version"
} catch {
    Write-Error "Failed to create commit: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# Step 7: Create git tag
Write-Info "[Step 7/9] " -NoNewline
Write-Warning "Creating git tag..."
try {
    git tag -a "v$Version" -m "Release version $Version"
    Write-Success "✓ Tag created: v$Version"
} catch {
    Write-Error "Failed to create tag: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# Step 8: Extract changelog and create GitHub release
Write-Info "[Step 8/9] " -NoNewline
Write-Warning "Creating GitHub release..."

# Extract changelog entry for this version
$changelogEntry = ""
if (Test-Path "Changelog.md") {
    $changelogContent = Get-Content "Changelog.md"
    $inTargetVersion = $false
    $extractedLines = @()
    
    foreach ($line in $changelogContent) {
        if ($line -match "^## \[ $([regex]::Escape($Version)) \]") {
            $inTargetVersion = $true
            continue
        }
        if ($inTargetVersion -and $line -match "^## \[") {
            break
        }
        if ($inTargetVersion) {
            $extractedLines += $line
        }
    }
    
    # Join lines and trim whitespace
    $changelogEntry = ($extractedLines -join "`n").Trim()
}

if ([string]::IsNullOrWhiteSpace($changelogEntry)) {
    Write-Warning "⚠ Could not extract changelog entry, using default message"
    $changelogEntry = "Release v$Version"
} else {
    Write-Success "✓ Changelog entry extracted ($($changelogEntry.Length) characters)"
}

# Create GitHub release using gh CLI with changelog content as release notes
try {
    gh release create "v$Version" --title "Release v$Version" --notes $changelogEntry
    Write-Success "✓ GitHub release created"
} catch {
    Write-Error "Failed to create GitHub release: $($_.Exception.Message)"
    Write-Warning "Make sure 'gh' CLI is installed and authenticated"
    exit 1
}
Write-Host ""

# Step 9: Push to repository
Write-Info "[Step 9/9] " -NoNewline
Write-Warning "Pushing to repository..."
try {
    git push origin main
    git push origin "v$Version"
    Write-Success "✓ Pushed commit and tag to origin/main"
} catch {
    Write-Error "Failed to push to repository: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

Write-Success "╔════════════════════════════════════════════════════════════╗"
Write-Success "║           Release v$Version completed successfully!          ║"
Write-Success "╚════════════════════════════════════════════════════════════╝"
Write-Host ""
Write-Host "Summary:"
Write-Host "  • Version $Version committed and tagged"
Write-Host "  • GitHub release created with changelog"
Write-Host "  • All changes pushed to main branch"
Write-Host ""