---
name: inline-comments
description: When you need to leave structured inline marks in markdown files — quote dialogue, admonitions, or comments — and validate quote dialogue status with louke's parser.
license: MIT
compatibility: opencode
metadata:
  audience: agents
  workflow: louke
---

## What I do

I guide you to leave three kinds of structured inline marks in markdown documents:

1. **Quote dialogue** — multi-agent or agent-to-user discussion using nested blockquotes with speaker tags.
2. **Admonition** — public, non-dialogue callouts such as notes, warnings, or tips.
3. **Comment** — hidden agent notes or TODOs that stay in the source but do not render.

All of them keep discussion, context, and reminders inside project documents instead of scattered chat messages.

## When to use me

- Clarifying FR/NFR boundaries with users or other agents
- Reviewing spec coverage, test plans, interfaces, or architecture
- Any multi-round discussion that must be traceable in project docs
- Leaving a public note that does not belong to a dialogue chain
- Adding a private TODO or reminder for yourself or another agent
- Commenting and replying to comments in any markdown document

## Parse quote dialogue

Louke ships a parser that extracts quote dialogue from markdown files and reports open/resolved/blocked quotes per unit.

Use it to verify that a document is ready before proceeding:

```bash
# Special use case: check whether a spec is ready (exit 0 = all quotes resolved)
lk agent sage quote-check --spec v0.1-001-init

# Direct parser access: text or JSON summary
python -m louke._tools.quote_parser .louke/project/specs/v0.1-001-init/spec.md
python -m louke._tools.quote_parser .louke/project/specs/v0.1-001-init/spec.md --format json

# Check who closed quotes they did not own
python -m louke._tools.quote_parser .louke/project/specs/v0.1-001-init/spec.md --check-violations
```

### Check your personal quote backlog

To see what needs your attention as a specific speaker, use `--for <speaker>`:

```bash
# Via lk CLI
lk agent sage quote-check --spec v0.1-001-init --for Lex

# Direct parser access
python -m louke._tools.quote_parser .louke/project/specs/v0.1-001-init/spec.md --for Lex
```

The report contains three lists:

1. **unanswered** — questions you started (depth 1) that have no reply at all.
2. **unresolved** — questions you started whose latest reply is not `resolved`.
3. **awaiting_my_reply** — quotes where you were `@mentioned` and the latest reply in that thread is neither from you nor `resolved`.

Each item carries a `conversation_id` (SHA256 of the thread's first line) and `first_line` so humans can locate the discussion.

### When to run the parser

- Before locking a spec (for Sage only).
- During review or gate checks to confirm no open questions remain.
- After resolving a discussion thread, to confirm the status changed correctly.
- When you want to see every thread that is waiting for your answer.

## How to write

### 1. Quote dialogue

Use nested blockquotes to show who is speaking and the reply depth.

#### Plain speaker line

```markdown
> **Sage:** What should happen when depth is zero?
>> **Aaron:** Treat it as invalid input.
```

#### Mention someone explicitly

```markdown
> **Sage:** @Lex, Does this AC have test coverage?
>> **Lex:** Yes, covered by TC-0010.
```

### 2. Admonition

Use GFM admonition syntax for public notes that are not part of a dialogue chain.

```markdown
> [!NOTE]
> This section will be completed in the next round.
```

```markdown
> [!WARNING]
> This API is still experimental.
```

### 3. Comment

Use HTML comments for internal agent drafts or TODOs that should not render.

```markdown
<!-- TODO: double check edge case -->
```

## Rules

1. Each `>` in a quote or admonition must be followed by a space.
2. Speaker names are wrapped in `**` and followed by `:`.
3. Speaker names are case-insensitive for matching but keep original casing for display.
4. Nesting indicates reply depth: `>>` is a reply, `>>>` is a reply-to-reply.
5. Keep dialogue to 1-3 levels. Split deeper threads into a new thread.
6. Admonitions use `[!NOTE]`, `[!WARNING]`, `[!TIP]`, `[!IMPORTANT]`, or `[!CAUTION]`.
7. Comments use HTML `<!-- ... -->` syntax and do not render in the final document.
8. Never reply in plain chat — always write quote dialogue in the relevant document.

## Mistakes to avoid

- Forgetting the space after `>`
- Using `[note]` instead of `[!NOTE]`
- Using `@` in a way that obscures who is being mentioned
- Sending plain-text replies in chat instead of writing quotes
- Mixing admonitions or comments into a dialogue chain
