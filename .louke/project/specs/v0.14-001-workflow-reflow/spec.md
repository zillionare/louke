---
status: Draft
spec_id: v0.14-001-workflow-reflow
created: 2026-07-17
story_digest_bound: sha256:8a86969c36d60b26efbc1b1c02cb48eddf765af7064a94c9b5dc8d513191bd0f
---

# v0.14 Workflow Reflow — Spec

- **Spec ID**: v0.14-001-workflow-reflow
- **Created**: 2026-07-17
- **Status**: Draft (M-SPEC initial drafting — anchor injection deferred to Runtime M-SPEC step 4)
- **Bound Story digest**: sha256:8a86969c36d60b26efbc1b1c02cb48eddf765af7064a94c9b5dc8d513191bd0f

> **Authority boundary.** This document defines only the requirements (FR/NFR descriptions + metadata). The canonical product narrative (user stories, happy path, usage scenarios, risks/assumptions) and the original product language remain in `story.md`; they are not repeated here. Each FR/NFR records the originating behavior seeds (BS-IDs) and cutover-checklist / research-report section IDs in its `Source` field.
>
> **Spec size hard gate.** At most 30 active FR+NFR units (`Valid=❌` excluded) — exactly 30 is allowed; >30 cannot be waived and triggers `SPEC_SCOPE_TOO_LARGE` → `needs_story_split` per BS-23/BS-29 and cutover-checklist §E. Hard-gate scope is **one Spec**; it does not accumulate across multiple Specs in the same release.
>
> **Active count for this draft.** 22 FR + 7 NFR = 29 active units (≤30 hard gate satisfied). All 31 BS seeds (BS-01 … BS-31) and every Happy Path step are mapped to at least one FR/NFR below; no requirement duplicates Story / User Stories / Usage Scenarios content.
>
> **Acceptance.** Every test-assertable pass condition lives in `acceptance.md`. Each AC must be observable from outside the system; "works well" / "is correct" / "feels right" are not ACs.
>
> **Lock semantics awareness.** The two-tier Human gate binding rules live in this Spec (FR-0400, FR-0410). The six-document M-LOCK contract bundle (story + spec + acceptance + test-plan + architecture + interfaces) is named here but authored downstream — those documents are owned by their respective producers. Requirements-approval and M-LOCK are distinct gates; this Spec does not collapse them.
>
> **Decided status.** All requirements in this draft carry `Decided=⚠️` because they have not yet been confirmed via anchored inline discussion with the user/Human. Sage is using draft-first per BS-26 / FR-0610; subsequent rounds will resolve specific units via inline discussion, not via the exception `question` channel.

## Functional Requirements

> **Format convention.** Each FR unit: level-3 heading `### FR-XXXX {title}` (4 digits, uppercase), 3-column metadata table, `Source` line, requirement body, `---` separator.
>
> **Numbering.** Initial draft uses 100-step spacing starting at FR-0100 (FR-0100, FR-0200, FR-0300, …) to leave 9 insertion slots per tier for subsequent review rounds.
>
> **Coverage note.** Every FR has at least one `Source`; no requirement is severable from its source seeds; cutover-checklist §A–§G and research-report §5/§7/§9/§10 are referenced as supporting evidence rather than re-quoted.

### FR-0100 Production Composition Root, Auto-Driver, and Complete Workflow Entry

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-01, BS-15, BS-17; Happy Path steps 1–2, 10; cutover-checklist §B, §C; research-report §5.1

- A single production composition root (shared persistent Store, versioned Catalog, registered Handlers/Capabilities, Orchestrator, Gate service, OpenCode adapter, program executor) MUST be installed before any workflow is reachable. The composition root MUST NOT be replaced or supplemented by test-fixture injection.
- Web Chat (the Chat tab inside the Web Workbench served by `lk serve`) is the only user-facing development entry for `new_feature` and `bug_fix` at v0.14 release cutover onward. CLI commands that previously advanced workflow (`lk agent ...` etc.) are removed from the public CLI surface — see FR-0910 / NFR-0600; pre-cutover development retains CLI workflow-advance behaviour per BS-28.
- A `new_feature` or `bug_fix` WorkflowRun MUST be created and bound to its `WorkflowDefinition` version (FR-0200) before any step is dispatched.
- When a step becomes current: a `program` step MUST auto-execute its registered handler and accept only that handler's authoritative result (FR-0110); a `semantic` step MUST auto-create a controlled Agent task under the current run; a `human` step MUST persist `waiting_for_human` (FR-0300, FR-0400) and stop without advancing.
- The `new_feature` run order is non-reorderable: Story → requirements-three-piece review → requirements approval gate → design-three-piece review → M-LOCK gate → Issue splitting → implementation → authoritative tests → release confirmation → history archive. The two Human gates (requirements approval, then M-LOCK) gate all work in between.
- Web, CLI, Chat and Agents MUST NOT submit program results, pass declarations, target stages, or forged authoritative evidence to advance the run; only the corresponding handler/adapter's real result is accepted (FR-0110, BS-02).
- For runs created under this composition root, Runtime MUST NOT create tasks, sessions, or dispatches targeting Scout, Warden, or Keeper; those names MUST NOT appear in the registered Agent catalog, the Chat Agent picker, or model bindings (BS-13). Their semantic residual responsibilities MUST be reassigned before retirement (Scout → Scribe; Warden story-semantic residue → Scribe/Sage/Lex; Keeper semantic review residue → Prism) and foundation-deterministic duties map to explicit program handlers. Repository, docs (Maestro prompt, README, `docs/workflow.md`, Agent list), and observed model bindings MUST be updated before this composition root becomes reachable. A v0.13-baseline run that still references a retired Agent MUST be reached only via the pre-cutover CLI workflow-advance surface and MUST NOT mutate v0.14 run state.

---

### FR-0110 Authoritative Program Result Boundary

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-02; cutover-checklist §B; research-report §5.1, §13 risk R-01

- A program step's success / failure, gate decision, or authoritative evidence MUST be accepted only as the result returned by the registered handler invoked on the current `StepContext`. No client (Web, CLI, Chat, Agent) MAY mark a program result, declare `pass`, set `next_step`, or forge authoritative evidence through any input channel.
- The current API surface that accepts a `result` string MUST be closed; existing adapters MUST be migrated to call the same program handler the workflow invokes (no second writer of authority).
- A forged or client-supplied program result MUST be rejected with a deterministic error and MUST leave run / project / Git state identical to pre-call state; the run MUST NOT advance, MUST NOT trigger Issue/worktree creation, MUST NOT push commits, and MUST NOT emit approval/lock signals.
- An E2E (FR-0920) MUST verify that the closed boundary holds across all four caller surfaces.

---

### FR-0200 Workflow Definition Versioning and Run Pinning

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-14; research-report §9; v0.12 FR-0001 inheritance

- Every `WorkflowDefinition` MUST carry a stable `definition_id`, an immutable `version`, a starting step, a finite step set, declared transition conditions, and an explicit `contract_digest`.
- The Catalog MUST refuse any attempt to re-register an existing `(definition_id, version)` with different content (same identifier, differing digest → reject before any caller can observe the candidate).
- A `WorkflowRun` created under `(definition_id, version)` MUST remain bound to that exact version and `contract_digest` for its entire lifetime; subsequent Catalog edits (new version registered, old version deprecated) MUST NOT alter in-flight runs.
- New runs default to the current approved definition; historical runs MUST remain replayable and inspectable from their pinned version (NFR-0200).

---

### FR-0300 Runtime-driven Persistence and Restart Recovery

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-03; Happy Path step 11; cutover-checklist §B; research-report §5.1

- Runtime MUST persist WorkflowRun identity, definition identity/version, current step, status, revision, input digest, event log, gate state, task/attempt state, artifact/evidence identities, and the last known error under a shared, schema-versioned, atomic store. Persistence MUST NOT depend on Agent session memory.
- For every accepted state change, the persisted state and its corresponding event MUST commit in the same transaction; partial writes are forbidden.
- After a clean shutdown, crash, or `lk serve` restart, Runtime MUST enumerate all in-flight and recent runs and their current step without re-running any program step. Recovery MUST NOT depend on OpenCode session re-attach or legacy `current_stage` inference.
- Steps whose authoritative result is unknown or ambiguous on restart MUST stay in a diagnostically recoverable state (no implicit PASS, no implicit advance). A deterministic re-execute path MUST exist for the same handler with the same idempotency key.

---

### FR-0400 Requirements Approval Gate (Three-document Binding)

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ⚠️ | ⚠️ |

- **Source**: BS-18; cutover-checklist §B; v0.12 FR-0801 inheritance

- When `story.md`, `spec.md`, and `acceptance.md` complete user review and Lex structural verification, Runtime MUST create a dedicated `requirements_approval` gate that binds the joint digest of the three documents.
- The gate MUST NOT be approved by any Agent or via a free-text claim; only a Human decision matched against the bound digest is accepted (FR-0110, FR-0500).
- Until the requirements approval gate is approved, Runtime MUST refuse to launch, accept, or persist any `test-plan`, `architecture`, or `interfaces` task or product; this refusal covers Agents attempting to write those documents out of band.
- If any of the three bound documents digest changes after approval, the previous approval MUST be invalidated and a fresh gate MUST be created; the original digest MUST remain auditable.
- On `reject`, the run MUST return to M-SPEC requirement review with the Human's reason and the artifact digest preserved.

---

### FR-0410 M-LOCK Gate (Six-document Contract Bundle)

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ⚠️ | ⚠️ |

- **Source**: BS-19; cutover-checklist §B; v0.12 FR-0901 inheritance

- M-LOCK MAY be created only when both preconditions hold: (a) requirements approval (FR-0400) is effective AND (b) `test-plan.md`, `architecture.md`, and `interfaces.md` have completed program validation, independent reviewer review, and user review.
- M-LOCK MUST bind a single `contract_digest` computed from the six documents: `story.md + spec.md + acceptance.md + test-plan.md + architecture.md + interfaces.md`. The M-LOCK gate is contract-bundle-locked, not design-triple-locked.
- Until M-LOCK is Human-approved against this bound bundle, Runtime MUST NOT create implementation worktrees, dispatch implementation tasks, accept implementation commits, create or split GitHub Issues, or push any branch (FR-0420).
- Any change to any of the six bound documents after M-LOCK approval MUST invalidate that approval and require re-approval. The upstream rule (which bound document edit forces which upstream re-stage) is fixed by the workflow definition.

---

### FR-0420 Issue Splitting and Implementation Worktree Gating

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-20; cutover-checklist §B

- GitHub Issue splitting, creation of implementation worktrees, the first implementation commit, and any `git push` of implementation branches MUST occur strictly after M-LOCK approval (FR-0410).
- The split MUST be performed by the Runtime program handler. Agents MUST NOT create the Issues, the worktree, the commit, or the push directly. The closed program-result boundary (FR-0110) covers the result side; this FR covers the Issue/commit/push initiation side.
- The E2E (FR-0920) MUST assert that, before M-LOCK, no implementation worktree exists and no Issue is created; after M-LOCK, both are present and traceable to Issue / commit / spec / AC identities (NFR-0300).
- Re-issuing the same Issue-split attempt under the same split digest MUST be idempotent (no double creation, no duplicate push).

---

### FR-0430 bug_fix Inheritance of Source Requirements Approval

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-21; v0.12 FR-0801 / FR-2101 inheritance

- For a `bug_fix` run, Runtime MUST verify by program check that the linked GitHub Issue maps to an already-approved Spec / AC (or a logically equivalent slot in the accepted contract bundle), AND that the proposed change does NOT alter the approved product behaviour.
- If both checks pass, the existing requirements approval is inherited; Runtime MUST NOT create a new requirements gate. M-LOCK (FR-0410) remains mandatory for every `bug_fix` run.
- If either check fails (Issue lacks traceability or behaviour changes), the `bug_fix` MUST exit the hotfix path; Runtime MUST require a fresh requirements flow (a new requirements gate).
- A failed inheritance check MUST leave the original run state untouched and emit a deterministic `hotfix_inheritance_rejected` event.

---

### FR-0500 Runtime-owned M-SPEC Main Loop

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-22; cutover-checklist §E, §G; research-report §15.13

- Runtime owns the M-SPEC main loop end-to-end: artifact revision / digest / diff computation; structure validation of `spec.md` and `acceptance.md`; inline-discussion scan and waiter; anchor injection; Git / GitHub-Issue reconciliation; requirements-approval gate (FR-0400); M-LOCK gate (FR-0410); restart recovery for the spec loop.
- In one M-SPEC round, Sage and Lex MUST each complete only one semantic task (drafting, reviewing, or structural verification). They MUST NOT call workflow / gate / dispatch tools; the round's persisted outputs are read by Runtime, and subsequent actions are Runtime's responsibility.
- The loop MUST be resumable. If `lk serve` is restarted mid-M-SPEC, Runtime MUST recover to the current spec revision, the current inline-discussion set, the current approval gate state, and any unscheduled Sage/Lex task, without retrying already-completed rounds.

---

### FR-0510 Spec Scope Hard Gate (≤30 Active FR+NFR per Spec)

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-23; cutover-checklist §E; research-report §15.14

- After Sage completes the initial draft or any revised draft of `spec.md` and Runtime persists it, Runtime MUST compute the active FR+NFR count (`Valid=✅` units; `Valid=❌` requirements do not count) before dispatching Lex.
- The hard gate is exactly 30: ≤30 active units pass; >30 MUST immediately return the deterministic error `SPEC_SCOPE_TOO_LARGE` and mark the run `needs_story_split` (FR-0520). The gate is per-Spec and does not accumulate across Specs in the same release (NFR-0100).
- When the run is marked `needs_story_split`, Runtime MUST perform no downstream side-effects: no anchor injection, no GitHub Issue creation, no requirements-approval action, no M-LOCK action, no push. Lex is not asked to decide whether to split.
- The E2E (FR-0920 §E) MUST assert both directions: 30 active units pass into Lex review; 31 active units return `SPEC_SCOPE_TOO_LARGE` without side-effects and leave the run in a recoverable `needs_story_split` state.

---

### FR-0520 Over-limit Return and `needs_story_split` Governance

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-24, BS-29; cutover-checklist §E

- On `needs_story_split`, Runtime MUST legally return control to M-STORY with the original Story + Spec + Acceptance revision preserved intact (no silent truncation, no automatic rewrite).
- Runtime MUST NOT itself decide the split boundary. Scribe proposes independent value slices; the Human decides. Both steps MUST be recorded as audit events referencing the original Story digest.
- Once the Human approves a split, the original Story is marked `Split parent`; every child Story records `parent_story_id` and enters its own independent release/run. The child Spec continues to be governed by FR-0510 (≤30 active units, gate per-Spec).
- The E2E (BS-29 / FR-0920) MUST cover: 31 active units rejected at the Lex-precursor step with zero downstream side-effects; `needs_story_split` state recoverable across restart; original Spec revision preserved; parent–child digest chain traceable; and a child Spec of ≤30 units completing independently.

---

### FR-0600 Scribe Story Authority vs. Sage Spec Boundary

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-25; cutover-checklist §B, §C; research-report §15.13

- Scribe owns the canonical `story.md`, including the User Stories narrative. The bound Story digest is the source of truth for the original product intent.
- Sage (M-SPEC) MUST NOT redo Story discovery and MUST NOT rewrite User Stories, Usage Scenarios, Happy Path, or Risks in `spec.md`. Sage translates the Story into traceable FR/NFR with `Source` references to BS-IDs and Story section IDs; the User Stories narrative remains canonical in `story.md`.
- Both the Story digest and the Spec revision MUST be reproducibly traceable to the same Story source revision. Cross-references between the two documents MUST NOT silently disagree (NFR-0300: identity independence).

---

### FR-0610 Sage draft-first and Anchored Inline-Discussion Interaction

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-26; cutover-checklist §G; research-report §15.12

- Sage MUST default to draft-first. When a `spec.md` or `acceptance.md` requirement needs clarification, Sage MUST write a concrete draft of the FR/NFR/AC and attach an anchored inline-discussion thread under the relevant line; the document is shipped for IDE review with all open threads visible.
- The interactive `question` channel is the exception, not the default (see FR-0620 for its exception semantics). It MUST be opened only when (a) no meaningful document anchor exists, or (b) a product decision must be taken immediately and cannot be deferred to inline-discussion.
- An anchored inline-discussion thread IS the canonical mechanism for traceability of an M-SPEC clarification. The `lk discuss` query output (5-tuple positioning: `anchor_line` / `anchor_text` / `root_line` / `root_text` / `thread_id`) is the authoritative locator across revisions.

---

### FR-0620 Sage `question` Exception Channel + `waiting_human` Persistence

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-31; cutover-checklist §G; research-report §15.12

- When Sage opens the exception `question` channel, the question and its anchor MUST be persisted as a first-class wait state (`waiting_human`) by Runtime, independent of any Agent session memory. The blocked requirement MUST keep `Decided=⚠️` and MUST NOT be auto-defaulted to any value.
- While `waiting_human` is active for a given requirement, Runtime MUST NOT consume a review round, MUST NOT auto-progress, and MUST NOT release either the requirements-approval gate or M-LOCK gate for the affected run. The round counter for M-SPEC MUST remain at its pre-question value.
- Visibility durability is dual. Runtime persists the wait state; the opencode session restore mechanism keeps the Sage prompt visible after `lk serve` restart when the user re-enters the chat window. Either alone is insufficient. Runtime's `waiting_human` and gate-block semantics do NOT depend on session restore.
- The task resumes only when a matching Human reply lands in the same spec revision. Non-matching replies (cross-revision, wrong anchor) MUST NOT be auto-accepted (NFR-0700).

---

### FR-0700 M-TESTPLAN Author / Reviewer Division of Labor

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-27; cutover-checklist §D; research-report §15.16

- `test-plan.md` MUST be authored by Archer and reviewed by the S-tier Prism as the sole technical reviewer. Shield MAY provide downstream executability feedback but MUST NOT approve. Sage MUST NOT approve M-TESTPLAN; Sage's role is S-tier M-SPEC requirement analysis only.
- The reviewer assignment is enforced at the program-handler level: the M-TESTPLAN approval signature MUST be bound to Prism's identity, not Sage's. An approval signed by Sage or by a non-tier-S role MUST be rejected without demoting the run.
- Re-issuing the same M-TESTPLAN review MUST be idempotent under the same review digest and MUST NOT cause double approval or double rejection.

---

### FR-0720 return-upstream with Fixed Targets and Downstream Stale

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-04, BS-05; cutover-checklist §D; research-report §7.1

- return-upstream is permitted only when the run is active and not yet released. The set of legal return targets is declared statically by the WorkflowDefinition and MUST be fixed; user-typed arbitrary stage names MUST be rejected.
- Runtime MUST surface, in the UI or program surface, only the fixed legal targets, and the run MUST pause in `waiting_for_human` until the user confirms one.
- On return-upstream execution, the chosen target step and every step after it MUST be marked stale / superseded in the run ledger. Their associated artifacts, approvals, evidence and event records are retained (no file, document or Git-history deletion); identity must remain auditable (NFR-0300).
- The run MUST re-enter the workflow at the chosen target step and MUST re-pass through the subsequent review, requirements approval (FR-0400), M-LOCK (FR-0410), and Issue split (FR-0420) gates before any further implementation work.

---

### FR-0730 Irreversible-Side-effect Refusal on return-upstream

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-06; cutover-checklist §D; research-report §7.1

- If return-upstream would need to reverse an irreversible external side-effect (a public release, a published tag, a delivered external artifact, or any other side-effect whose reversal is not under Runtime's control), Runtime MUST refuse the automatic return and MUST move the run into `needs_attention`.
- The refusal MUST be auditable: actor (or system), reason, attempted target, the irreversible side-effect list (with publication / tag / artifact identity), and the timestamp MUST be recorded as a single event.
- `needs_attention` MUST be Human-resolvable only. The run MUST NOT auto-progress, MUST NOT re-enter requirements approval, and MUST NOT skip M-LOCK; the Human may choose to (a) abandon the return and continue, or (b) start a new run via `bug_fix` / `new_feature` per WorkflowDefinition rules.

---

### FR-0740 Bounded Waiver Recording with Non-Waivable Invariants

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-07, BS-08; cutover-checklist §E; research-report §7.2

- A waiver is a risk-acceptance record, not an override. For every waivable check failure, Runtime MUST persist a waiver record that binds at least: actor / principal, reason, target check identifier, target evidence digest, scope (what is and is not waived), revision / digest bound at the time of decision, creation timestamp, recheck condition, and the original failure reference (BS-07).
- The waiver record MUST coexist with the original failure: the original `FAIL` evidence is NOT rewritten to PASS, and any review surface continues to show both the failure and the waiver. The run MAY continue past that specific gate only if the waiver is bound and the check is on the waivable list.
- The following MUST NEVER be waivable: requirements approval (FR-0400), M-LOCK (FR-0410), identity / secret / auth handling, revision CAS and atomicity, artifact freshness, Agent self-approval or self-declared program result (FR-0110), and release identity mismatch. A waiver request against any of these MUST be rejected deterministically and the run MUST NOT advance.
- Waivers MUST be re-evaluated when the bound evidence / revision changes. A stale waiver MAY NOT continue to suppress a FAIL.

---

### FR-0750 No-new-debt Adoption Preview / Apply / Touch-to-Clean / Fail-Safe

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-09, BS-10, BS-11; cutover-checklist §E; research-report §6

- Adoption preview: on user request, Runtime MUST pin the project's Git revision and workspace digest, run the full set of applicable program checks (lint / typecheck / test / security / docs / trace / anti-pattern), and report three buckets: (a) items blocking adoption, (b) historical items eligible for `baseline-known`, (c) auto-fixable items.
- Baseline `known` is not PASS. Frozen historical findings remain visible and are recorded in a debt ledger keyed by check_id / rule_id / finding_identity / source_revision / evidence_digest / scope / severity / status / owner / reason / review_condition / expires_at (research-report §6.3).
- Touch-to-Clean: when a baseline file is first modified after adoption, the entire file MUST be re-checked under the current applicable program checks before the run can continue. If all checks pass, the file permanently exits `baseline-known` and is marked `managed`; reverting to the adoption content does NOT restore baseline.
- Fail-safe: if adoption preview or apply fails for any reason (network error, user cancel, program-handler exception, evidence inconsistency), Runtime MUST NOT alter the user files, MUST NOT rewrite Git history, and MUST NOT publish new evidence. The previous state MUST remain reachable; a deterministic retry is permitted but MUST NOT silently succeed after a prior failure.
- Critical invariants (correctness, security, identity, release identity) MUST NEVER be baselined; a baseline request against these MUST be rejected at preview time.

---

### FR-0800 Built-in Versioned Lifecycle Hook Scheduling

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-12; cutover-checklist §D; research-report §8

- v0.14 supports only Louke-internal, versioned lifecycle hooks pinned to a `hook_id + hook_version`. Project-supplied arbitrary shell hooks, external hook marketplaces, and user-defined scripts are out-of-scope.
- Every registered hook declaration MUST contain at least: `hook_id`, `hook_version`, lifecycle point, input / output schema, `blocking` flag, timeout, retry policy, idempotency policy, permissions, and redaction policy. Runtime MUST refuse an undeclared hook.
- Hooks are scheduled by Runtime; they MUST NOT be invoked by Agent prompt self-call. A hook MAY be tagged `behavioral` (state-affecting, bound to a WorkflowDefinition version) or `observational` (log / telemetry only, may be enabled globally and MUST NOT change run state on failure).
- On lifecycle points `after_semantic_result`, `after_human_decision`, session save, and around `return-upstream`, Runtime MUST dispatch the declared hooks under a stable correlation_id bound to `run_id` / `step_id` / `attempt_id` / `revision`. Hook failures are recorded and correlated but MUST NOT change the originating run state in an undeclared way (NFR-0500).

---

### FR-0910 Cutover Entry Convergence and Old-workflow CLI Command Absence

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-28, BS-30; cutover-checklist §C, §F; research-report §15.11, §15.17

- v0.14 development occurs on top of v0.13; during that pre-cutover window CLI and Web Chat are both reachable, and CLI retains v0.13-style workflow-advance behaviour (including `lk agent ...`) so dogfood, debugging and regression remain possible. At v0.14 release cutover, Runtime MUST converge the entry surface in one atomic operation: Web Chat becomes the only user-facing development entry; old workflow CLI commands are removed from the public surface; pre-cutover CLI whitelists (`lk serve`, `lk upgrade`) remain.
- After cutover, removed commands (e.g. `lk agent ...`) MUST NOT appear in the CLI registry, `--help`, shell completion, or any published command list. CLI dispatcher MUST NOT route them to Runtime / any Agent / any workflow. A user invocation MUST hit the CLI's plain `unknown` / `unsupported-command` path — identical to any other unknown command. No special error code for "deprecated command" MAY be emitted; no `cli_legacy_deprecated_noop` audit event MAY be written; no deprecated-no-op exit code contract exists; no migration warning text exists; no specialised stdout / stderr shape is required; no fallback to legacy Runtime / Agent / workflow is permitted.
- Half-cutover intermediates are forbidden. After the cutover transaction commits, no CLI command surface, no `--help` page, no completion entry, and no dispatcher route may offer the pre-cutover workflow-advance behaviour. The cutover is recorded as an atomic event with pre- and post-state digests.
- Runtime stores (run / project / Git / audit) MUST be byte-identical before and after any call to a removed command. No external side-effect MAY occur.
- The E2E (FR-0920) MUST assert: (a) post-cutover CLI does not register any old workflow command; (b) a sample old command invocation follows the plain unknown / unsupported-command path with no special exit code, no special audit event, and no state change; (c) the pre-cutover v0.13 baseline (in v0.14 dev window) still executes the legacy workflow-advance CLI commands.

---

### FR-0920 Installed-wheel E2E and Louke Dogfood Acceptance

(placed at the end of FRs and before NFRs, summarising the cross-cutting acceptance harness that every other FR references.)

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-16, BS-29; Happy Path step 11; cutover-checklist §D, §E; research-report §3 §10 §15.5

- Installed-wheel E2E: from a clean checkout the v0.14 wheel is built, installed, and exercised in an isolated workspace via only public `lk serve`, Web / CLI, the persisted store, and declared external adapters; no test fixture MAY inject the shared store.
- The run MUST complete a full `new_feature` journey: setup, Story, Go human decision, requirements approval, design three-piece review, M-LOCK, implementation, authoritative tests, release confirmation, history archive. A `bug_fix` journey MUST be coverable by the same E2E harness.
- The E2E MUST assert: Scout / Warden / Keeper task / session / dispatch counts are zero (BS-16); the closed program-result boundary (FR-0110) holds for every caller; restart recovery (FR-0300) works across `lk serve` restart; old workspace adoption (FR-0750) does not produce a dual-authority state; the 31-unit over-limit case (FR-0510 / FR-0520) returns `SPEC_SCOPE_TOO_LARGE` with no side-effects and is recoverable; the cutover CLI absence + unknown-command path (FR-0910) and the exception-question `waiting_human` path (FR-0620) both behave as specified.
- Louke dogfood: the v0.14 Spec and implementation MUST run themselves through the new `new_feature` workflow end-to-end; public evidence of the journey MUST be retained from Story to history; the dogfood run MUST NOT dispatch Scout / Warden / Keeper.

---

## Non-Functional Requirements

> **Format and numbering rules** match FR above; the table meaning is identical. `Source` references remain the originating behavior seed IDs.

### NFR-0100 Per-Spec Scope Independence from Release Cumulative Limit

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-23, BS-29; cutover-checklist §E; research-report §15.14, §15.15

- The 30 active FR+NFR hard gate (FR-0510) operates on a single Spec, NOT on the cumulative count across multiple Specs in the same release.
- The hard gate is non-waivable. No actor / reason / scope combination MAY turn a >30-active-unit Spec into a passing one. A waiver attempt MUST be rejected with `SPEC_SCOPE_TOO_LARGE` regardless of scope.
- Recommend 1 Story / 1 Spec / 1 release as the default shape; this is a recommendation, not an enforcement. Two Specs in the same release are allowed as long as each obeys its own per-Spec gate.

---

### NFR-0200 Workflow Definition Immutability and Tampering Resistance

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-14; research-report §9; v0.12 FR-0001 inheritance

- Once a `(definition_id, version)` is registered with a specific `contract_digest`, any attempt to substitute the registered content (Catalog write, file edit, memory store write, prompt injection, or replay) MUST fail at the Catalog boundary before any run observes the candidate.
- The Catalog MUST distinguish "re-registration with new content" (reject) from "new version with new content" (accept as `(definition_id, version+1)`). A successful new-version registration MUST NOT alter any in-flight run's pinned version.
- The E2E (FR-0920) MUST include a tampering probe that tries (i) same-id/same-version/different-digest re-registration, (ii) attempted edit of an in-flight run's bound definition, and (iii) attempt to soft-mutate the Catalog from a non-owner context; all three MUST be rejected deterministically with a documented error.

---

### NFR-0300 Spec / Acceptance / Issue / Commit Identity Independence from Workflow Changes

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: Happy Path step 11; cutover-checklist §D; research-report §10

- When the WorkflowDefinition version changes, Runtime MUST NOT rewrite any Spec / AC / GitHub Issue / commit identity / artifact digest / evidence digest that is referenced by existing runs. New runs MAY reference old assets; old runs MUST continue to reference their original assets through their pinned version.
- The Trace/Evidence graph (SPEC-ID, FR/NFR, AC, Issue, commit hash, artifact digest) is the stable address space; WorkflowRun records only the path by which an asset was produced, reviewed and approved, not the asset's identity.
- An approval / evidence / gate record MUST be marked stale only when the digest of the asset it binds changes — never simply because the workflow definition version changed.

---

### NFR-0400 Adoption Ledger Integrity and No-Double-Authority

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-09, BS-11; cutover-checklist §E; research-report §6.3

- A baseline finding record MUST be uniquely keyed by `check_id + rule_id + finding_identity + source_revision + evidence_digest + artifact_digest`; record collisions MUST be rejected on insert. Renames of equal content carry baseline and a `renamed_from` record; renames with content changes, copies, and deletes exit baseline and become managed or removed.
- After adoption apply, Runtime MUST NOT allow a second authority (legacy `current_stage`, ad-hoc file write, manual commit) to mutate the run / project / baseline ledger. Any such attempt MUST be rejected deterministically and recorded.
- Re-running preview MUST be deterministic for the same pinned revision: the same bucketing, the same evidence digests, and the same ledger identities (no drift across replays).

---

### NFR-0500 Hook Isolation from Transition / Gate / Program-result Authority

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-12; cutover-checklist §D; research-report §8.3

- A lifecycle hook (FR-0800) MUST NOT approve a gate, submit a program result, choose a next step, run an undeclared shell command, or bypass freshness / identity / CAS requirements. Any such behaviour MUST be rejected deterministically and logged under the hook's correlation_id.
- Behavioural hooks MUST be pinned to a WorkflowDefinition version. Observational hooks MAY be enabled globally but MUST NOT affect run state on failure; their timeout / retry policy MUST be applied locally and isolated from the originating step's idempotency window.
- Hook declarations MUST be auditable (declaration diff, lifecycle point, blocking / non-blocking, retry policy) across the run ledger; unauthorised modification of a registered hook declaration MUST be detected and recorded.

---

### NFR-0600 Web Chat Cutover Idempotency and Surface Integrity

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-28, BS-30; cutover-checklist §C, §F; research-report §15.11, §15.17

- The cutover operation (FR-0910) MUST be idempotent under the same trigger digest. Re-issuing the cutover for an already-cutover release MUST be a no-op with the same pre/post digests and MUST NOT introduce half-cutover intermediate states.
- After cutover, the Web Chat entry MUST be the only development entry for `new_feature` / `bug_fix`, and the CLI surface MUST contain only the whitelisted operations (`lk serve`, `lk upgrade` and any other explicitly whitelisted ops), with no deprecated no-op layer — including no `cli_legacy_deprecated_noop` audit event type, no deprecated-no-op exit code contract, no migration warning text.
- Surface integrity checks MUST be program-level (registry, help, completion, dispatcher routes, audit-store query results) and not derivable solely from documentation. The E2E (FR-0920) MUST run those checks before and after cutover and assert byte-level surface equality with the expected post-cutover shape.

---

### NFR-0700 Exception-question Channel: Non-default-decision / Non-round-consumption Guarantee

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ⚠️ |

- **Source**: BS-31; cutover-checklist §G; research-report §15.12

- While `waiting_human` is active for a requirement (FR-0620), Runtime MUST NOT substitute a default answer, MUST NOT consume a review round, MUST NOT auto-approve requirements (FR-0400) or M-LOCK (FR-0410), and MUST NOT roll the run forward into design or implementation.
- A Human reply that arrives in the wrong spec revision, on the wrong anchor, or under a different correlation MUST be classified non-matching and MUST NOT be auto-accepted. The review round counter MUST NOT increment on such non-matching replies.
- The opencode session restore mechanism (visibility of Sage prompts after restart) is an observability carrier only; Runtime's `waiting_human` persistence and gate-block semantics MUST NOT depend on session restore and MUST continue to hold even when the session is cold-started from a fresh device.

---

## Clarification Log

> Record questions raised during user review, Sage / Lex replies, reasons for deprecated requirements, and any decisions that affect FR / NFR table status. This section is reserved for anchored inline-discussion threads; Sage has not yet opened any thread in this initial draft (draft-first per BS-26 / FR-0610). Subsequent rounds will add threads anchored to specific FR/NFR lines.
