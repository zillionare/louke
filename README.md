# LouKe - beyond vibes, into Louke(craft)

![louke pipeline](docs/hero.png)

[🇨🇳 中文](README.zh.md) · [🇺🇸 English](README.md)

**louke is a multi-agent collaborative development methodology built on spec-first, test-driven, and tool-aligned agent behavior.** Every stage transition is a tool-enforced check.

---

### Supported environments

| Dimension | Supported | Notes |
| --- | --- | --- |
| **OS** | macOS, Linux | **No native Windows.** Use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/) or Docker. `install.sh` self-checks `uname -s` and exits with a clear error otherwise. |
| **IDE / Agent host** | **OpenCode only** (currently) | Claude Code, Cursor, Continue, Copilot, Kilo are **not supported** in this release. The agent prompts are plain Markdown so other hosts *can* read them, but `default_agent` wiring, plugin install paths, and hold-point UX are validated against OpenCode only. |

If you need another host, open an issue — do not assume parity.

---

### Why louke?

You can't build a real software with one-sentence vibecoding.

A real software has hundreds to thousands of sub-requirements, tens of thousands of execution paths and boundary checks.

Real work takes concrete, detailed specs, acceptance criteria, and test plans. Humans must participate in and guide the production of these documents; tools must break them into traceable sub-items so agent code maps one-to-one to those items. Only then can we build a retractable, traceable, trustworthy software production process.

That's the value of louke. Beyond vibecoding — agent programming becomes precision manufacturing, executing every detail you specified perfectly.

When vibecoding:

- You haven't figured out what software you want, yet expect the agent to know
- Words are always suggestive and leave too much room for imagination, but software must be precise
- You have many Stories, but neither AI nor you has formed a complete blueprint

Even spec-kit / superpowers / oh-my-openagent don't turn spec into a "programming contract". For spec to be a contract, three things must hold simultaneously — and louke is the only one that achieves them:

- **Sub-requirements are orthogonal** — non-conflicting and non-overlapping, already pruned by Occam's razor
- **Right-sized granularity** — you can't expect an agent to read a 10,000-word document and still grasp every small detail, unless you break them into items that fit cleanly into a PR
- **Traceable** — every thread from requirement to code to test must be bidirectionally traceable: forward to find the source, backward to find the landing. Any requirement that can't be matched to its code and tests is a blank check hanging on the wall

And the deepest gap between louke and other frameworks: louke turns this into **Infrastructure-as-Checkpoint** — the traceable loop is not in the AI's self-discipline, but in the forced execution of external CLIs at commit-time. `exit 0/1` is an OS process return value; you can't bypass it. The engineering world only recognizes this one language.

### What louke provides

louke turns the contract's three principles into 5 observable things. Each maps to an `lk` command or a traceable artifact — not just prompts, but tools:

- **spec → GitHub issue, commits must reference issue** — Lex converts each FR into an issue; Devon's commit message enforces `#NNN` format. Requirement to code, one-way trace, never lost

- **test ↔ AC-FRXXXX-YY auto-association, CI static validation closes both directions** — every test docstring must carry an `AC-FRXXXX-YY` ID. `lk archer ci-scan` validates at commit-time: every AC must be referenced by a test, every test must reference an AC. If the loop doesn't close, merge is blocked

- **Anti-pattern CI gate + identity consistency check** — `lk keeper gate` statically scans 8 anti-patterns (`assert True` / `try/except: pass` / no-issue skip / mock-framework core / ...). `lk scout identity-check` locks gh/git identity consistency before workflow start. Violations block

- **Project wiki auto-distillation** — based on LLM compounding engineering, `.louke/raw/` (each agent's session records) → `.louke/wiki/` (structured knowledge). Facts, decisions, current state at a glance, lint-checkable

- **Socratic requirement interrogation** — Sage asks multiple rounds of questions around a vague story until it produces traceable `spec.md` + `acceptance.md`

`louke` defines 12 specialized agents, a 10-stage pipeline, and an `lk` CLI — so every transition is a real check, not the soft "agents review each other". Each agent has its own dedicated toolbox; at every hold point, work is gated for verification.

### The Pipeline

| Stage       | Implementer     | Reviewer             | Notes                                                           |
| ----------- | --------------- | -------------------- | --------------------------------------------------------------- |
| M-FOUND     | Scout           | Warden               | Project setup + permission gate                                 |
| M-SPEC      | Sage            | Lex                  | spec + FR → issue, Lex reviews + 100% verifies                  |
| M-TESTPLAN  | Archer          | Sage                 | Test plan (Sage has unique spec context)                        |
| M-ARCH      | Archer          | Prism                | Architecture + interfaces                                       |
| M-LOCK      | Maestro         | User                 | 3-signal lock (Sage quote-parser + Lex 3 stages + User confirm) |
| M-DEV       | Devon           | **Prism → Keeper ★** | Code + unit tests                                               |
| M-E2E       | Shield          | **Prism → Keeper ★** | e2e tests (B-level)                                             |
| M-BUGFIX    | Devon           | **Keeper ★**         | Bug fixes                                                       |
| M-SECURITY  | Judge (S-level) | User                 | Deep security audit                                             |
| M-MILESTONE | Librarian       | Maestro              | raw → wiki distillation                                         |

★ **HOLD POINT** — tool-enforced check (`lk` CLI returns 0/1; pipeline doesn't advance until it passes). `★` only marks the PROD gate that blocks merge at commit-time; stage-transition hold points aren't separately marked.

**Principle: implementer ≠ reviewer. Always.**

### The 12 agents

Default primary model per agent (and in-tier fallback). Override via `~/.louke/models.json` (user) or `.louke/models.json` (project); see `lk models list` / `lk models doctor` for current bindings and `lk models bind <abstract> <full>` to override.

| Agent         | What it does                                          | Tier | Open-source       | Closed-source (reference)               |
| ------------- | ----------------------------------------------------- | :--: | ----------------- | ---------------------------------------- |
| **Maestro**   | Conductor — coordinates the whole pipeline            |  S   | `minimax-m3`      | `gpt-5.6`, `fable`                      |
| **Sage**      | The wise — Socratic questions for requirements         |  S   | `glm-5.2`         | `gpt-5.6`, `fable`                      |
| **Judge**     | Arbiter — S-grade deep security audit                  |  S   | `minimax-m3`      | `gpt-5.6`, `fable`                      |
| **Archer**    | Marksman — designs test-plan + architecture            |  S   | `glm-5.2`         | `gpt-5.6`, `fable`                      |
| **Devon**     | Smith — forges code through R-G-R discipline            |  A   | `kimi-2.7-code`   | `opus-4.8`, `gpt-5.5`                   |
| **Prism**     | Prism — refracts code through anti-pattern + security scan |  A   | `deepseek-v4-pro` | `opus-4.8`, `gpt-5.5`                   |
| **Shield**    | Shield — writes end-to-end test scripts                 |  A   | `kimi-2.6`        | `opus-4.8`, `gpt-5.5`                   |
| **Lex**       | The law — spec-level structural validation             |  B   | `deepseek-v4-flash` | `gpt-5.4-mini`, `gpt-5.4`, `sonnet-4.6` |
| **Warden**    | Gatekeeper — guards the door, confirms exit conditions |  B   | `glm-5`           | `gpt-5.4-mini`, `gpt-5.4`, `sonnet-4.6` |
| **Keeper**    | Warden of gates — enforces quality gates              |  B   | `minimax-2.7`     | `gpt-5.4-mini`, `gpt-5.4`, `sonnet-4.6` |
| **Scout**     | Pathfinder — scouts terrain, verifies preconditions    |  B   | `glm-5`           | `gpt-5.4-mini`, `gpt-5.4`, `sonnet-4.6` |
| **Librarian** | Librarian — distills Wiki, preserves project memory     |  B   | `minimax-2.7`     | `gpt-5.4-mini`, `gpt-5.4`, `sonnet-4.6` |

### Install

> **Platform support**: macOS and Linux only. Windows users: please use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/) or Docker. The installer self-checks `uname -s` and exits with a clear error on unsupported platforms.

```bash
# Standard pip-based install (recommended): auto-creates venv, sets PATH, links lk to ~/.local/bin
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash

# Or pin a version
curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash -s -- v0.3.0

# Or dev mode (clone + editable install)
git clone https://github.com/zillionare/louke
cd louke
./install.sh --editable

# Verify
lk --help
```

`install.sh` does 4 things:

1. Creates an isolated venv at `~/.louke/venv/` (no system-Python pollution)
2. `pip install louke` into that venv
3. `~/.local/bin/lk` → symlink to venv's `lk`, and appends PATH to your shell rc
4. Verifies the install + prints uninstall instructions

Uninstall:

```bash
rm -rf ~/.louke/venv ~/.local/bin/lk
```

You now have:
- `lk` CLI — see `lk --help` for the full command list (12 agents + top-level `init` / `board` / `models`)
- `templates/` — doc templates (spec, acceptance, test-plan, security-checklist, project-info, etc.)
- `louke/_tools/` — Python scripts wrapped by `lk`

### Use in Your Project

Initialize via `lk init`:

```bash
# New project (creates <name>/ dir with .louke/ skeleton + OpenCode agents + issue template + CI workflow)
lk init my-project

# Adopt existing git repo (non-destructive, adds .louke/ alongside your code)
cd ~/work/my-existing-repo
lk init .
```

`lk init` walks you through:
1. Copy agents/templates to `.louke/`
2. Generate `.opencode/agents/*.md` (with resolved `model:` per agent)
3. Write `default_agent: maestro` to `opencode.json`
4. Install `.github/ISSUE_TEMPLATE/feature.yml` (4-digit FR schema)
5. Install `.github/workflows/louke-ci.yml` (AC traceability gate)
6. Resolve abstract model names → `provider/model` via `lk models doctor --fix-auto`

For the M-FOUND foundation step (creating GitHub repo/Project/smoke issue), run `lk scout foundation` after `lk init`.

### Use with Your AI Assistant

> **Currently only OpenCode is supported as the agent host.** See *Supported environments* above. The instructions below assume OpenCode.

#### OpenCode

`lk init` automatically generates `.opencode/agents/*.md` (12 agent files with `model:` frontmatter) and writes `default_agent: maestro` to your project's `opencode.json`. No manual plugin configuration needed.

After install, the default primary agent is **Maestro**, so any new session routes through the pipeline orchestrator. (Maestro will then dispatch to Scout / Sage / Lex / Archer / Devon / Keeper / Judge / Librarian as the workflow demands.)

If you ever need to switch manually inside OpenCode: press `<leader>a` (or `/agents`) and pick Maestro from the list.

### A Working Session

In a typical session with OpenCode, after `lk init` has set `default_agent: maestro`:

1. **Switch to Maestro** (skip if it's already the default): press `<leader>a` and pick **Maestro**.
2. **Tell Maestro what you want**, in plain language. Example:
   > "We need to add user authentication — username + password, plus Google login."
3. **Maestro routes the pipeline automatically**. You stay in the same Maestro chat the whole time — you never manually switch agents. Subagents come and go as helpers; Maestro is the persistent voice.
4. **Subagent questions come back through Maestro**. When Sage asks Socratic questions, or Judge surfaces a security finding, you see them in your Maestro chat and reply there.

What Maestro does behind the curtain:

| Step | What happens | Your role |
| --- | --- | --- |
| 1. M-FOUND | Maestro dispatches **Scout** → `lk scout foundation` | (you watch) |
| 2. M-SPEC | Maestro dispatches **Sage** (interview you) | **answer Sage's questions in the chat** |
| 3. M-TESTPLAN + M-ARCH | Maestro dispatches **Archer** | (silent) |
| 4. M-DEV | Maestro dispatches **Devon** (R-G-R coding) | (silent) |
| 5. M-E2E | Maestro dispatches **Shield** (e2e scripts) | (silent) |
| 6. M-SECURITY | Maestro dispatches **Judge** | **review the S-level report** |
| 7. M-MILESTONE | Maestro dispatches **Librarian** (wiki) | (silent) |

`★` hold points (`lk keeper gate`, `lk judge security-audit`, `lk maestro advance --stage M-*`) are tool-enforced and return 0 (pass) or 1 (fail). Maestro does not advance the pipeline until they pass.

You check progress anytime: `lk maestro status`.

### How It Works: One Spec, End to End

Same example ("add user authentication") as a 9-stage pipeline. Each stage is owned by one agent; transitions are explicit; handoffs are tool-mediated.

1. **M-FOUND** (Scout) — `lk scout foundation` creates the repo, GitHub Project, and a Test Issue to verify permissions.
2. **M-SPEC** (Sage → Lex) — Sage interviews you Socratically (MFA? session timeout? rate limiting?). Lex finds 3 issues. Sage fixes, marks spec locked when **3 signals align**: `lk sage quote-check` exit 0, Lex 3 stages pass, user confirms in IDE.
3. **M-TESTPLAN** (Archer → Sage) — Archer writes `test-plan.md` with 3-layer testing strategy + AC traceability + anti-pattern rules. Sage reviews (it has unique spec context from M-SPEC).
4. **M-ARCH** (Archer → Prism) — Archer writes `architecture.md` + `interfaces.md`. Prism checks spec/code consistency.
5. **M-LOCK** — Spec locked. Implementation begins.
6. **M-DEV** (Devon → Prism → Keeper) — Devon implements in R-G-R. Each commit prefixed `test: red`, `feat: green`, `refactor`. Prism reviews (cynical + test patterns + security quick scan). Keeper runs `lk keeper gate` (commit format + tests).
7. **M-E2E** (Shield → Prism → Keeper) — Shield writes e2e (B-level, simple methods: Playwright/testclient/DB). Same Prism + Keeper.
8. **M-SECURITY** (Judge S-level → User) — `lk judge security-audit` does pattern scan + S-level semantic review. User makes final call.
9. **M-MILESTONE** (Librarian → Maestro) — `lk librarian from-raw` distills the session to wiki. `lk maestro advance --stage M-MILESTONE` closes the milestone.

Each transition is a different agent. Each hold point is tool-enforced. Each handoff is explicit.

### How louke compares

| Framework                                | Is spec a contract?                                                         | Who reviews                                                                  | Enforcement layer                           | spec → code → test loop                                      |
| ---------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------ |
| **spec-kit** (GitHub)                    | spec.md is the source, but no MECE / granularity / traceability constraints | No review                                                                    | None                                        | Manual + social                                              |
| **superpowers** (obra, 240k★)            | plan.md is plain text, no AC numbering, no commit-time validation           | subagent review (same model reviewing itself)                                | prompt-level self-discipline                | TDD indirect guarantee (no ID binding between test and spec) |
| **oh-my-openagent** (code-yeongyu, 64k★) | agents digest spec themselves                                               | team of agents (same LLM, different prompts)                                 | hooks / middleware                          | task self-defined, no FR ↔ test binding                      |
| **louke**                                | FR-XXXX / AC-FRXXXX-YY + `lk archer ci-scan`                                     | 12 different personas (implementer ≠ reviewer, cross-stage context disjoint) | `lk` CLI exit 0/1 (OS process return value) | FR ↔ issue ↔ commit ↔ AC ↔ test end-to-end                   |

### Architecture (Light)

```
  agents/*.md              templates/*.md                louke/                louke/_tools/*.py
  (12 prompts)            (spec, acceptance,           (12 agents +          (Python scripts,
                          test-plan, security-          init/board/models)   wrapped by lk)
                          checklist)
       │                       │                            │                      │
└───────────┬───────────┴────────────┬───────────────┘                      │
                    │                        │                                      │
                    ↓                        ↓                                      ↓
             AI assistant              Tool-enforced                            wrapped by lk
          (OpenCode — only          hold points
           host currently             (lk keeper gate,
           supported)                  lk judge
                                       security-audit)

  Two-tier memory:
    .louke/raw/    →   episodic, per-agent session records
    .louke/wiki/   →   distilled knowledge, maintained by Librarian
```

Four things louke doesn't compromise on:

- **12 Agents** = implementer ≠ reviewer; cross-stage context is disjoint
- **`lk` CLI** = OS-process-level contract; `exit 0/1` is unbypassable
- **Two-tier memory** = `raw/` (episodic) + `wiki/` (distilled), maintained by Librarian
- **Promise** = spec → code → test three-segment bidirectional reachability; breakage at any node can be traced to its source

### Backlog project

`lk scout foundation` creates two GitHub Projects per repo:

- **`{repo}-{version}`** — per-release, tracks the current milestone's issues
- **`{repo}-backlog`** — per-repo (permanent), holds unscheduled user stories / feature ideas

When you create an issue with `gh issue create --no-milestone`, it naturally lands in the backlog. During planning, pull backlog issues into `{repo}-{version}` via `gh project item-add`.

Future enhancements (not in v0.6-008 scope):

- **[#78](https://github.com/zillionare/louke/issues/78)**: `.louke/project` as a standalone private GitHub repo (via git submodule) to separate spec/wiki from public code
- **[#79](https://github.com/zillionare/louke/issues/79)**: `louke serve` web UI for browsing/editing wiki/spec/acceptance

### License

MIT
