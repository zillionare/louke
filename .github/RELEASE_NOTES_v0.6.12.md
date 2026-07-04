# louke v0.6.12

**Patch release (cleanup).** Removes internal spec references (`FR-XXXX`, `v0.X-XXX`, `(v0.5-006)`, `(v0.6-008 FR-0710)`) from the 6 agent prompts that ship to users. These internal spec IDs are useless to end users and look like leaked internal tracking.

## What was cleaned

Internal spec annotations removed from these 6 agent prompts:

| File | Removed annotations |
|---|---|
| `agents/Maestro.md` | `(v0.6-008 FR-0710)`, `(详见 spec FR-0070)`, `(FR-0026 修订)` |
| `agents/Lex.md` | `(FR-0022)`, `(v0.5-006):` (×2), `(默认无 marker = pending, 见 FR-0017)`, `(FR-0022 修订)`, `(v0.5-006 三种形式)`, `(默认 pending, 见 FR-0017)` |
| `agents/Sage.md` | `(FR-0070.5)`, `(v0.5-006 起支持三种形式)`, `(v0.5-006):`, `(FR-0026 修订):`, `(FR-0022 quote dialogue 协议)`, `(违反 FR-0022 协议)` |
| `agents/Archer.md` | `(FR-0070.5)` (section header) |
| `agents/Judge.md` | `(FR-0070.5)` (section header) |
| `agents/Scout.md` | `(FR-0070.5)` (section header) |

## What was kept (intentionally)

These are **examples** showing users how to format their own IDs, not internal references. They belong in shipped prompts:

- `archer-v0.1-001-test-plan` (session-id format example in `## 你的工具` blocks)
- `spec: v0.1-001-init-adopt-mode` (spec-id format example)
- `Issue #42 [FR-0001] xxx` (example issue body showing FR anchor format)
- `(FR-0001, FR-0101, FR-0201, ...)` (numbering convention example)
- `### FR-0100 画一个圆` (tutorial example in Sage.md showing how to write a FR)
- `(\`{#fr-0001}\` 锚点, \`{#ac-fr-0001}\` 锚点)` (format spec for HTML anchors)

## Why this matters

The 12 agent prompts are bundled into the louke PyPI package and shipped to every user. When a user reads `agents/Maestro.md` they should see clear instructions, not `(v0.6-008 FR-0710)` which references an internal project-tracking ID they have no context for. Same for the other annotations — they're internal breadcrumbs that look like leakage.

Aaron's feedback: *"这是要发行出去的版本，怎么能保留内部机密信息"* (this is the version to be released, how can it keep internal confidential info).

## Backward compatibility

- Pure wording cleanup, no behavior change
- No tests needed
- The functional behavior (Maestro's `task` dispatch, `question` tool bubbling, etc.) is unchanged — just without the inline internal spec IDs

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.12
```

## License

MIT
