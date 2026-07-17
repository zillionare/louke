---
status: Draft
spec_id: v0.14-001-workflow-reflow
created: 2026-07-17
story_digest_bound: sha256:8a86969c36d60b26efbc1b1c02cb48eddf765af7064a94c9b5dc8d513191bd0f
---

# v0.14 Workflow Reflow — Acceptance Criteria

- **Spec ID**: v0.14-001-workflow-reflow
- **Created**: 2026-07-17
- **Bound Story digest**: sha256:8a86969c36d60b26efbc1b1c02cb48eddf765af7064a94c9b5dc8d513191bd0f

> **Purpose.** Central registry of test-assertable acceptance criteria. `spec.md` defines FR/NFR requirements and metadata only; observable, assertable pass conditions live here. Full AC ID format is `AC-FRXXXX-YY` (4-digit FR + 2-digit AC sequence), compatible with the test-plan / issue schema.
>
> **Assertability rule.** Each AC must be a runnable, observable, deterministic condition. "Works well" / "is correct" / "feels right" / "behaves reasonably" are NOT ACs. Given/When/Then phrasing is recommended; bullets that name a tool, an exit code, a digest equality, or a registry query are encouraged over prose.
>
> **Closure.** Every FR/NFR in `spec.md` MUST have a section here (or be explicitly listed under `## No Acceptance`). Coverage at draft time: 22 FR + 7 NFR = 29 sections. AC numbering restarts at 1 inside each FR/NFR section.
>
> **Decided status.** Each requirement in `spec.md` carries `Decided=⚠️`; AC content mirrors that — no AC has been confirmed by the user yet (draft-first per BS-26 / FR-0610). Subsequent rounds will resolve specific requirements via anchored inline-discussion.

## FR-0100 Production Composition Root, Auto-Driver, and Complete Workflow Entry

### AC-1
- Given the v0.14 wheel is installed and `lk serve` is started
- When the user opens the Web Workbench and creates a `new_feature` project
- Then a single WorkflowRun is created bound to the current `WorkflowDefinition` version, and the visible CLI surface in `lk --help` and shell completion contains only the whitelisted operations (`lk serve`, `lk upgrade`, etc.) — not retired workflow-advance commands.

### AC-2
- Given a run is active in program step `S_p`
- When `S_p` becomes current
- Then the registered handler for `S_p` is auto-executed by the Composition Root; the visible program result recorded against the step is byte-equal to that handler's authoritative return value (FR-0110 cross-check); a forged / client-submitted alternative result is rejected with a deterministic error before any state change.

### AC-3
- Given an active run with one `program` step, one `semantic` step, and one `human` step in its plan
- When the composition root drives each step into the current position
- Then (a) the `program` step auto-runs its handler; (b) the `semantic` step creates exactly one controlled Agent task under the run; (c) the `human` step persists `waiting_for_human` (FR-0300) and stops without advancing.

### AC-4
- Given a `new_feature` run reaches the requirements-approval gate, then the design review, then M-LOCK, then implementation
- When the user inspects the run timeline
- Then the step order is non-reorderable; no step is skipped, no two human gates are merged, and the saved `workflow_definition.definition_id` + `version` is the same one bound at run creation (FR-0200).

### AC-5
- Given the production composition root is reachable
- When a CLI / Web / Chat / Agent submission attempts to advance the run via `pass`, `next_step`, `set_stage`, or forged evidence
- Then the submission is rejected, no run / project / Git / audit state changes, and no Issue / worktree / commit / push occurs.

### AC-6
- Given a fresh activation of the composition root under v0.14
- When the runtime enumerates the registered Agent catalog, Chat Agent picker, and model bindings
- Then no entry refers to Scout, Warden or Keeper; their responsibilities (Scout → Scribe; Warden story-semantic residue → Scribe/Sage/Lex; Keeper semantic review residue → Prism) are explicitly reassigned to a live Agent or a live program handler.

### AC-7
- Given the user starts a `new_feature` run under the composition root before repository / docs / model bindings have been updated to retire Scout/Warden/Keeper
- When the composition root is asked to bind the run
- Then the binding MUST refuse with a documented precondition error and MUST NOT create a new WorkflowRun.

### AC-8
- Given a v0.13-baseline run still references a retired Agent
- When the user invokes the pre-cutover CLI workflow-advance surface to reach it (this is allowed during pre-cutover dev, BS-28)
- Then the call completes against the pre-cutover surface, the v0.14 run state remains byte-equal, and the v0.14 ledger contains an audit event tagging the legacy surface as the authority for that call only.

---

## FR-0110 Authoritative Program Result Boundary

### AC-1
- Given a program step is running under FR-0100
- When the Web UI (or CLI / Chat / Agent) submits a JSON body or text claiming the step `pass` or providing a `result` string outside the registered handler's return channel
- Then the submission is rejected with a deterministic error (e.g. `program_result_forged`), run state is unchanged, and the only authoritative result stored against the step is the handler's real return.

### AC-2
- Given the legacy API surface that accepted client `result` strings
- When v0.14 takes effect
- Then that endpoint returns a closed-contract error (`program_result_endpoint_closed`) and does NOT accept any client-supplied result.

### AC-3
- Given four caller surfaces (Web / CLI / Chat / Agent)
- When each surface attempts to forge a program result on the same step
- Then every attempt is rejected, and the E2E (FR-0920) asserts the same byte-equal pre/post state from each surface.

---

## FR-0200 Workflow Definition Versioning and Run Pinning

### AC-1
- Given a WorkflowDefinition is registered with `(definition_id="new_feature", version=1, contract_digest=D1)`
- When the Catalog receives a second registration with the same `definition_id` and `version` but different content (digest D2 ≠ D1)
- Then the Catalog rejects the second registration with a deterministic error and no caller observes the candidate.

### AC-2
- Given a `new_feature` WorkflowRun was created at `(definition_id="new_feature", version=1, contract_digest=D1)`
- When the operator adds `(definition_id="new_feature", version=2, contract_digest=D2)` to the Catalog
- Then the in-flight run remains bound to `version=1, contract_digest=D1`; its steps interpret transitions exactly as in version 1; no event / state references version 2.

### AC-3
- Given a registered `WorkflowDefinition`
- When a caller inspects its declared content (steps, transitions, gates, hooks, contract_digest)
- Then it contains a stable `definition_id`, an immutable `version`, a starting step, a finite step set, declared transition conditions, and an explicit `contract_digest`. Any reply missing one of these fields is rejected at registration.

---

## FR-0300 Runtime-driven Persistence and Restart Recovery

### AC-1
- Given an active run whose current step is `S` with attempt `a`
- When the Runtime accepts a state change for `S`
- Then (a) the persisted run state and (b) the corresponding event commit in the same transaction; partial writes are observable as a hard failure, never as a silently-mixed state.

### AC-2
- Given `lk serve` is stopped mid-run (clean shutdown, crash, or `kill -9`) and then restarted
- When the runtime enumerates in-flight runs
- Then every in-flight run reappears with its pinned definition identity/version (FR-0200), current step (no advancement past the last persisted step), status, revision, last-known error, gate state, and event-log tail; no program step is re-executed as a side-effect of recovery.

### AC-3
- Given a step's authoritative result is unknown or ambiguous at restart (e.g. power loss after partial handler execution)
- When the runtime recovers the run
- Then the step remains in a diagnostically recoverable state (NOT implicitly PASS, NOT implicitly advanced), and a deterministic re-execute path with the same idempotency key is available to the same handler.

### AC-4
- Given recovery completed
- When the runtime's recovery harness is verified
- Then the harness did NOT depend on OpenCode session re-attach or legacy `current_stage` inference to re-establish run state.

---

## FR-0400 Requirements Approval Gate (Three-document Binding)

### AC-1
- Given `story.md`, `spec.md`, and `acceptance.md` have completed user + Lex review
- When the Runtime creates the requirements-approval gate
- Then the gate's bound digest is the joint `sha256(story.md | spec.md | acceptance.md)` (or equivalent deterministic digest) and the gate is distinct from any M-LOCK gate.

### AC-2
- Given the requirements-approval gate is open
- When any caller (Agent, Web, CLI, Chat) attempts to launch, write, or persist a `test-plan`, `architecture`, or `interfaces` artefact
- Then the write is rejected with a deterministic error and the artefact is not produced.

### AC-3
- Given the requirements-approval gate is approved
- When the user mutates any of the three bound documents (story, spec, acceptance) — e.g. adds a sentence, reorders an AC, edits a Source field
- Then the prior approval is invalidated, a fresh gate is created, and the original digest remains auditable in the gate ledger.

### AC-4
- Given the Human rejects the requirements-approval gate (with a stated reason)
- When the run is checked
- Then the run is returned to M-SPEC review; the reason and the artifact digest are persisted; no design / implementation step proceeds.

---

## FR-0410 M-LOCK Gate (Six-document Contract Bundle)

### AC-1
- Given requirements approval (FR-0400) is effective AND `test-plan.md`, `architecture.md`, `interfaces.md` have completed program validation + independent reviewer review + user review
- When the Runtime creates the M-LOCK gate
- Then the gate's bound digest is the joint digest of `story.md + spec.md + acceptance.md + test-plan.md + architecture.md + interfaces.md`, and the gate is the contract-bundle lock (NOT the design-triple lock).

### AC-2
- Given M-LOCK is open
- When any caller attempts implementation worktree creation, Issue creation, implementation task dispatch, the first implementation commit, or `git push` of implementation branches
- Then each attempt is rejected with a deterministic error and no side-effect occurs.

### AC-3
- Given M-LOCK is approved
- When any of the six bound documents changes digest (including a no-op edit that nevertheless re-serialises the file with different whitespace)
- Then the prior M-LOCK approval is invalidated; re-approval is required; the upstream rule for "which bound document edit forces which upstream re-stage" matches the WorkflowDefinition's static rule and is observable in the run ledger.

---

## FR-0420 Issue Splitting and Implementation Worktree Gating

### AC-1
- Given the current run has not yet received M-LOCK approval
- When the Runtime inspects the project
- Then no implementation worktree exists, no GitHub Issue for the run has been created, and no push to an implementation branch has occurred.

### AC-2
- Given M-LOCK (FR-0410) is approved
- When the Runtime program handler performs Issue splitting
- Then (a) the Issues are created in the GitHub repo declared by the run; (b) the implementation worktree is created; (c) the first implementation commit is recorded; (d) the visible trace (Issue ←→ commit ←→ Spec/AC identities) is retrievable and stable (NFR-0300).

### AC-3
- Given the same split digest is re-issued
- When the program handler runs again
- Then the call is a no-op against existing Issues / worktree / commit; no duplicate creation occurs.

---

## FR-0430 bug_fix Inheritance of Source Requirements Approval

### AC-1
- Given a `bug_fix` run is being created against GitHub Issue `#N` that maps to an already-approved Spec/AC
- When the Runtime performs the inheritance check
- Then the check confirms traceability (Issue → Spec/AC) AND that the proposed change does NOT alter the approved product behaviour; both checks pass before inheritance is allowed.

### AC-2
- Given both inheritance checks pass
- When the user proceeds
- Then no new requirements-approval gate is created; M-LOCK (FR-0410) is still mandatory for the `bug_fix` run.

### AC-3
- Given either inheritance check fails (Issue lacks traceability to an approved spec/AC, OR the change alters approved behaviour)
- When the user proceeds
- Then the `bug_fix` exits the hotfix path, the Runtime requires a fresh requirements flow, and the audit log contains a `hotfix_inheritance_rejected` event naming the failed check.

---

## FR-0500 Runtime-owned M-SPEC Main Loop

### AC-1
- Given Sage has completed an M-SPEC round (drafting the spec, replying to an inline-discussion thread, etc.)
- When the Runtime reads the persisted outputs
- Then Runtime owns all next steps: structure validation, further inline-discussion scans, anchor injection, Git/GitHub reconciliation, gate creation or progression; Sage does NOT call workflow / gate / dispatch tools in this round.

### AC-2
- Given `lk serve` is restarted mid-M-SPEC
- When the Runtime recovers
- Then it reaches the current spec revision (no rolled-back text), the current inline-discussion set (no lost threads), the current approval-gate state (no spurious approval), and any unscheduled Sage/Lex task (no skipped work and no retried work).

### AC-3
- Given the Runtime is performing structure validation on `spec.md` and `acceptance.md`
- When validation completes
- Then validation result, computed digests, and any validation errors are persisted before any downstream side-effect (anchor, Issue reconciliation, gate action) is attempted.

---

## FR-0510 Spec Scope Hard Gate (≤30 Active FR+NFR per Spec)

### AC-1
- Given Sage has finished the initial draft of `spec.md` and Runtime has persisted it
- When Runtime computes the active FR+NFR count
- Then only `Valid=✅` units count; `Valid=❌` requirements, headings without a unit, and the clarification log are excluded.

### AC-2
- Given the active count is exactly 30
- When Runtime proceeds past the gate
- Then dispatch into Lex review proceeds with no side-effects from the gate itself.

### AC-3
- Given the active count is 31 or more
- When Runtime proceeds past the gate
- Then Runtime immediately returns the deterministic error `SPEC_SCOPE_TOO_LARGE`, marks the run `needs_story_split` (FR-0520), and performs NO anchor injection, NO GitHub Issue creation, NO requirements-approval action, NO M-LOCK action, and NO push.

### AC-4
- Given the active count is 31 and the run is in `needs_story_split`
- When the user restarts `lk serve`
- Then the run state is recoverable to the same `needs_story_split` state; no spec content was truncated.

---

## FR-0520 Over-limit Return and `needs_story_split` Governance

### AC-1
- Given the run is in `needs_story_split`
- When the Runtime returns control to M-STORY
- Then the original Story + Spec + Acceptance revision is preserved intact; no silent rewrite, truncation, or replacement has occurred.

### AC-2
- Given the run is in `needs_story_split`
- When Runtime considers the split boundary
- Then Runtime itself does NOT decide the boundary; the boundary proposal arrives as a Scribe authoring event, the decision arrives as a Human audit event, and the original Story digest is referenced by both.

### AC-3
- Given the Human approves a split
- When the parent / child relationship is recorded
- Then (a) the original Story is marked `Split parent`; (b) each child Story records `parent_story_id`; (c) the child Spec is independently governed by FR-0510 (≤30 active units); (d) the parent–child digest chain is queryable.

### AC-4
- Given the E2E (FR-0920) covers BS-29
- When the harness exercises a Spec with 31 active units
- Then the harness observes: (i) rejection at the Lex-precursor step with `SPEC_SCOPE_TOO_LARGE`; (ii) zero downstream side-effects; (iii) restart-recoverable `needs_story_split` state; (iv) parent-child digest chain traceable; (v) a child Spec with ≤30 active units that completes an independent run.

---

## FR-0600 Scribe Story Authority vs. Sage Spec Boundary

### AC-1
- Given Scribe has produced a canonical `story.md` with a User Stories narrative
- When Sage drafts `spec.md`
- Then Sage does NOT rewrite User Stories, Usage Scenarios, Happy Path, or Risks in `spec.md`; the User Stories narrative remains canonical in `story.md`.

### AC-2
- Given both `story.md` and `spec.md` exist
- When a reader cross-references a Story section to a `spec.md` `Source` field
- Then the Story digest and the Spec revision both resolve to the same Story source revision; a silent disagreement is not reachable.

### AC-3
- Given a Sage edit proposes to change a User Stories narrative
- When Sage persists the spec revision
- Then the Runtime refuses to write the change and surfaces a deterministic error (`sage_user_story_rewrite_refused`) before any side-effect.

---

## FR-0610 Sage draft-first and Anchored Inline-Discussion Interaction

### AC-1
- Given Sage needs clarification on an FR/NFR/AC unit
- When Sage persists the document
- Then Sage has written a concrete draft of the unit AND attached an anchored inline-discussion thread under the relevant line; no clarification round goes out as an open `question` by default.

### AC-2
- Given an anchored inline-discussion thread exists
- When `lk discuss query --file <spec.md>` runs
- Then the thread is returned with the 5-tuple positioning (`anchor_line` / `anchor_text` / `root_line` / `root_text` / `thread_id`) intact across revisions.

### AC-3
- Given a clarification round is needed
- When Sage decides whether to use `question`
- Then `question` is used only when (a) no meaningful anchor line exists in either `spec.md` or `acceptance.md`, or (b) a product decision must be taken immediately and cannot be deferred; otherwise inline-discussion is the chosen channel (FR-0620 covers the persistence semantics).

---

## FR-0620 Sage `question` Exception Channel + `waiting_human` Persistence

### AC-1
- Given Sage opens an exception `question` channel against a requirement at spec revision `R`
- When the Runtime persists the wait state
- Then Runtime records a `waiting_human` event with the anchor, the spec revision `R`, and the requirement ID; the requirement's `Decided` remains `⚠️`; no default answer is assigned.

### AC-2
- Given `waiting_human` is active for a requirement
- When the Runtime inspects the run state
- Then (a) the M-SPEC review round counter is unchanged from the pre-question value; (b) requirements approval (FR-0400) and M-LOCK (FR-0410) are still blocked for this run; (c) no design, implementation, Issue creation, or push proceeds against the run.

### AC-3
- Given `waiting_human` is active and `lk serve` is restarted
- When the user re-enters the chat window
- Then the opencode session restore makes the Sage prompt visible; independently, Runtime's `waiting_human` record is present in the persisted store and is independent of the session restore.

### AC-4
- Given `waiting_human` is active for spec revision `R`
- When a Human reply arrives under a different spec revision `R'`, or on a different anchor, or under a different correlation_id
- Then the reply is classified non-matching and is NOT auto-accepted; the round counter and gate-block states are unchanged.

### AC-5
- Given a matching Human reply lands on the same spec revision `R`
- When the Runtime resumes the task
- Then the requirement's `Decided` is updated only after the matching reply is recorded; the gate-block state changes only after subsequent gate checks succeed.

---

## FR-0700 M-TESTPLAN Author / Reviewer Division of Labor

### AC-1
- Given a `test-plan.md` is being authored
- When authorship is recorded
- Then the author is Archer; the reviewer is a registered S-tier Prism; Shield (if involved) is recorded as `feedback_only` and not as `reviewer`.

### AC-2
- Given an M-TESTPLAN approval signature is submitted
- When the program handler validates the signature
- Then signatures from Sage, non-tier-S roles, or agents not in the configured `prism_reviewers` set MUST be rejected with `m_testplan_approval_wrong_reviewer`; Prism's signature MUST be accepted; the run state evolves only after a valid Prism signature.

### AC-3
- Given the same M-TESTPLAN review digest is re-issued
- When the program handler processes it
- Then the call is idempotent: no double approval, no double rejection, no extra history rows.

---

## FR-0720 return-upstream with Fixed Targets and Downstream Stale

### AC-1
- Given an active, not-yet-released run
- When the user invokes return-upstream
- Then Runtime surfaces ONLY the fixed legal targets declared by the WorkflowDefinition; a user-typed arbitrary stage name MUST be rejected with `return_upstream_target_not_declared`.

### AC-2
- Given the user has not yet confirmed a target
- When the run is inspected
- Then the run is paused in `waiting_for_human`; no implementation work, no Issue creation, no `git push` proceeds until a target is confirmed.

### AC-3
- Given the user confirms a declared target and Runtime executes the return
- When the run ledger is inspected
- Then the target step and every step after it are marked `stale` / `superseded`; their artifacts, approvals, evidence and event records are retained (no file or Git-history deletion); their identities remain auditable (NFR-0300).

### AC-4
- Given a return-upstream has executed
- When the run is resumed at the chosen target
- Then the run re-passes through the subsequent review, requirements approval (FR-0400), M-LOCK (FR-0410), and Issue split (FR-0420) gates before any further implementation work; the bypass of any of these gates is not reachable.

---

## FR-0730 Irreversible-Side-effect Refusal on return-upstream

### AC-1
- Given a return-upstream would need to reverse an irreversible external side-effect (a public release, a published tag, a delivered external artifact, or any other side-effect outside Runtime's control)
- When Runtime evaluates the return
- Then Runtime refuses the automatic return and moves the run into `needs_attention`; no rollback is attempted.

### AC-2
- Given a refusal has been recorded
- When the audit log is inspected
- Then the entry contains actor (or system), reason, attempted target, the irreversible side-effect list (with publication / tag / artifact identity), and the timestamp — all in one event row.

### AC-3
- Given the run is in `needs_attention`
- When the run is checked
- Then the run does NOT auto-progress, does NOT re-enter requirements approval, and does NOT skip M-LOCK; only the Human's choice of (a) abandon the return and continue, or (b) start a new `bug_fix` / `new_feature` run per WorkflowDefinition rules, advances the state.

---

## FR-0740 Bounded Waiver Recording with Non-Waivable Invariants

### AC-1
- Given a waivable check failure
- When the user submits a waiver
- Then Runtime persists a waiver record binding at least: actor / principal, reason, target check identifier, target evidence digest, scope, revision / digest bound, creation timestamp, recheck condition, and the original failure reference.

### AC-2
- Given the waiver is recorded
- When the run is inspected
- Then the original `FAIL` evidence is preserved (NOT rewritten to PASS); the review surface continues to show both the failure and the waiver; the run MAY continue past that specific gate only if the waiver is bound and the check is on the waivable list.

### AC-3
- Given a waiver request targets a non-waivable check (requirements approval FR-0400, M-LOCK FR-0410, identity / secret / auth, revision CAS / atomicity, artifact freshness, Agent self-approval FR-0110, or release identity mismatch)
- When Runtime validates the request
- Then the request is rejected with `waiver_check_non_waivable`; the run MUST NOT advance; the audit log contains a single-event rejection row.

### AC-4
- Given a waiver was bound to evidence digest D
- When the underlying evidence digest changes to D' (e.g. the same check reruns)
- Then the waiver MUST be re-evaluated against D'; a stale waiver MUST NOT continue to suppress a FAIL.

---

## FR-0750 No-new-debt Adoption Preview / Apply / Touch-to-Clean / Fail-Safe

### AC-1
- Given the user invokes adoption preview on a project
- When Runtime runs the preview
- Then (a) the Git revision and workspace digest are pinned; (b) all applicable program checks run (lint / typecheck / test / security / docs / trace / anti-pattern); (c) the report partitions findings into: blocking, eligible for `baseline-known`, auto-fixable.

### AC-2
- Given a finding is marked `baseline-known`
- When the run is inspected
- Then the finding is recorded in a debt ledger keyed by `check_id + rule_id + finding_identity + source_revision + evidence_digest + scope / severity / status / owner / reason / review_condition / expires_at`; it is NOT marked PASS.

### AC-3
- Given a baseline file is modified for the first time after adoption
- When the modification is committed
- Then Runtime applies the full current applicable program checks to the entire file; if all checks pass, the file permanently exits `baseline-known` and is marked `managed`; reverting to the adoption content does NOT restore baseline.

### AC-4
- Given adoption preview or apply encounters any failure (network error, user cancel, program-handler exception, evidence inconsistency)
- When the run is rolled back
- Then user files are NOT altered; Git history is NOT rewritten; no new evidence is published; a deterministic retry is permitted but MUST NOT silently succeed after a prior failure.

### AC-5
- Given the user requests a baseline that targets a critical invariant (correctness, security, identity, release identity)
- When Runtime evaluates the request
- Then the baseline request is rejected at preview time with `baseline_critical_invariant`; the invariant does NOT enter the baseline ledger.

---

## FR-0800 Built-in Versioned Lifecycle Hook Scheduling

### AC-1
- Given a hook is declared
- When Runtime registers it
- Then the declaration contains `hook_id`, `hook_version`, lifecycle point, input / output schema, `blocking` flag, timeout, retry policy, idempotency policy, permissions, and redaction policy; undeclared hooks are refused with `hook_declaration_missing`.

### AC-2
- Given a hook is registered
- When Runtime dispatches it on lifecycle points (`after_semantic_result`, `after_human_decision`, session save, around `return-upstream`)
- Then the dispatch runs under a stable `correlation_id` bound to `run_id` / `step_id` / `attempt_id` / `revision`; it is NOT invoked by Agent prompt self-call.

### AC-3
- Given a hook is tagged `behavioral` vs `observational`
- When Runtime evaluates its authority
- Then behavioural hooks are pinned to a WorkflowDefinition version; observational hooks MAY be enabled globally but MUST NOT change run state on failure.

### AC-4
- Given a hook declaration is modified by a third party
- When Runtime compares the registered declaration to the persisted one
- Then Runtime detects the modification, refuses to honour the modified version, and records the event under the original correlation_id (NFR-0500).

---

## FR-0910 Cutover Entry Convergence and Old-workflow CLI Command Absence

> **Lex [RESOLVED]:** **BLOCKING — Copy-paste error: FR-0910 AC-1, AC-2, AC-3 are verbatim copies of FR-0700 (M-TESTPLAN) ACs, not the cutover CLI command-absence contract.**


>> **Sage:** Documentation-only correction applied to acceptance.md FR-0910 (no spec.md / Story / code / tests / templates / Agent / Runtime / git state change).

Replaced FR-0910 AC-1/2/3 (verbatim FR-0700 M-TESTPLAN copies) with three ACs that assert the authoritative command-absence contract from spec.md FR-0910 (lines 335-348) and Story BS-30 (stable command absence contract, 2026-07-17 supersede):

- AC-1 (post-cutover absence): post-cutover E2E enumerates the public CLI surface — registry dump, `lk --help`, shell-completion candidate list, every published command list, and the dispatcher routing table — and asserts every previously-registered workflow-advance command (incl. the `lk agent ...` family) is absent from each of those five surfaces; the only routable `lk` subcommands are the pre-cutover whitelist (`lk serve`, `lk upgrade`, other whitelisted ops); no half-cutover intermediate state is observable.

- AC-2 (plain unknown/unsupported-command path): invoking any removed `lk agent ...` command goes through the CLI's ordinary unknown/unsupported-command path with no specialised behaviour — no special error code, no deprecated-no-op exit-0 contract, no `cli_legacy_deprecated_noop` audit event (no Runtime-native-store payload either), no migration-warning text, no specialised stdout/stderr shape, no fallback to legacy Runtime/Agent/workflow; post-call run / project / Git / audit store state is byte-identical to pre-call; observed exit status and error message are indistinguishable from any other unknown `lk` subcommand on the same build.

- AC-3 (pre-cutover dogfood + atomic cutover): in the v0.14 dev window, a v0.13-baseline build still executes the legacy CLI workflow-advance commands (dogfood/debug preserved), while the post-cutover v0.14 build returns the AC-2 path; the cutover transition is atomic — no observable window where some old commands are registered and others are not, and no observable window where any removed command silently forwards to the legacy dispatcher.

Heading contract preserved: `## FR-0910 ...` stays at line 482; AC headings remain pure `### AC-1` / `### AC-2` / `### AC-3` with no suffix text. FR-0700 ACs (Archer authorship / Prism signature / idempotent re-issue) are unchanged — they remain the correct ACs for FR-0700. Lex root thread is left OPEN (Lex initiator owns resolution per skill rules).

FR-0910 in spec.md (lines 335-348) defines a detailed contract about:
1.  Cutover convergence: Web Chat becomes only development entry; old CLI commands removed from public surface.
2.  Command absence: removed commands MUST NOT appear in CLI registry, , shell completion, or any command list; dispatcher MUST NOT route them.
3.  Plain unknown/unsupported-command path: invocation MUST hit the CLI's ordinary unknown-command path with no special error code, no  audit event, no deprecated-no-op exit code contract, no migration warning text, no specialised stdout/stderr shape, no fallback to legacy Runtime/Agent/workflow.
4.  Byte-identical store before/after call: no external side-effect.
5.  E2E assertions: (a) post-cutover CLI does not register old workflow commands; (b) sample old command invocation follows plain unknown path; (c) pre-cutover v0.13 baseline still executes legacy CLI commands.

The current AC section (lines 484-498) addresses none of these. Instead it contains three verbatim M-TESTPLAN ACs (Archer authorship, Prism signature, idempotent re-issue), which are the correct content of FR-0700 but semantically impossible for FR-0910. This is a draft-first copy-paste accident — Sage needs to replace the three ACs with ACs that cover the cutover command-absence contract. The E2E ACs in FR-0920 AC-5 already reference the correct post-cutover assertions, so the FR-0910 ACs should align with the same contract.

**Action required:** Replace acceptance.md FR-0910 AC-1/2/3 with ACs that assert (i) post-cutover CLI command-registry absence, (ii) plain unknown-command path with no special exit code/audit event/state change, and (iii) pre-cutover v0.13 baseline still executes legacy CLI commands.


### AC-1
- Given the v0.14 release cutover transaction has committed and Runtime is on the post-cutover public surface
- When the E2E enumerates the public CLI surface (registry dump, `lk --help` output, shell-completion candidate list, and any published command list) and probes the dispatcher routing table
- Then every command that previously advanced the workflow under the v0.13 baseline (including the `lk agent ...` family) is absent from each of (i) the CLI registry, (ii) `--help`, (iii) shell completion, (iv) every published command list, and (v) the dispatcher routing table; the only `lk` subcommands that remain routable are the pre-cutover whitelist (`lk serve`, `lk upgrade`, and any other whitelisted ops commands) — no half-cutover intermediate state is observable.

### AC-2
- Given the post-cutover CLI surface is in effect (AC-1 holds)
- When a user invokes any command from the removed `lk agent ...` family (and one representative invocation per removed subcommand is exercised)
- Then the invocation is dispatched through the CLI's ordinary unknown / unsupported-command path with no specialised behaviour: (i) no special error code and no special exit-code contract (in particular, no deprecated-no-op exit-0 contract), (ii) no `cli_legacy_deprecated_noop` audit event is written to any audit store or Runtime-native store, (iii) no migration-warning text is emitted on stdout or stderr, (iv) no specialised stdout/stderr shape is required, (v) no fallback routes the call to legacy Runtime, legacy Agent, or legacy workflow, (vi) the post-call state of the run store, project store, Git tree, and audit store is byte-identical to the pre-call state (no mutation, no external side-effect); the observed exit status and error message are indistinguishable from the path taken by any other unknown / unsupported `lk` subcommand on the same CLI build.

### AC-3
- Given a v0.13-baseline build operating in the v0.14 development window (i.e. before the v0.14 release cutover transaction has committed) is installed alongside a post-cutover v0.14 build
- When an E2E step invokes the legacy workflow-advance CLI commands (the `lk agent ...` family) against the v0.13-baseline build, and then invokes the same commands against the post-cutover v0.14 build
- Then the v0.13-baseline build executes the legacy CLI commands (its dogfood/debug surface is preserved during the pre-cutover window); the post-cutover v0.14 build returns the same plain unknown / unsupported-command path described in AC-2 (no special exit-0, no `cli_legacy_deprecated_noop` audit event, no state change); the cutover transition between the two states is atomic — no observable window in which some old commands are registered while others are not, and no observable window in which any removed command silently forwards to the legacy dispatcher.

---

## FR-0920 Installed-wheel E2E and Louke Dogfood Acceptance

### AC-1
- Given an installed v0.14 wheel in an isolated workspace
- When the E2E harness completes a full `new_feature` journey (setup → Story → Go → requirements approval → design → M-LOCK → Issue split → implementation → authoritative tests → release → history archive)
- Then every step in the journey completes; no fixture is used to inject the shared store; the journey is reproducible from a clean checkout.

### AC-2
- Given the E2E (FR-0920) runs the `new_feature` journey
- When the harness inspects the Agent task ledger at the end
- Then Scout / Warden / Keeper task / session / dispatch counts are exactly zero; the closed program-result boundary (FR-0110) holds across Web / CLI / Chat / Agent callers; restart recovery (FR-0300) survives an `lk serve` restart mid-run.

### AC-3
- Given the E2E runs against an old workspace eligible for no-new-debt adoption
- When adoption applies
- Then no dual-authority state is produced (FR-0750 + NFR-0400); restart-recovery holds across the adoption transition.

### AC-4
- Given the E2E runs against a Spec with 31 active FR+NFR units
- When the harness reaches the scope-gate step
- Then `SPEC_SCOPE_TOO_LARGE` is returned; zero downstream side-effects (no anchor, no Issue, no approval, no lock); the `needs_story_split` state is restart-recoverable; the child Spec with ≤30 units completes independently (FR-0510 + FR-0520).

### AC-5
- Given the E2E runs the cutover harness
- When the harness verifies the post-cutover CLI surface
- Then: (a) no old workflow command is registered; (b) invoking `lk agent ...` goes through the plain `unknown` path with no special exit code, no special audit event, no state change; (c) the pre-cutover v0.13 baseline still executes its old commands (FR-0910).

### AC-6
- Given the E2E runs the exception-question harness
- When Sage opens a `question` channel and the user does not reply in the same spec revision
- Then `waiting_human` is persisted; the requirement `Decided=⚠️` is preserved; the round counter is unchanged; requirements approval and M-LOCK remain blocked; restart-survivability of the prompt is observable through both Runtime state and the opencode session restore path (FR-0620 + NFR-0700).

### AC-7
- Given the E2E Louke-dogfood step
- When Louke itself runs through the new `new_feature` workflow end-to-end
- Then public evidence from Story to history is retained; the dogfood run does NOT dispatch Scout / Warden / Keeper.

---

## NFR-0100 Per-Spec Scope Independence from Release Cumulative Limit

### AC-1
- Given two Specs in the same release (Spec A: 25 active units, Spec B: 25 active units)
- When Runtime evaluates each Spec against the gate
- Then each Spec passes per its own FR-0510 check; cumulative 50 across the release is NOT evaluated as a single gate.

### AC-2
- Given the hard gate is exceeded (≥31 active units in a Spec)
- When an actor / reason / scope is offered as a waiver
- Then the waiver attempt is rejected with `SPEC_SCOPE_TOO_LARGE` regardless of scope; the run does not advance.

### AC-3
- Given a release with multiple Specs
- When Runtime audits the per-Spec scope gate history
- Then each audit row identifies the Spec uniquely; no row attributes the cumulative release count to a single Spec.

---

## NFR-0200 Workflow Definition Immutability and Tampering Resistance

### AC-1
- Given a registered `(definition_id, version, contract_digest=D1)`
- When the E2E runs a tampering probe
- Then: (a) a same-id/same-version/different-digest re-registration is rejected with a deterministic error; (b) an attempted edit of an in-flight run's bound definition is rejected; (c) an attempt to soft-mutate the Catalog from a non-owner context is rejected. Each rejection is logged with a documented error code.

### AC-2
- Given a registered `(definition_id, version=1, contract_digest=D1)`
- When the operator adds `(definition_id, version=2, contract_digest=D2)`
- Then the in-flight run is NOT altered; the new version lives alongside the old and may be used for new runs only.

---

## NFR-0300 Spec / Acceptance / Issue / Commit Identity Independence from Workflow Changes

### AC-1
- Given a project's existing SPEC-IDs, FR/NFR IDs, AC IDs, GitHub Issue numbers, commit hashes, artifact digests, and evidence digests
- When the WorkflowDefinition version is bumped
- Then none of these identities is rewritten; new runs reference the same assets via their original identities.

### AC-2
- Given the workflow definition version is bumped
- When the Runtime evaluates approval/evidence/gate records for old runs
- Then a record is marked stale ONLY when the asset digest it binds has changed, NOT merely because the workflow definition version was bumped.

### AC-3
- Given a SPEC-ID is referenced by a still-in-flight run
- When the WorkflowDefinition is upgraded
- Then the in-flight run continues to resolve SPEC-ID to the same Spec document content and digest; new runs MAY reference it (if it is logically still relevant) or MAY use a new Spec (not automatically forced).

---

## NFR-0400 Adoption Ledger Integrity and No-Double-Authority

### AC-1
- Given two baseline finding records claim the same key (`check_id + rule_id + finding_identity + source_revision + evidence_digest + artifact_digest`)
- When Runtime inserts them
- Then the second insert is rejected with a deterministic error (`baseline_finding_key_collision`); the ledger integrity is preserved.

### AC-2
- Given adoption apply has completed
- When any legacy authority (legacy `current_stage`, ad-hoc file write, manual commit outside Runtime) attempts to mutate the ledger or the run
- Then the attempt is rejected with a deterministic error and recorded in the audit log under the rejection event type.

### AC-3
- Given the same pinned revision and the same check set
- When preview re-runs
- Then the bucketing, evidence digests, and ledger identities are identical across replays (no drift).

---

## NFR-0500 Hook Isolation from Transition / Gate / Program-result Authority

### AC-1
- Given a lifecycle hook is declared `behavioral` and pinned to a WorkflowDefinition version
- When the hook attempts to approve a gate, submit a program result, choose a next step, run an undeclared shell command, or bypass freshness / identity / CAS
- Then Runtime rejects the attempt with a deterministic error and logs it under the hook's correlation_id; the run state is unchanged by the rejected attempt.

### AC-2
- Given an `observational` hook is enabled globally
- When the hook fails (timeout, exception, network error)
- Then the failure is recorded but the originating run state is unchanged; the hook's timeout / retry policy is applied locally and does not consume the originating step's idempotency window.

### AC-3
- Given a registered hook declaration
- When a third party attempts to modify the declaration (declaration diff, lifecycle point, blocking/non-blocking flag, retry policy)
- Then Runtime detects the modification, refuses to honour the modified declaration, and records the event under the original correlation_id.

---

## NFR-0600 Web Chat Cutover Idempotency and Surface Integrity

### AC-1
- Given the cutover operation has been performed
- When the same cutover trigger digest is re-issued
- Then the operation is a no-op with the same pre/post digests; no half-cutover intermediate state is observable.

### AC-2
- Given cutover has taken effect
- When the post-cutover CLI surface is inspected (registry, `--help`, completion, dispatcher routes, audit-store query results)
- Then only the whitelisted operations (`lk serve`, `lk upgrade`, etc.) are present; no `cli_legacy_deprecated_noop` audit event type exists; no deprecated-no-op exit code contract exists; no migration warning text exists.

### AC-3
- Given the E2E runs the cutover harness
- When it captures the pre-cutover and post-cutover surface states
- Then the byte-level diff matches the expected post-cutover shape (registries equal; no deprecated-no-op layer); the assertions are program-level, not derivable solely from documentation.

---

## NFR-0700 Exception-question Channel: Non-default-decision / Non-round-consumption Guarantee

### AC-1
- Given `waiting_human` is active for a requirement (FR-0620)
- When Runtime is asked to advance the run, substitute a default answer, or roll a round
- Then Runtime refuses: the run does not advance past the gate; the round counter is unchanged; requirements approval (FR-0400) and M-LOCK (FR-0410) remain blocked.

### AC-2
- Given a Human reply arrives under a different spec revision, anchor, or correlation_id
- When Runtime classifies the reply
- Then the reply is classified non-matching; the round counter is unchanged; no requirement is auto-accepted.

### AC-3
- Given `lk serve` is restarted and the opencode session is cold-started from a fresh device
- When the Runtime state is queried
- Then `waiting_human` persists; the requirement's `Decided=⚠️`; the gate-block states are unchanged — independently of the session restore visibility path.

---

## No Acceptance

None. Every FR/NFR in `spec.md` (22 FR + 7 NFR = 29 active units) is covered above.
