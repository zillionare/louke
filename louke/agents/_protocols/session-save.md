# Session Save Protocol (louke raw session notes)

## 1. Purpose

Save raw records of agent work sessions for the Librarian to later distill into wiki knowledge.

**raw and wiki must not be mixed**:
- raw = episodic memory, preserving trial-and-error and open items
- wiki = distilled knowledge
- raw **does not enter git**, maintained locally only

## 2. When to Use

- At the end of any agent work session
- The session produced non-trivial decisions
- The session tried options that were rejected
- The session left open questions for the next round

## 3. File Path

```
.louke/raw/{yy-mm-dd}/{session-id}.md
```

- `yy-mm-dd` = session date
- `session-id` = `{agent}-{spec-id or phase}-{topic}`
  - e.g. `devon-v0.1-001-task-impl`

## 4. Format

Frontmatter is required:

```markdown
---
date: 2026-06-27
session: devon-v0.1-001-task-impl
agents: [Devon, Prism]
spec: v0.1-001-init-adopt-mode
related_issues: [#142, #143]
status: resolved | superseded | open     # required
supersedes: []
---

## Topic {what is being coordinated/decided}
## Decision {conclusion, in command/file/spec form}
## Tried but abandoned {rejected options and reasons — key input for wiki distillation}
## Open questions {left for the next round}
```

## 5. Constraints

- `status` is required (if omitted, treated as `open`; the Librarian refuses to distill)
- When referenced via `supersedes`, the referenced entry should add `superseded-by` in its frontmatter for bidirectional traceability
- Write before returning the result, but do not block the flow
