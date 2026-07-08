# louke v0.7.1

**Metadata release — no code changes from v0.7.0.** Aligns the package
`version` field (in `pyproject.toml`) and the top-level `VERSION` file with
the v0.7 release line.

## Why this release

When v0.7.0 was originally tagged (2026-07-06), the in-repo metadata
(`pyproject.toml: version = "0.6.14"`, `VERSION = "0.3.0"`) was stale
relative to the released code. The release workflow
(`.github/workflows/release.yml`) works around this at build time by
syncing `pyproject.toml` from the tag, but the on-disk `VERSION` file and
the committed `pyproject.toml` value remained outdated. v0.7.1 closes
this gap so the in-repo metadata matches what `pip` actually installs.

## What changed

| File | Before | After |
|---|---|---|
| `pyproject.toml` | `version = "0.6.14"` | `version = "0.7.1"` |
| `VERSION` | `0.3.0` | `0.7.1` |

No source files under `louke/` or `agents/` were modified by this release.

## v0.7.0 (re-tagged at main HEAD)

The v0.7.0 Git tag was moved from its original tip (`11cd56a3`) to the
current `main` HEAD (`bdc1a9b`) so that `pip install louke==0.7.0` picks
up the post-release fixes that landed on `main`:

- **v0.7-003 inline-discussion protocol** — replaces the older
  quote-dialogue protocol; adds `lk discuss start/reply` to
  Lex/Archer/Prism; preserves `discuss.py` backward compatibility for the
  ✓ resolved marker.
- **English localization for public release** — public-facing docs and
  agent prompts are now English-first.
- **Agent prompt alignment** (per Qwen review) — fixes `lk <agent>`
  → `lk agent <agent>` command format in agent docs; restores
  quote-check as a business gate in Lex; expands the
  `[--5-tuple]` discussion payload; aligns quote-check semantics with
  v0.7-003.
- **#91 — editable install pinning** — venv `louke` is now pinned to the
  workspace via editable install, with a smoke test guarding the layout.

## Upgrade

```bash
pip install --upgrade louke            # → 0.7.1
pip install --upgrade louke==0.7.0     # → 0.7.0 (now at main HEAD)
```

## Verification

- `lk --version` reports `lk 0.7.1` after upgrade.
- `python -c "import importlib.metadata as m; print(m.version('louke'))"`
  prints `0.7.1`.
