# louke v0.6.0

**Layered orchestration + agent permission tightening + three-layer model verification.** `louke 0.6.0` consolidates three rounds of improvements around one theme: **make OpenCode's agent behavior tool-enforced, not prompt-enforced**.

## Highlights

- **`mode: subagent` is now the default for 11 of 12 agents.** `Maestro` is the only `mode: primary` agent; the rest are dispatched via `task` and hidden from `<Leader>a`. Workflow control stays in the AI's hands — users never have to press `Tab` to switch primary agents.
- **Subagent `question` calls bubble to the main window** (verified by manual IDE test, 2026-07-03). Interactive subagents (Scout / Sage / Archer / Judge) can ask clarifying questions in a popup; users answer in the main window without navigating to the child session.
- **5 agents get explicit `permission:` blocks** (YAML object, 11–13 keys) constraining their tool access. Audit/write/read agents can no longer accidentally modify code out of scope — `permission.edit: deny` is now enforced by OpenCode, not by prompt politeness.
- **`lk models doctor` does three-layer verification**: auth-provider filter (from `~/.local/share/opencode/auth.json`) → cost-aware strong/weak match against `opencode models` → optional `--probe` (spawns `opencode run --model <m> ping` to confirm the model is actually callable). `--fix-auto` only writes aliases for `✓` (verified) entries, and prefers free models when multiple candidates exist.
- **`lk upgrade --index <URL>`** lets you pull from Test PyPI or a private index. New `--pre` and `--dry-run` flags round out the upgrade flow.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash
lk --version   # lk 0.6.0
lk agent lint  # 12 agents pass lint (5 with permission)
```

Specific version:

```bash
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash -s -- v0.6.0
```

Upgrade an existing install:

```bash
lk upgrade                                       # default (PyPI)
lk upgrade --index https://test.pypi.org/simple/ # Test PyPI
lk upgrade --dry-run                              # preview the pip command
```

Dev (editable, from source):

```bash
bash install.sh --editable
```

> macOS / Linux only. Windows users: WSL2 or Docker; see README §Install.

## What's in this release

### 1. Agent permission tightening (v0.6-009 FR-0010 ~ FR-0050)

- 4 roles (Warden / Judge / Archer / Librarian) + Maestro get explicit `permission:` blocks
- `permission:` is a YAML object, **not** a comma-separated string (the earlier `permissions:` field name was wrong — OpenCode 1.1.1+ renamed it to singular)
- All `permission` keys are from OpenCode's whitelist: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop` (13 keys, with `todowrite` explicitly excluded because OpenCode controls it internally)
- 4 roles show **11 keys** (4–5 allow + 6–7 deny); Maestro shows **13 keys** (7 allow + 1 ask + 5 deny)
- 4 interactive subagents get `permission.question: allow`; 5 non-interactive subagents + Maestro get `permission.question: deny`

### 2. Layered orchestration (v0.6-009 FR-0060)

- `Maestro` is `mode: primary`; the other 11 agents are `mode: subagent`
- OpenCode's `mode: subagent` behavior: not in `<Leader>a` list, not in Tab cycle, can only be invoked via `task` or `@` mention
- This enforces "Maestro 自主推进" — humans can no longer accidentally break the workflow by switching to a non-Maestro primary agent
- `Maestro`'s `permission:` block explicitly includes `task: allow` (the only way to dispatch subagents)
- `lk init` continues to set `default_agent: maestro` (v0.6-008 FR-0300)

### 3. Interactive subagent behavior (v0.6-009 FR-0070)

- **IDE-tested 2026-07-03**: subagent `question` calls bubble to the Maestro main window. Users see a popup with 1/2/3 options in the main window — no `<Leader>+Down` navigation required.
- 4 interactive subagents (Scout / Sage / Archer / Judge) get `permission.question: allow` plus explicit `AskUser` scenario tables in their prompts (FR-0070.5) listing exactly when to ask vs. assume
- 7 non-interactive subagents (Lex / Devon / Shield / Keeper / Prism / Warden / Librarian) get `permission.question: deny` and run on conservative defaults

### 4. `lk models doctor` three-layer verification (v0.6-008 FR-0201 + 2026-07-03 增补)

- **Auth filter**: reads `~/.local/share/opencode/auth.json` directly (JSON keys = provider IDs); only considers models from authenticated providers
- **Cost-aware matching**: parses `opencode models --verbose` output to build a `{model: (in_cost, out_cost)}` index; `--fix-auto` prefers **free** models (cost 0/0) when multiple strong matches exist
- **Explicit deny**: any tool key not in the `permission` block is explicitly `deny` (does not rely on OpenCode default — which would be `ask` for `external_directory` and `doom_loop`, causing dialogs to interrupt audit/write flows)
- **3-state output**: `✓` (auth + match), `~` (match but provider not authenticated), `✗` (no match)
- **`--probe` flag**: opt-in, runs `opencode run --model <m> ping` (30s timeout) to verify the model is actually callable; demotes `✓` to `✗ (probe failed)` on failure

### 5. `lk upgrade` enhancements (2026-07-03)

- `--index <URL>`: specify a non-default PyPI source (e.g., Test PyPI or a private index)
- `--pre`: allow pre-release / dev versions
- `--dry-run`: preview the pip command without executing
- Unknown options are forwarded to `pip` (e.g., `--force-reinstall`)

### 6. `lk agent lint` (new in v0.6-009 FR-0040)

- Validates source `agents/*.md` frontmatter (schema, `permission` block, OpenCode key whitelist, value enum)
- Enforces the **single primary** constraint: exactly one `mode: primary` agent, must be `maestro`; `mode: all` is rejected as deprecated
- Optional `--check-opencode-version` compares installed OpenCode version against `MIN_OPENCODE_VERSION` (set to `1.1.1` — the version where `permission` object format replaced the deprecated `tools` boolean field)

### 7. Board generation improvements

- `board.py` now passes through a `PASSTHROUGH_KEYS` whitelist (10 fields: `permission`, `hidden`, `color`, `temperature`, `top_p`, `steps`, `disable`) instead of writing only `description` / `mode` / `model`
- `parse_frontmatter` now parses the nested YAML dict format (so `permission:` is correctly round-tripped)
- `--dry-run` warns about unknown frontmatter keys (e.g., `_debug: true`)

## Breaking change

⚠️ Upgrading from any v0.3.x will cause OpenCode's `<Leader>a` list to drop from 12 agents to 1 (Maestro). This is by design — the v0.6-009 design rationale is documented in `.louke/project/specs/v0.6-009-agent-permission-tightening/spec.md` §0.2 and §0.4.

To restore the old behavior, manually edit your project-level `.opencode/agents/*.md` files and change `mode: subagent` to `mode: all` (not recommended).

## Migration from v0.3.0

- The `.louke/wiki/`, `.louke/raw/`, `.louke/project/` directory layout is unchanged
- `lk models.json` location and schema are unchanged (existing aliases still work)
- The `models:` field in `agents/*.md` is still honored (see `lk models doctor` for the new three-layer verification)
- The new `permission:` field is **additive** — existing agents without it continue to work (they get OpenCode's default permission behavior); only the 5 explicitly-listed agents (Maestro, Warden, Judge, Archer, Librarian) have the new constraint

## Out of scope (deferred to v0.6-010+)

- 7 non-interactive subagents' `permission` details (other than the `question: allow/deny` already configured)
- Per-file `edit` allowlists in OpenCode (no upstream support; relying on prompt-level path constraints)
- `lk` Homebrew formula
- TestPyPI shadow releases
- Windows-native installer

## Spec & docs

- `.louke/project/specs/v0.6-009-agent-permission-tightening/spec.md` — full spec (FR-0010 ~ FR-0070, NFR-0010 ~ NFR-0050)
- `.louke/project/specs/v0.6-009-agent-permission-tightening/acceptance.md` — acceptance criteria
- `.louke/project/specs/v0.6-008-louke-v030-usability-closure/spec.md` — FR-0200 marked as `SUPERSEDED by v0.6-009 FR-0060.2`
- `.louke/qwen-review-v0.6-009.md` — full review discussion between Kilo and Qwen
- `README.md` §6.1 (Agent Permissions) and §6.2 (Layered Orchestration) — new sections
- `tests/test_agent_frontmatter.bats` — 20 tests covering schema, mode, permission, board passthrough, lint (all green)
- `tests/test_upgrade_options.bats` — 6 tests covering `--index` / `--pre` / `--dry-run` (all green)

## License

MIT
