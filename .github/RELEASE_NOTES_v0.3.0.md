# louke v0.3.0

**First public release.** `louke 0.3.0` ships spec-as-contract tooling for multi-agent development: 12 specialized agents orchestrated through a 10-stage pipeline, with `lk` CLI as the tool-enforced hold-point between stages.

## Highlights

- **Spec-as-contract**: every requirement has a unique AC, every AC is bound to a test, every test carries the AC ID in its docstring. `lk archer ci-scan` runs at commit-time and blocks merge if the loop doesn't close.
- **Infrastructure-as-Checkpoint**: `lk` CLI is an external binary, `exit 0/1` is an OS process return value. Holds are tool-enforced, not prompt-enforced. The AI can't decide to skip them.
- **12 distinct personas (implementer ≠ reviewer)**: implementer of one stage is never the reviewer of the same stage. Cross-stage context is disjoint, so reviewer inherits no implementer blind spots.
- **`lk scout foundation`**: one command to bootstrap a project — repo, Project board, identity check, F1–F11 foundation gates, push.
- **Two-tier memory**: `.louke/raw/` for episodic session records; `.louke/wiki/` for distilled knowledge maintained by Librarian.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash
lk --help
```

Specific version:

```bash
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash -s -- v0.3.0
```

Dev (editable, from source):

```bash
bash install.sh --editable
```

> macOS / Linux only. Windows users: WSL2 or Docker; see README §Install.

## What's in this release

This is the first published version. The codebase carried history from a previous internal codename ("holdpoint" / "specforge") which has been fully retired — see git log for `chore: rename holdpoint → louke (Lòukè)` and the v0.6 agent-consolidation commits.

What's working:
- All 12 agents with single-responsibility prompts (`agents/*.md`)
- 10-stage pipeline (M-FOUND through M-MILESTONE) with implementer / reviewer pairing
- `lk` CLI with 32 commands covering one subcommand per agent
- `lk scout foundation` interactive bootstrap
- `lk archer ci-scan` AC ↔ test bidirectional validation
- `lk keeper gate` anti-pattern enforcement (8 classes)
- `lk scout identity-check` git/gh identity consistency (L1–L5)
- `louke/_tools/` Python scripts (formerly `tools/`) — `check_acs.py`, `check_identity.py`, `verify_issue_schema.py`, `verify_acceptance.py`, `quote_parser.py`, `git_diff_quote_resolver.py`
- OpenSpec-style YAML issue template with form-b / form-c acceptance variants
- 129 bats tests covering frontmatter, validation, identity, wiki checks (all green on Python 3.9–3.12)

What's intentionally not in this release:
- Homebrew formula (planned)
- Pre-built platform packages (.deb / .rpm)
- TestPyPI shadow release — for v0.4 onwards
- Windows-native installer — track upstream pip + bash progress

## Upgrading

This is the first public release; no prior versions on PyPI to upgrade from. To migrate from a pre-rename checkout (`holdpoint` / `specforge`), move `.specforge/` to `.louke/`, rename `tools/` references to `louke/_tools/`, and re-run `lk scout identity-check`. The new `agents/` is a 12-agent Roster — see `agents/Maestro.md` if you're coming from a 17- or 19-agent setup.

## License

MIT
