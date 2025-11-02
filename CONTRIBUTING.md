# Contributing

Thanks for contributing to Contact Energy! A few project guardrails help us keep releases safe and predictable.

## Enable local Git hooks

We keep our hooks in the `.githooks` directory. To enable them in your local clone, run once:

```bash
git config core.hooksPath .githooks
```

This enables the `pre-push` hook which blocks pushes to `main` that include a version bump without the required release guard files.

## Release guard files

When preparing a release via `./release.sh <version>`:

- `.allow_release` must exist and contain only the target version (e.g. `0.3.21`). The release script can generate/update this for you.
- `.release-owners` must exist and contain either your GitHub username or your noreply email (`<username>@users.noreply.github.com`). Multiple owners can be listed (CSV or whitespace-separated). Lines starting with `#` are treated as comments.
- `CHANGELOG.md` must include a `## <version>` section describing the changes.

Our CI workflow (`.github/workflows/release-guard.yml`) validates these conditions for any pushed tag that looks like a semantic version (e.g. `0.3.21`).

## Version fields to update

- `custom_components/contact_energy/manifest.json` → `version` must match the release tag.
- `hacs.json` → `version` should match the release tag (if present).
- `README.md` → update displayed version badges/strings as needed.

The `release.sh` script automates these updates and will refuse to run if safeguards aren’t met.

## Branching

- All work happens on feature branches. Open a PR into `main`.
- `main` should always be in a releasable state.

## Code style

- Python: follow the existing style and async best practices used in Home Assistant integrations.
- Keep changes minimal and focused; avoid unrelated refactors in release PRs.

## Tests and verification

- When you change behavior that affects sensors or statistics, test locally in Home Assistant if possible.
- For release changes, ensure the guard checks pass locally and in CI before tagging.
