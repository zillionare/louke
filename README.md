# louke

> **beyond vibes, into craft.**

![louke pipeline](docs/hero.svg)

[🇨🇳 中文](README.zh.md) · [🇺🇸 English](README.md)

**louke is a multi-agent collaborative development methodology built on spec-first, test-driven, and tool-aligned agent behavior.** Every stage transition is a machine-enforced hold point. Requirements are tracked at AC-FRXXXX-YY granularity across spec → code → test.

---

### Why louke?

When multiple AI agents work on the same project, things go wrong:

- Two agents edit the same file → merge conflict
- An agent makes an assumption → silent bug
- A test passes but doesn't actually verify → false confidence
- One agent finishes its work but the next can't start because the handoff isn't defined

**The failure mode isn't agents being bad at coding. It's the absence of explicit, tool-enforced handoffs between them.**

`louke` defines 12 specialized agents, a 10-stage pipeline, and an `lk` CLI that makes every transition a real check — not a soft "agent reviews agent". The name is the mechanism: at every **point**, work is **held** until a different agent verifies it.

### The Pipeline

| Stage | Implementer | Reviewer | Notes |
|---|---|---|---|
| M-FOUND | Scout | Warden | Project setup + permission gate |
| M-SPEC | Sage | Lex | Spec + acceptance.md |
| M-TESTPLAN | Archer | Sage | Test plan (Sage has unique spec context) |
| M-ARCH | Archer | Prism | Architecture + interfaces |
| M-LOCK | Maestro | User | 3-signal lock (Sage quote-parser + Lex 3 stages + User confirm) |
| M-DEV | Devon | **Prism → Keeper ★** | Code + unit tests |
| M-E2E | Shield | **Prism → Keeper ★** | e2e tests (B-level) |
| M-BUGFIX | Devon | **Keeper ★** | Bug fixes |
| M-SECURITY | Judge (S-level) | User | Deep security audit |
| M-MILESTONE | Librarian | Maestro | raw → wiki distillation |

★ **HOLD POINT** — tool-enforced check (`lk` CLI returns 0/1; pipeline doesn't advance until it passes)

**Principle: implementer ≠ reviewer. Always.**

### Install

```bash
git clone https://github.com/your-org/louke
cd louke
pip install -e .
lk --help
```

You now have:
- `lk` CLI (32 commands across 12 agents)
- `agents/` — 14 prompt files, one per role
- `templates/` — 4 doc templates (spec, acceptance, test-plan, security-checklist)
- `louke/_tools/` — Python scripts wrapped by `lk`

### Use in Your Project

Copy the framework into your project:

```bash
cd your-project
cp -r /path/to/louke/agents ./
cp -r /path/to/louke/templates ./
```

Or initialize via the CLI:

```bash
lk scout foundation --repo owner/repo --version v0.1 --spec-id v0.1-001-init
# → creates .louke/project/project-info.md
# → creates .louke/project/specs/v0.1-001-init/story.md
# → opens editor for you to fill in story (interactive)
```

`lk scout foundation` walks you through:
1. Step 1 — Collect story/version/repo/DoD (interactive)
2. Step 2 — Create repo + project + permissions
3. Step 3 — Verify gh + git identity
4. Step 4 — Run `lk warden foundation-check` (F1-F11 automated checks)
5. Step 5 — Commit + push

### Use with Your AI Assistant

`agents/*.md` are written as natural-language agent prompts. Any coding agent that reads instructions can use them.

#### OpenCode

Add the framework as a plugin in `~/.config/opencode/opencode.json`:

```json
{"plugin": ["louke"]}
```

#### Claude Code

Place `agents/` under `.claude/agents/` and reference each role via `--agent`:

```bash
claude --agent agents/Sage.md "interview me about user auth"
```

#### VSCode (Cursor / Continue / Copilot)

Add the agent prompts to your rules:

```json
// .continue/config.json
{
  "rules": [
    "agents/Maestro.md",
    "agents/Sage.md",
    "agents/Archer.md"
  ]
}
```

In Cursor: **Settings → Rules → Add file → `agents/Sage.md`**

### A Working Session

In a typical session with one of the above AI assistants:

```
1. lk scout foundation            # Initialize project, verify permissions
2. "You are Sage. Interview me about user auth."   # AI plays Sage role
3. lk sage commit-spec --spec ...  # Commit spec + acceptance
4. lk lex verify-acceptance       # [HOLD POINT] Different agent, tool-enforced
5. "You are Archer. Write test-plan + arch + interfaces."
6. lk archer ci-scan              # AC 引用 + 反模式 扫描
7. "You are Devon. Implement in R-G-R."
8. lk devon commit-rgr --phase red/green/refactor
9. lk keeper gate                 # [HOLD POINT] Tool-enforced commit format
10. lk judge security-audit       # [HOLD POINT] S-level security review
11. lk librarian from-raw         # Distill session → wiki
12. lk maestro status             # Check progress
```

Each `★` HOLD POINT returns 0 (pass) or 1 (fail). The pipeline doesn't advance until it passes.

### How It Works: One Spec, End to End

Say you want to build user auth:

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

### Comparison

| Framework | Spec role | Review model | Agent handoff | Hold point enforcement |
|---|---|---|---|---|
| **spec-kit** (GitHub) | Drives code (single agent) | None | N/A | None |
| **superpowers** (obra, 240k★) | Triggers skills | Subagent reviews | TDD + subagent | TDD (test) |
| **oh-my-openagent** (code-yeongyu, 64k★) | Guides agent | Team of agents | Parallel | Skills + hooks |
| **antigravity-awesome-skills** (1,693+ skills) | (skill library) | None | N/A | None |
| **louke** | **Holds agents accountable** | **Different agent per stage** | **10 stage transitions** | **`lk` CLI tool-enforced** |

The unique claim: **gated specs hold agents accountable via hold points, not just inform them**.

### Architecture (Light)

```
  agents/*.md              templates/*.md                louke/                louke/_tools/*.py
  (12 prompts)            (spec, acceptance,           (32 commands,         (Python scripts,
                         test-plan, security-          12 agents)           wrapped by lk)
                         checklist)
       │                       │                            │                      │
       └───────────┬───────────┴────────────┬───────────────┘                      │
                   │                        │                                      │
                   ↓                        ↓                                      ↓
            AI assistant              Tool-enforced                            wrapped by lk
         (OpenCode, Cursor,           hold points
          Claude Code,                 (lk keeper gate,
          Continue, etc.)               lk judge
                                      security-audit)

  Two-tier memory:
    .louke/raw/    →   episodic, per-agent session records
    .louke/wiki/   →   distilled knowledge, maintained by Librarian
```

- **12 agents** = implementer + reviewer per stage, all distinct
- **`lk` CLI** = tool-enforced hold points (return 0/1)
- **Two-tier memory** = `raw/` (what happened) + `wiki/` (what we know)
- **Traceability** = every test docstring must reference `AC-FRXXXX-YY`; CI scans for it

### License

MIT
