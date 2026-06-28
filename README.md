# holdpoint

> **Gated specs hold agents accountable.**

![holdpoint pipeline](docs/hero.svg)

[🇨🇳 中文](README.zh.md) · [🇺🇸 English](README.md)

A spec-driven methodology where every stage transition is a machine-enforced hold point. Requirements are tracked at AC-FRXXXX-YY granularity across spec → code → test.

---

### Why holdpoint?

When multiple AI agents work on the same project, things go wrong:

- Two agents edit the same file → merge conflict
- An agent makes an assumption → silent bug
- A test passes but doesn't actually verify → false confidence
- One agent finishes its work but the next can't start because the handoff isn't defined

**The failure mode isn't agents being bad at coding. It's the absence of explicit, tool-enforced handoffs between them.**

`holdpoint` defines 12 specialized agents, a 10-stage pipeline, and an `hp` CLI that makes every transition a real check — not a soft "agent reviews agent". The name is the mechanism: at every **point**, work is **held** until a different agent verifies it.

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

★ **HOLD POINT** — tool-enforced check (`hp` CLI returns 0/1; pipeline doesn't advance until it passes)

**Principle: implementer ≠ reviewer. Always.**

### Install

```bash
git clone https://github.com/your-org/holdpoint
cd holdpoint
pip install -e .
hp --help
```

You now have:
- `hp` CLI (32 commands across 12 agents)
- `agents/` — 14 prompt files, one per role
- `templates/` — 4 doc templates (spec, acceptance, test-plan, security-checklist)
- `tools/` — Python scripts wrapped by `hp`

### Use in Your Project

Copy the framework into your project:

```bash
cd your-project
cp -r /path/to/holdpoint/agents ./
cp -r /path/to/holdpoint/templates ./
```

Or initialize via the CLI:

```bash
hp scout foundation --repo owner/repo --version v0.1 --spec-id v0.1-001-init
# → creates .holdpoint/project/project-info.md
# → creates .holdpoint/project/specs/v0.1-001-init/story.md
# → opens editor for you to fill in story (interactive)
```

`hp scout foundation` walks you through:
1. Step 1 — Collect story/version/repo/DoD (interactive)
2. Step 2 — Create repo + project + permissions
3. Step 3 — Verify gh + git identity
4. Step 4 — Run `hp warden foundation-check` (F1-F11 automated checks)
5. Step 5 — Commit + push

### Use with Your AI Assistant

`agents/*.md` are written as natural-language agent prompts. Any coding agent that reads instructions can use them.

#### OpenCode

Add the framework as a plugin in `~/.config/opencode/opencode.json`:

```json
{"plugin": ["holdpoint"]}
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
1. hp scout foundation            # Initialize project, verify permissions
2. "You are Sage. Interview me about user auth."   # AI plays Sage role
3. hp sage commit-spec --spec ...  # Commit spec + acceptance
4. hp lex verify-acceptance       # [HOLD POINT] Different agent, tool-enforced
5. "You are Archer. Write test-plan + arch + interfaces."
6. hp archer ci-scan              # AC 引用 + 反模式 扫描
7. "You are Devon. Implement in R-G-R."
8. hp devon commit-rgr --phase red/green/refactor
9. hp keeper gate                 # [HOLD POINT] Tool-enforced commit format
10. hp judge security-audit       # [HOLD POINT] S-level security review
11. hp librarian from-raw         # Distill session → wiki
12. hp maestro status             # Check progress
```

Each `★` HOLD POINT returns 0 (pass) or 1 (fail). The pipeline doesn't advance until it passes.

### How It Works: One Spec, End to End

Say you want to build user auth:

1. **M-FOUND** (Scout) — `hp scout foundation` creates the repo, GitHub Project, and a Test Issue to verify permissions.
2. **M-SPEC** (Sage → Lex) — Sage interviews you Socratically (MFA? session timeout? rate limiting?). Lex finds 3 issues. Sage fixes, marks spec locked when **3 signals align**: `hp sage quote-check` exit 0, Lex 3 stages pass, user confirms in IDE.
3. **M-TESTPLAN** (Archer → Sage) — Archer writes `test-plan.md` with 3-layer testing strategy + AC traceability + anti-pattern rules. Sage reviews (it has unique spec context from M-SPEC).
4. **M-ARCH** (Archer → Prism) — Archer writes `architecture.md` + `interfaces.md`. Prism checks spec/code consistency.
5. **M-LOCK** — Spec locked. Implementation begins.
6. **M-DEV** (Devon → Prism → Keeper) — Devon implements in R-G-R. Each commit prefixed `test: red`, `feat: green`, `refactor`. Prism reviews (cynical + test patterns + security quick scan). Keeper runs `hp keeper gate` (commit format + tests).
7. **M-E2E** (Shield → Prism → Keeper) — Shield writes e2e (B-level, simple methods: Playwright/testclient/DB). Same Prism + Keeper.
8. **M-SECURITY** (Judge S-level → User) — `hp judge security-audit` does pattern scan + S-level semantic review. User makes final call.
9. **M-MILESTONE** (Librarian → Maestro) — `hp librarian from-raw` distills the session to wiki. `hp maestro advance --stage M-MILESTONE` closes the milestone.

Each transition is a different agent. Each hold point is tool-enforced. Each handoff is explicit.

### Comparison

| Framework | Spec role | Review model | Agent handoff | Hold point enforcement |
|---|---|---|---|---|
| **spec-kit** (GitHub) | Drives code (single agent) | None | N/A | None |
| **superpowers** (obra, 240k★) | Triggers skills | Subagent reviews | TDD + subagent | TDD (test) |
| **oh-my-openagent** (code-yeongyu, 64k★) | Guides agent | Team of agents | Parallel | Skills + hooks |
| **antigravity-awesome-skills** (1,693+ skills) | (skill library) | None | N/A | None |
| **holdpoint** | **Holds agents accountable** | **Different agent per stage** | **10 stage transitions** | **`hp` CLI tool-enforced** |

The unique claim: **gated specs hold agents accountable via hold points, not just inform them**.

### Architecture (Light)

```
  agents/*.md              templates/*.md                hp/                  tools/*.py
  (12 prompts)            (spec, acceptance,           (32 commands,         (Python scripts,
                         test-plan, security-          12 agents)           wrapped by hp)
                         checklist)
       │                       │                            │                      │
       └───────────┬───────────┴────────────┬───────────────┘                      │
                   │                        │                                      │
                   ↓                        ↓                                      ↓
            AI assistant              Tool-enforced                            wrapped by hp
         (OpenCode, Cursor,           hold points
          Claude Code,                 (hp keeper gate,
          Continue, etc.)               hp judge
                                      security-audit)

  Two-tier memory:
    .holdpoint/raw/    →   episodic, per-agent session records
    .holdpoint/wiki/   →   distilled knowledge, maintained by Librarian
```

- **12 agents** = implementer + reviewer per stage, all distinct
- **`hp` CLI** = tool-enforced hold points (return 0/1)
- **Two-tier memory** = `raw/` (what happened) + `wiki/` (what we know)
- **Traceability** = every test docstring must reference `AC-FRXXXX-YY`; CI scans for it

### License

MIT
