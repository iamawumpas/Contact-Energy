#!/bin/bash
set -Eeuo pipefail

# Automated release script for Contact Energy integration

# Files to update version in
VERSION_FILES=(
  "hacs.json"
  "custom_components/contact_energy/manifest.json"
  "README.md"
)

# --- Release guards (kill-switch) ---
# Enforce manual approval, version confirmation, and authorized releaser.
check_release_guards() {
  local version="$1"

  # Basic repo sanity checks
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$branch" != "main" ]]; then
    echo "Release guard: Must release from 'main' branch (current: $branch)." >&2
    exit 1
  fi

  # Working tree must be clean (no staged or unstaged changes)
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Release guard: Working tree must be clean (no unstaged or staged changes)." >&2
    exit 1
  fi

  # Must be up-to-date with remote tracking branch
  git fetch -q origin
  if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
    local LOCAL REMOTE
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    if [[ "$LOCAL" != "$REMOTE" ]]; then
      echo "Release guard: Local main is not up to date with origin/main. Pull/rebase first." >&2
      exit 1
    fi
  fi

  # 1) Explicit environment approval
  if [[ "${RELEASE_APPROVED:-}" != "1" ]]; then
    echo "Release guard: Missing approval. Set RELEASE_APPROVED=1 to proceed." >&2
    echo "Example: RELEASE_APPROVED=1 bash $0 ${version} [.summary-file]" >&2
    exit 1
  fi

  # 2) Confirmation file matching the version
  if [[ ! -f .allow_release ]]; then
    echo "Release guard: .allow_release file not found at repo root." >&2
    echo "Create a file named .allow_release containing exactly: ${version}" >&2
    exit 1
  fi
  local allowed_version
  allowed_version=$(head -n1 .allow_release | tr -d ' \t\r\n')
  if [[ "${allowed_version}" != "${version}" ]]; then
    echo "Release guard: .allow_release has '${allowed_version}', expected '${version}'." >&2
    exit 1
  fi

  # 3) Verify the releaser identity from git config user.email
  local email
  email=$(git config user.email || true)
  if [[ -z "${email}" ]]; then
    echo "Release guard: git config user.email is empty. Configure your git email." >&2
    exit 1
  fi
  if [[ ! -f .release-owners ]]; then
    echo "Release guard: .release-owners is missing. Create it with one allowed email per line." >&2
    echo "Your current git user.email: ${email}" >&2
    exit 1
  fi
  # Allow skipping owner check via env, or when the file exists but has no non-empty lines
  if [[ "${RELEASE_SKIP_OWNER_CHECK:-}" != "1" ]]; then
    local owners_count
    owners_count=$(grep -Ev '^[[:space:]]*$' .release-owners | wc -l | tr -d ' \t')
    if [[ "${owners_count}" -eq 0 ]]; then
      echo "Release guard: .release-owners is empty; skipping owner check." >&2
    else
      if ! grep -Fxq "${email}" .release-owners; then
        echo "Release guard: ${email} is not listed in .release-owners. Aborting." >&2
        exit 1
      fi
    fi
  else
    echo "Release guard: Skipping owner check (RELEASE_SKIP_OWNER_CHECK=1)" >&2
  fi

  # 4) Ensure version increases the latest tag (semantic version order)
  local last_tag
  last_tag=$(git tag --sort=version:refname | tail -n 1 || true)
  if [[ -n "$last_tag" ]]; then
    # sort -V compares version numbers naturally
    local top
    top=$(printf "%s\n%s\n" "$last_tag" "$version" | sort -V | tail -n1)
    if [[ "$top" != "$version" ]]; then
      echo "Release guard: Version $version is not greater than latest tag $last_tag." >&2
      exit 1
    fi
  fi
}

# Update README.md version robustly (preserve formatting; insert if missing)
update_readme_version() {
  local new_version="$1"
  local f="README.md"
  [[ ! -f "$f" ]] && return 0

  # Update version in HTML <strong> tag format used in the table
  # Look for patterns like: <strong>version:</strong> 0.4.0
  sed -i -E 's/(<strong>version:<\/strong>)[[:space:]]+[0-9.]+/\1 '"$new_version"'/' "$f"
}

update_version_in_files() {
  local new_version="$1"
  for f in "${VERSION_FILES[@]}"; do
    if [[ -f "$f" ]]; then
      if [[ "$f" == *.json ]]; then
        # Update JSON version field (preserve formatting)
        sed -i -E 's/("version"[^"]*":\s*")[0-9.]+(\")/\1'$new_version'\2/' "$f"
      elif [[ "$f" == "README.md" ]]; then
        update_readme_version "$new_version"
      fi
    fi
  done
}

# Find previous tag before the provided version (semantic sort)
previous_tag_for_version() {
  local version="$1"
  local tags sorted prev=""
  mapfile -t sorted < <(git tag --sort=version:refname)
  for t in "${sorted[@]}"; do
    if [[ "$t" == "$version" ]]; then
      echo "$prev"
      return 0
    fi
    prev="$t"
  done
  echo "" # none
}

# Build detailed changelog entry from a git range (prev..curr) with specific change descriptions
build_changelog_from_range() {
  local range="$1"

  # Analyze specific changes in key files to generate detailed descriptions
  local detailed_changes=""
  
  # Check config_flow.py changes
  if git diff $range --name-only | grep -q "custom_components/contact_energy/config_flow.py"; then
    local config_diff
    config_diff=$(git diff $range -- custom_components/contact_energy/config_flow.py)
    if echo "$config_diff" | grep -q "domain = DOMAIN"; then
      detailed_changes+="- Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)\n"
    fi
    if echo "$config_diff" | grep -q "duplicate.*import\|import.*duplicate" || echo "$config_diff" | grep -qE "^-.*import.*ContactEnergyApi"; then
      detailed_changes+="- Removed duplicate import statements in config flow\n"
    fi
    if echo "$config_diff" | grep -q "selector\|voluptuous\|schema"; then
      detailed_changes+="- Updated config flow validation schema and UI selectors\n"
    fi
    if echo "$config_diff" | grep -q "error.*mapping\|InvalidAuth\|CannotConnect"; then
      detailed_changes+="- Enhanced error handling and user-friendly error messages\n"
    fi
  fi

  # Check api.py changes
  if git diff $range --name-only | grep -q "custom_components/contact_energy/api.py"; then
    local api_diff
    api_diff=$(git diff $range -- custom_components/contact_energy/api.py)
    if echo "$api_diff" | grep -q "retry\|backoff\|exponential"; then
      detailed_changes+="- Added retry logic and exponential backoff for API requests\n"
    fi
    if echo "$api_diff" | grep -q "async_get_usage\|usage.*endpoint"; then
      detailed_changes+="- Implemented working Contact Energy usage data endpoint\n"
    fi
    if echo "$api_diff" | grep -q "session.*token\|x-api-key"; then
      detailed_changes+="- Updated authentication headers and session management\n"
    fi
    if echo "$api_diff" | grep -q "InvalidAuth\|CannotConnect\|UnknownError"; then
      detailed_changes+="- Added custom exception classes for better error handling\n"
    fi
  fi

  # Check sensor.py changes
  if git diff $range --name-only | grep -q "custom_components/contact_energy/sensor.py"; then
    local sensor_diff
    sensor_diff=$(git diff $range -- custom_components/contact_energy/sensor.py)
    
    # Check for specific bug fixes and improvements
    if echo "$sensor_diff" | grep -q "mean_type"; then
      detailed_changes+="- Added mean_type parameter to StatisticMetaData for Home Assistant 2026.11 compatibility\n"
    fi
    if echo "$sensor_diff" | grep -q "len(response) > 0\|response.*and.*len"; then
      detailed_changes+="- Added validation to only process API responses containing actual data points\n"
    fi
    if echo "$sensor_diff" | grep -q "timedelta(days=60)"; then
      detailed_changes+="- Increased daily chart sensor data collection period from 30 to 60 days\n"
    fi
    if echo "$sensor_diff" | grep -q "ISO.*8601\|strftime.*%Y-%m-%dT%H:%M:%SZ"; then
      detailed_changes+="- Changed daily chart sensors to use ISO 8601 datetime format with timestamps at 23:59:59\n"
    fi
    if echo "$sensor_diff" | grep -q "delta.*=.*abs\|abs.*float.*val.*-.*prev"; then
      detailed_changes+="- Converted chart sensor values from cumulative totals to delta values (daily usage)\n"
    fi
    
    # Generic changes (only add if no specific changes detected above)
    if [[ -z "$detailed_changes" ]]; then
      if echo "$sensor_diff" | grep -q "StatisticData\|StatisticMetaData\|async_add_external_statistics"; then
        detailed_changes+="- Updated statistics handling in sensor implementation\n"
      fi
    fi
  fi

  # Check coordinator.py changes
  if git diff $range --name-only | grep -q "custom_components/contact_energy/coordinator.py"; then
    local coord_diff
    coord_diff=$(git diff $range -- custom_components/contact_energy/coordinator.py)
    if echo "$coord_diff" | grep -q "DataUpdateCoordinator"; then
      detailed_changes+="- Implemented 8-hour polling DataUpdateCoordinator\n"
    fi
    if echo "$coord_diff" | grep -q "28800\|8.*hour"; then
      detailed_changes+="- Configured 8-hour data refresh interval\n"
    fi
  fi

  # Check __init__.py changes
  if git diff $range --name-only | grep -q "custom_components/contact_energy/__init__.py"; then
    local init_diff
    init_diff=$(git diff $range -- custom_components/contact_energy/__init__.py)
    
    # Check for specific bug fixes
    if echo "$init_diff" | grep -q "async def _restart_wrapper\|_restart_wrapper"; then
      detailed_changes+="- Fixed async thread safety issue with hass.async_create_task in daily restart scheduler\n"
    fi
    if echo "$init_diff" | grep -q "async_call_later\|call_soon_threadsafe"; then
      detailed_changes+="- Replaced lambda function with proper async wrapper to prevent RuntimeError\n"
    fi
    
    # Generic changes (only add if no specific changes detected)
    if [[ -z "$detailed_changes" ]] && echo "$init_diff" | grep -q "async_setup_entry\|async_unload_entry"; then
      detailed_changes+="- Updated integration setup and unload procedures\n"
    fi
  fi

  # Check strings/translations changes
  if git diff $range --name-only | grep -q "strings.json\|translations"; then
    detailed_changes+="- Updated user interface strings and translations\n"
  fi
  
  # Check README and documentation changes
  if git diff $range --name-only | grep -q "README.md"; then
    local readme_diff
    readme_diff=$(git diff $range -- README.md)
    
    if echo "$readme_diff" | grep -q "60.*day\|60-day"; then
      detailed_changes+="- Updated README documentation to reflect 60-day data collection capability\n"
    fi
    if echo "$readme_diff" | grep -q "WIP\|work.*progress" || echo "$readme_diff" | grep -qE "^-.*WIP"; then
      detailed_changes+="- Removed work-in-progress notes from documentation\n"
    fi
    if echo "$readme_diff" | grep -q "image-1.png\|screenshot"; then
      detailed_changes+="- Updated daily usage chart screenshot with current visualization\n"
    fi
    if [[ -z "$detailed_changes" ]]; then
      detailed_changes+="- Documentation updates\n"
    fi
  fi
  
  # Check ApexCharts example changes
  if git diff $range --name-only | grep -q "ApexCharts.*yaml"; then
    detailed_changes+="- Updated ApexCharts card configuration examples\n"
  fi
  
  # Check asset/image changes
  if git diff $range --name-only | grep -q "assets/.*\.png"; then
    if [[ ! "$detailed_changes" =~ "screenshot" ]]; then
      detailed_changes+="- Updated integration screenshots and visual assets\n"
    fi
  fi

  # Check manifest/metadata changes
  if git diff $range --name-only | grep -q "manifest.json\|hacs.json"; then
    local meta_diff
    meta_diff=$(git diff $range -- custom_components/contact_energy/manifest.json hacs.json 2>/dev/null || true)
    if echo "$meta_diff" | grep -q "iot_class.*cloud_polling"; then
      detailed_changes+="- Added cloud_polling IoT class designation\n"
    fi
    # Skip version updates as they're automatic in releases
  fi

  # If no specific changes detected, use generic analysis
  if [[ -z "$detailed_changes" ]]; then
    local files
    mapfile -t files < <(git diff --name-only $range)
  local have_config="" have_api="" have_setup="" have_consts="" have_meta="" have_i18n="" have_docs="" have_sensors="" have_coordinator=""
    for f in "${files[@]}"; do
      [[ "$f" =~ ^custom_components/contact_energy/config_flow\.py$ ]] && have_config=1
      [[ "$f" =~ ^custom_components/contact_energy/api\.py$ ]] && have_api=1
      [[ "$f" =~ ^custom_components/contact_energy/__init__\.py$ ]] && have_setup=1
      [[ "$f" =~ ^custom_components/contact_energy/const\.py$ ]] && have_consts=1
      [[ "$f" =~ ^(custom_components/contact_energy/manifest\.json|hacs\.json)$ ]] && have_meta=1
      [[ "$f" =~ ^(custom_components/contact_energy/(strings\.json|translations/.+\.json))$ ]] && have_i18n=1
      [[ "$f" =~ ^README\.md$ || "$f" =~ ^CHANGELOG\.md$ ]] && have_docs=1
      [[ "$f" =~ ^custom_components/contact_energy/sensor\.py$ ]] && have_sensors=1
      [[ "$f" =~ ^custom_components/contact_energy/coordinator\.py$ ]] && have_coordinator=1
    done

  if [[ -n "${have_config}" ]]; then detailed_changes+="- Config flow and validation improvements\n"; fi
  if [[ -n "${have_api}" ]]; then detailed_changes+="- API client updates and enhancements\n"; fi
  if [[ -n "${have_setup}" ]]; then detailed_changes+="- Integration setup/unload adjustments\n"; fi
  if [[ -n "${have_consts}" ]]; then detailed_changes+="- Constants and configuration updates\n"; fi
  if [[ -n "${have_meta}" ]]; then detailed_changes+="- Metadata and manifest updates\n"; fi
  if [[ -n "${have_i18n}" ]]; then detailed_changes+="- User interface translations updated\n"; fi
  if [[ -n "${have_docs}" ]]; then detailed_changes+="- Documentation updates\n"; fi
  if [[ -n "${have_sensors}" ]]; then detailed_changes+="- Sensor platform implementation\n"; fi
  if [[ -n "${have_coordinator}" ]]; then detailed_changes+="- Data coordination updates\n"; fi
  fi

  local entry=""
  if [[ -n "$detailed_changes" ]]; then
    entry+=$'### Changes\n\n'
    # Convert bullet character • to standard Markdown dash -
    detailed_changes=$(echo "$detailed_changes" | sed 's/^•/-/g' | sed 's/^\([[:space:]]*\)•/\1-/g')
    entry+="$detailed_changes\n"
  fi


  if [[ -z "$entry" ]]; then
    entry="No relevant changes."
  fi
  echo -e "$entry"
}

# Build detailed changelog entry including uncommitted working directory changes
build_changelog_from_working_changes() {
  local range="$1"

  # Analyze specific changes for detailed descriptions
  local detailed_changes=""
  
  # Analyze both committed and working directory changes
  local all_changed_files
  mapfile -t all_changed_files < <(git diff --name-only $range 2>/dev/null; git status --porcelain | awk '{print $2}')
  
  # Check each file type for specific changes
  for file in "${all_changed_files[@]}"; do
    [[ -z "$file" ]] && continue
    case "$file" in
      custom_components/contact_energy/config_flow.py)
        # Analyze config flow changes
        if git diff $range HEAD -- "$file" 2>/dev/null | grep -q "domain = DOMAIN" || git diff HEAD -- "$file" 2>/dev/null | grep -q "domain = DOMAIN"; then
          detailed_changes+="- Fixed critical config flow registration bug (domain attribute fix)\n"
        fi
        if git diff $range HEAD -- "$file" 2>/dev/null | grep -q "duplicate.*import\|import.*duplicate" || git diff HEAD -- "$file" 2>/dev/null | grep -q "duplicate.*import"; then
          detailed_changes+="- Removed duplicate import statements in config flow\n"
        fi
        if [[ -z "$detailed_changes" ]]; then
          detailed_changes+="- Config flow validation and UI improvements\n"
        fi
        ;;
      custom_components/contact_energy/api.py)
        detailed_changes+="- API client enhancements and authentication improvements\n"
        ;;
      custom_components/contact_energy/sensor.py)
        detailed_changes+="- Energy Dashboard sensor implementation and statistics integration\n"
        ;;
      custom_components/contact_energy/coordinator.py)
        detailed_changes+="- DataUpdateCoordinator implementation with 8-hour polling\n"
        ;;
      custom_components/contact_energy/__init__.py)
        detailed_changes+="- Integration setup and platform initialization\n"
        ;;
      custom_components/contact_energy/strings.json|custom_components/contact_energy/translations/*)
        detailed_changes+="- User interface strings and translations updated\n"
        ;;
      custom_components/contact_energy/manifest.json|hacs.json)
        detailed_changes+="- Integration metadata and version updates\n"
        ;;
      README.md|CHANGELOG.md)
        detailed_changes+="- Documentation and changelog updates\n"
        ;;
    esac
  done

  local entry=""
  if [[ -n "$detailed_changes" ]]; then
    entry+=$'### Changes\n\n'
    # Convert bullet character • to standard Markdown dash -
    detailed_changes=$(echo "$detailed_changes" | sed 's/^•/-/g' | sed 's/^\([[:space:]]*\)•/\1-/g')
    entry+="$detailed_changes\n"
  fi

  # Add note about uncommitted changes if any
  if git status --porcelain | grep -q .; then
    entry+=$'\n**Note**: This release includes uncommitted changes from the working directory.\n'
  fi

  if [[ -z "$entry" ]]; then
    entry="No relevant changes."
  fi
  echo -e "$entry"
}

# Write changelog (removes existing section for version and prepends fresh one)
write_changelog_section() {
  local version="$1"
  local entry_text="$2"
  
  # Strip any version headers from entry_text to avoid duplicates
  # Remove lines like "## [0.4.1] - 2025-11-10" or "## 0.4.1" or "## [0.4.1]"
  entry_text=$(echo "$entry_text" | sed -E '/^##[[:space:]]*(\[)?[0-9]+\.[0-9]+\.[0-9]+(\])?([[:space:]]*-[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2})?[[:space:]]*$/d')
  
  # Ensure header exists
  if [[ ! -f CHANGELOG.md || ! $(grep -m1 -E '^# Changelog' -n CHANGELOG.md) ]]; then
    echo -e "# Changelog\n" > CHANGELOG.md
  fi
  # Remove existing section for this version: from header to next header or EOF
  if [[ -f CHANGELOG.md ]]; then
    awk -v ver="## $version" '
      BEGIN {del=0}
      $0==ver {del=1; next}
      del && /^## [0-9]+\.[0-9]+\.[0-9]+/ {del=0}
      !del {print}
    ' CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md
  fi
  # Prepend fresh section without date, after the header line
  awk -v ver="## $version" -v notes="$entry_text" '
    BEGIN {printed=0}
    NR==1 && $0 ~ /^# Changelog/ {
      print $0
      print ""
      print ver
      print ""
      # notes may contain backslashes/newlines; split by \n safely below
      n=split(notes, arr, "\n");
      for(i=1;i<=n;i++){ print arr[i] }
      print ""
      printed=1
      next
    }
    { print }
  ' CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md
}

# Create GitHub release using CLI
github_release() {
  local version="$1"
  local entry_text="$2"
  # Allow opt-out to avoid notifications
  if [[ "${RELEASE_SKIP_GH:-}" == "1" ]]; then
    echo "Skipping GitHub release (RELEASE_SKIP_GH=1)" >&2
    return 0
  fi
  
  # Check if gh CLI is available
  if ! command -v gh &> /dev/null; then
    echo "Warning: GitHub CLI (gh) not found. Skipping GitHub release creation." >&2
    echo "Install gh CLI from: https://cli.github.com/" >&2
    return 0  # Don't fail the whole release if gh is missing
  fi
  
  # Check if gh is authenticated
  if ! gh auth status &> /dev/null; then
    echo "Warning: GitHub CLI not authenticated. Skipping GitHub release creation." >&2
    echo "Run: gh auth login" >&2
    return 0  # Don't fail the whole release if not authenticated
  fi
  
  local draft_flag=""
  if [[ "${RELEASE_DRAFT:-}" == "1" ]]; then
    draft_flag="--draft"
  fi

  if gh release view "$version" >/dev/null 2>&1; then
    echo "Release $version already exists. Updating..."
    # If requested, keep or set as draft on edit as well
    if ! gh release edit "$version" --title "$version" --notes "$entry_text" ${draft_flag}; then
      echo "Error: Failed to edit GitHub release $version" >&2
      return 1
    fi
    echo "Release $version updated successfully."
  else
    echo "Creating new release $version..."
    if ! gh release create "$version" --title "$version" --notes "$entry_text" ${draft_flag}; then
      echo "Error: Failed to create GitHub release $version" >&2
      return 1
    fi
    echo "Release $version created successfully."
  fi
  return 0
}

# Commit, tag, push
commit_and_release() {
  local version="$1"
  local entry_text="$2"
  
  # Check if we're on a branch (not detached HEAD)
  if ! git symbolic-ref -q HEAD >/dev/null; then
    echo "Error: Detached HEAD state detected. Cannot push to remote." >&2
    echo "Creating release tag locally and will attempt GitHub release..." >&2
  fi
  
  git add .
  if ! git diff --cached --quiet; then
    git commit -m "Release $version"
    # Only push if we're on a branch
    if git symbolic-ref -q HEAD >/dev/null; then
      if ! git push; then
        echo "Warning: Failed to push commit to remote. Continuing with tag..." >&2
      fi
    else
      echo "Skipping git push (detached HEAD). Tag will be pushed separately." >&2
    fi
  else
    echo "No changes to commit."
  fi
  
  # Tag handling: force-update if exists; allow opting out of remote push
  if git rev-parse -q --verify "refs/tags/$version" >/dev/null; then
    git tag -fa "$version" -m "Release $version"
    if [[ "${RELEASE_SKIP_TAG_PUSH:-}" != "1" ]]; then
      if ! git push --force origin "$version"; then
        echo "Error: Failed to push tag to remote." >&2
        exit 1
      fi
    else
      echo "Skipping remote tag push (RELEASE_SKIP_TAG_PUSH=1)" >&2
    fi
  else
    git tag -a "$version" -m "Release $version"
    if [[ "${RELEASE_SKIP_TAG_PUSH:-}" != "1" ]]; then
      if ! git push origin "$version"; then
        echo "Error: Failed to push tag to remote." >&2
        exit 1
      fi
    else
      echo "Skipping remote tag push (RELEASE_SKIP_TAG_PUSH=1)" >&2
    fi
  fi
  
  # Create GitHub release (this is independent of git push)
  echo "Creating GitHub release for $version..."
  if ! github_release "$version" "$entry_text"; then
    echo "Error: Failed to create GitHub release." >&2
    exit 1
  fi
  echo "GitHub release created successfully!"
  
  # Cleanup temporary release files
  echo "Cleaning up temporary release files..."
  rm -f .allow_release .release-owners .release_summary_* || true
  echo "Cleanup completed."
}

# Main script logic
main() {
  if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <version> [summary-file]"
    exit 1
  fi

  # Rebuild mode regenerates changelog and release notes for all existing tags
  if [[ "$1" == "rebuild" ]]; then
    echo -e "# Changelog\n" > CHANGELOG.md
    mapfile -t tags < <(git tag --sort=version:refname)
    local prev=""
    for t in "${tags[@]}"; do
      local range
      if [[ -n "$prev" ]]; then
        range="$prev..$t"
      else
        range="$(git hash-object -t tree /dev/null)..$t"
      fi
      local entry_text
      entry_text=$(build_changelog_from_range "$range")
      write_changelog_section "$t" "$entry_text"
      github_release "$t" "$entry_text"
      prev="$t"
    done
    git add CHANGELOG.md
    if ! git diff --cached --quiet; then
      git commit -m "chore: rebuild changelog and release notes"
      git push
    fi
    exit 0
  fi

  local version="$1"
  local summary_file=""
  if [ "$#" -eq 2 ]; then
    summary_file="$2"
  fi

  # Enforce release guardrails
  check_release_guards "$version"

  # Step 1: Use agent-provided summary if available
  local entry_text=""
  if [[ -n "$summary_file" && -f "$summary_file" ]]; then
    entry_text=$(cat "$summary_file")
  elif [[ -n "${AGENT_CHANGE_SUMMARY:-}" ]]; then
    entry_text="${AGENT_CHANGE_SUMMARY}"
  else
    # Fallback: Compute changelog from code analysis
    local prev_tag
    prev_tag=$(git tag --sort=version:refname | tail -n 1 || true)
    local range
    if [[ -n "$prev_tag" ]]; then
      range="$prev_tag..HEAD"
    else
      range="$(git hash-object -t tree /dev/null)..HEAD"
    fi
    if git diff --quiet && git diff --cached --quiet; then
      entry_text=$(build_changelog_from_range "$range")
    else
      entry_text=$(build_changelog_from_working_changes "$range")
    fi
  fi

  # Step 2: Write changelog with the agent summary or fallback
  write_changelog_section "$version" "$entry_text"

  # Step 3: Update version numbers in files
  update_version_in_files "$version"

  # Step 4: Commit all changes including the changelog
  commit_and_release "$version" "$entry_text"

  # Cleanup approval file to avoid accidental re-use
  rm -f .allow_release || true
}

main "$@"