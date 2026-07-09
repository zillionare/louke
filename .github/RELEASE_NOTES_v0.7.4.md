# louke v0.7.4

Patch release. Fixes a long-standing bug in `lk agent lex verify-issue` that
prevented it from reading specs on a non-`main` branch, and removes a stale
package payload that could only ever run in the louke repo itself.

## Highlights

- `lk agent lex verify-issue` now accepts `--branch` (and falls back to the
  project-info `Release Branch` field). Previously the subcommand always
  read `main`, which made Stage 3 validation 404 against any spec living on
  a release branch such as `releases/v0.2`.
- Removed `louke/.github/workflows/{ci,louke-ci,release}.yml` from the
  Python package payload. These were the louke repo's own CI/release
  workflows; they were never copied by `lk init` (it only handles
  `ISSUE_TEMPLATE/`) and never ran for downstream projects, since pip
  installs do not place workflow files into the user's repo. Keeping them
  inside `louke/` only invited confusion — `release.yml` in particular
  would have run `twine upload --skip-existing dist/louke-*` against a
  project owner's empty `PYPI_API_TOKEN` if it had ever been triggered.

## What changed

| Area | Change |
|---|---|
| `lk agent lex verify-issue` | New `--branch` flag; passes the branch through to `verify_issue_schema`. Defaults to the `Release Branch` field from `.louke/project/project.toml` when set. |
| Package payload | `louke/.github/workflows/` removed (3 files, 211 lines deleted). Repo-level `.github/workflows/` for louke itself is unchanged. |
| Tests | `tests/test_fix_094.bats` covers argparser acceptance, subprocess pass-through, and empty-branch handling (3 cases). |

## Verification

- `bats tests/test_fix_094.bats tests/test_issue_form.bats` — 40/40 pass.
- The full lex / issue-form / backward-compat / cli-contract suite passes
  on the release candidate before tagging.

## Migration

No action required for downstream users. The `verify-issue` change is
strictly additive (a flag that was previously missing). The workflow
removal is invisible to anyone who never had these files copied (which
was everyone, since `lk init` never copied them).
