#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	cat >&2 <<USAGE
Usage:
	$0 <x.y.z> mikey     # explicit version
	$0 mikey             # auto-bump patch from current version
	$0 auto mikey        # auto-bump patch (alias)
USAGE
	exit 2
}

# -------- helpers --------
TAG_CREATED=0

semver_cmp() {
	local a b a1 a2 a3 b1 b2 b3 IFS=.
	a="$1"; b="$2"
	read -r a1 a2 a3 <<<"$a"; read -r b1 b2 b3 <<<"$b"
	a1=${a1:-0}; a2=${a2:-0}; a3=${a3:-0}; b1=${b1:-0}; b2=${b2:-0}; b3=${b3:-0}
	(( a1 < b1 )) && { echo -1; return; }
	(( a1 > b1 )) && { echo 1; return; }
	(( a2 < b2 )) && { echo -1; return; }
	(( a2 > b2 )) && { echo 1; return; }
	(( a3 < b3 )) && { echo -1; return; }
	(( a3 > b3 )) && { echo 1; return; }
	echo 0
}

semver_bump_patch() {
	local v="$1" x y z IFS=.
	read -r x y z <<<"$v"; x=${x:-0}; y=${y:-0}; z=${z:-0}
	echo "$x.$y.$((z+1))"
}

extract_manifest() {
	grep -E '"version"\s*:\s*"[0-9]+\.[0-9]+\.[0-9]+"' custom_components/contact_energy/manifest.json \
		| sed -E 's/.*"version"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/' | head -n1 || true
}
extract_hacs() {
	grep -E '"version"\s*:\s*"[0-9]+\.[0-9]+\.[0-9]+"' hacs.json \
		| sed -E 's/.*"version"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/' | head -n1 || true
}
extract_readme() {
	grep -E '<strong>version:</strong>\s*[0-9]+\.[0-9]+\.[0-9]+' README.md \
		| sed -E 's/.*version:<\/strong>\s*([0-9]+\.[0-9]+\.[0-9]+).*/\1/' | head -n1 || true
}
extract_changelog() {
	grep -E '^##\s+[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md 2>/dev/null \
		| head -n1 | sed -E 's/^##\s+([0-9]+\.[0-9]+\.[0-9]+).*/\1/' || true
}

majority_version() {
	local values=()
	local v
	v=$(extract_manifest);  [[ -n "$v" ]] && values+=("$v")
	v=$(extract_hacs);      [[ -n "$v" ]] && values+=("$v")
	v=$(extract_readme);    [[ -n "$v" ]] && values+=("$v")
	v=$(extract_changelog); [[ -n "$v" ]] && values+=("$v")
	if (( ${#values[@]} == 0 )); then echo "0.0.0"; return; fi

	# count occurrences
	declare -A count=()
	local best="" best_count=0
	for ver in "${values[@]}"; do
		(( count[$ver]++ )) || true
		if (( count[$ver] > best_count )); then best="$ver"; best_count=${count[$ver]}; fi
		if (( count[$ver] == best_count )); then
			if [[ -n "$best" ]]; then
				local cmp; cmp=$(semver_cmp "$ver" "$best")
				[[ "$cmp" == 1 ]] && best="$ver"
			fi
		fi
	done
	echo "$best"
}

# -------- args parsing --------
VERSION=""
TOKEN=""
AUTO=0

case $# in
	1)
		if [[ "$1" == "mikey" ]]; then
			TOKEN="mikey"; AUTO=1
		else
			usage
		fi
		;;
	2)
		if [[ "$1" == "auto" ]]; then
			AUTO=1; VERSION=""; TOKEN="$2"
		else
			VERSION="$1"; TOKEN="$2"
		fi
		;;
	*) usage ;;
esac

[[ "$TOKEN" == "mikey" ]] || { echo "Error: unauthorized. Second argument must be 'mikey'." >&2; exit 2; }

if (( AUTO )); then
	CUR=$(majority_version)
	[[ -z "$CUR" ]] && CUR="0.0.0"
	VERSION=$(semver_bump_patch "$CUR")
fi

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Error: version must be semantic (x.y.z). Got: '$VERSION'" >&2; exit 2; }

echo "ok: args validated (version=$VERSION, token=$TOKEN)"
if (( AUTO )); then
	echo "auto-bumped from $(majority_version) to $VERSION"
fi

# -------- apply version to files (no commit/tag here) --------

apply_manifest() {
	local f="custom_components/contact_energy/manifest.json"
	if [[ -f "$f" ]]; then
		if grep -qE '"version"\s*:\s*"[0-9]+\.[0-9]+\.[0-9]+"' "$f"; then
			sed -E -i "s/(\"version\"\s*:\s*\")[0-9]+\.[0-9]+\.[0-9]+(\")/\1$VERSION\2/" "$f"
			echo "updated: $f -> $VERSION"
		else
			echo "warn: version field not found in $f" >&2
		fi
	fi
}

apply_hacs() {
	local f="hacs.json"
	if [[ -f "$f" ]]; then
		if grep -qE '"version"\s*:\s*"[0-9]+\.[0-9]+\.[0-9]+"' "$f"; then
			sed -E -i "s/(\"version\"\s*:\s*\")[0-9]+\.[0-9]+\.[0-9]+(\")/\1$VERSION\2/" "$f"
			echo "updated: $f -> $VERSION"
		else
			echo "warn: version field not found in $f" >&2
		fi
	fi
}

apply_readme() {
	local f="README.md"
	if [[ -f "$f" ]]; then
		if grep -qE '<strong>version:</strong>\s*[0-9]+\.[0-9]+\.[0-9]+' "$f"; then
			sed -E -i "s#(<strong>version:</strong>)\s*[0-9]+\.[0-9]+\.[0-9]+#\1 $VERSION#" "$f"
			echo "updated: $f version line -> $VERSION"
		else
			echo "warn: README version line not found" >&2
		fi
	fi
}

scaffold_changelog() {
	local f="CHANGELOG.md"
	if [[ -f "$f" ]]; then
		if grep -q "^## $VERSION" "$f"; then
			echo "changelog: section for $VERSION already exists"
		else
			tmp=$(mktemp)
			{
				printf '## %s\n\n' "$VERSION"
				printf '### Changes\n\n- TBA\n\n'
				cat "$f"
			} > "$tmp"
			mv "$tmp" "$f"
			echo "changelog: scaffolded section for $VERSION"
		fi
	else
		# create a minimal changelog with the new version
		printf '# Changelog\n\n## %s\n\n### Changes\n\n- TBA\n' "$VERSION" > "$f"
		echo "changelog: created $f with section $VERSION"
	fi
}

apply_manifest
apply_hacs
apply_readme
scaffold_changelog

echo "files updated for version $VERSION (no commit performed)"

# -------- commit changes (versioned files only) --------
commit_release() {
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		echo "warn: not a git repository; skipping commit" >&2
		return 0
	fi

	local files=(
		"custom_components/contact_energy/manifest.json"
		"hacs.json"
		"README.md"
		"CHANGELOG.md"
	)

	# Stage only the intended files
	git add -- "${files[@]}" || true

	if git diff --cached --quiet -- "${files[@]}"; then
		echo "git: no changes to commit for $VERSION"
		return 0
	fi

	git commit -m "Release $VERSION" -- "${files[@]}"
	echo "git: committed Release $VERSION"
}

commit_release

# -------- create tag if missing (no push) --------
create_tag() {
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		echo "warn: not a git repository; skipping tag" >&2
		return 0
	fi
	if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null 2>&1; then
		echo "git: tag $VERSION already exists; skipping"
		TAG_CREATED=0
		return 0
	fi
	git tag -a "$VERSION" -m "Release $VERSION"
	echo "git: created tag $VERSION"
	TAG_CREATED=1
}

create_tag

# -------- ensure on main, sync, and push --------
ensure_on_main() {
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		echo "warn: not a git repository; skipping branch checks" >&2
		return 0
	fi
	local cur
	cur=$(git symbolic-ref --quiet --short HEAD || echo "")
	if [[ "$cur" != "main" ]]; then
		echo "git: current branch is '$cur', switching to 'main'"
		git fetch --all --prune || true
		# Ensure local main exists
		if ! git show-ref --verify --quiet refs/heads/main; then
			git checkout -b main origin/main
		else
			git checkout main
		fi
		if [[ -n "$cur" ]]; then
			# Merge current branch into main (fast-forward if possible)
			if git merge --ff-only "$cur" 2>/dev/null; then
				echo "git: fast-forwarded main from '$cur'"
			else
				git merge --no-edit "$cur"
				echo "git: merged '$cur' into main"
			fi
		fi
	fi
}

sync_with_remote() {
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		return 0
	fi
	if ! git remote get-url origin >/dev/null 2>&1; then
		echo "warn: no 'origin' remote; skipping pull/push" >&2
		return 0
	fi
	git fetch origin --prune || true
	# Try fast-forward pull; if not possible, leave as-is (manual intervention later)
	if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
		: # HEAD not ancestor of origin/main; continue
	fi
	if git merge-base --is-ancestor HEAD origin/main 2>/dev/null && \
		 ! git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
		# Local behind remote
		if git pull --ff-only origin main; then
			echo "git: fast-forwarded main from origin/main"
		else
			echo "warn: cannot fast-forward pull; manual rebase/merge required" >&2
		fi
	fi
}

push_changes() {
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		return 0
	fi
	if git remote get-url origin >/dev/null 2>&1; then
		# Push branch (may be up to date)
		if git push origin main; then
			echo "git: pushed main to origin"
		else
			echo "warn: failed to push main" >&2
		fi
		# Push tag
		if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null 2>&1; then
			if git push origin "refs/tags/$VERSION"; then
				echo "git: pushed tag $VERSION to origin"
			else
				echo "warn: failed to push tag $VERSION" >&2
			fi
		fi
	fi
}

ensure_on_main
sync_with_remote
push_changes

# -------- GitHub release (only if tag was created now) --------
extract_changelog_section() {
	local f="CHANGELOG.md"
	if [[ ! -f "$f" ]]; then
		return 1
	fi
	awk -v ver="$VERSION" '
		$0 ~ "^## " ver "$" {flag=1; next}
		flag && /^## [0-9]+\.[0-9]+\.[0-9]+/ {flag=0}
		flag {print}
	' "$f"
}

maybe_create_github_release() {
	# Only proceed if we created the tag in this run
	if [[ "${TAG_CREATED:-0}" != "1" ]]; then
		echo "release: tag $VERSION not newly created; skipping GitHub release create"
		return 0
	fi

	if ! command -v gh >/dev/null 2>&1; then
		echo "warn: GitHub CLI (gh) not found; cannot create GitHub release automatically" >&2
		return 0
	fi

	# Ensure we are authenticated; if not, skip gracefully
	if ! gh auth status >/dev/null 2>&1; then
		echo "warn: gh not authenticated; skipping GitHub release creation" >&2
		return 0
	fi

	# Avoid creating if a release already exists for this tag
	if gh release view "$VERSION" >/dev/null 2>&1; then
		echo "release: GitHub release $VERSION already exists; skipping"
		return 0
	fi

	# Prepare notes from changelog section, fallback to a simple message
	tmp_notes=$(mktemp)
	if body=$(extract_changelog_section); then
		if [[ -n "$body" ]]; then
			printf "%s\n" "$body" > "$tmp_notes"
		else
			printf "Release %s\n" "$VERSION" > "$tmp_notes"
		fi
	else
		printf "Release %s\n" "$VERSION" > "$tmp_notes"
	fi

	# Create the release; --verify-tag ensures tag exists on remote (after push)
	if gh release create "$VERSION" -F "$tmp_notes" -t "$VERSION" --verify-tag >/dev/null; then
		echo "release: created GitHub release $VERSION"
	else
		echo "warn: failed to create GitHub release $VERSION" >&2
	fi

	rm -f "$tmp_notes" || true
}

maybe_create_github_release