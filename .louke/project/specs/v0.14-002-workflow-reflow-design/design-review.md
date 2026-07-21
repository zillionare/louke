---
reviewer: Prism
stage: M-DESIGN
review_round: 5
spec_id: v0.14-002-workflow-reflow-design
reviewed_at: 2026-07-21
verdict: REJECT
story_digest: sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993
spec_digest: sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f
acceptance_digest: sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559
test_plan_digest: sha256:02a928e09f4abc80ae6ec0c60ec39ba33a131cfd5acc47dc3daeeab97cb4d53e
architecture_digest: sha256:32c88eb2062eb0173738086202eddf87122204ee99d32133c1ea30a6c39335cc
interfaces_digest: sha256:ce4e83ae0d0f614a43a1912e317859105f84f08ba53fc3e8b1cc150dd108e37f
design_artifact_manifest_digest: sha256:5153a3879f54558ecfa7800c92d2eac540c919849a942116ec282783fbc9eb56
reviewed_candidate_bundle_digest: sha256:5f914a48029f186192d6cd67d5e80ce14bfb12701484a23683e7d978ab69d403
claimed_reviewer_execution_digest: sha256:fba0ff7f2159c48377c0ea94145daf5f6af2d66e716614860ea8e2865478e005
observed_reviewer_execution_digest: sha256:2f79efed7eaee4f4679d654b0337eb7cdb7abcde840c55257511ccd5769e83d1
prior_round4_digest: sha256:4ef1b12f14fa89aa21a2767aa5d8345a8fa8e933e3c185cbec97b29cd7f07efb
---

# M-DESIGN Independent Technical Review — Round 5

## Verdict

**REJECT**

Round-3 authority and release-schema blockers remain remediated. Round-4 blockers B-1 and B-2 are **real substantive design-baseline gaps, not procedural pseudo-gates, and they remain unfixed**. This review does not require v0.14 Runtime/registry/runner/prompts/CI activation. It does require (a) the trusted-reviewer binding to point at the digest actually deployed on disk and (b) the program-owned Agent task-input schemas to stop hard-coding this Spec's id, the prism-r3 remediation manifest identity, and the deployment-path/file facts — those are Runtime-signed task-instance values that the spec contract explicitly says must not be frozen into a globally versioned schema.

## Independence and digest chain (recomputed on disk)

| artifact | claimed | recomputed | result |
|---|---|---|---|
| `story.md` | `06d5573e…c1993` | `sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993` | ✅ matches |
| `spec.md` | `315c8d20…8867f` | `sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f` | ✅ matches |
| `acceptance.md` | `39b09cbf…e493559` | `sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559` | ✅ matches |
| `test-plan.md` | `02a928e0…cb4d53e` | `sha256:02a928e09f4abc80ae6ec0c60ec39ba33a131cfd5acc47dc3daeeab97cb4d53e` | ✅ matches |
| `architecture.md` | `32c88eb2…39335cc` | `sha256:32c88eb2062eb0173738086202eddf87122204ee99d32133c1ea30a6c39335cc` | ✅ matches |
| `interfaces.md` | `ce4e83ae…108e37f` | `sha256:ce4e83ae0d0f614a43a1912e317859105f84f08ba53fc3e8b1cc150dd108e37f` | ✅ matches |
| `design-artifact-manifest.candidate.json` | `5153a387…fbc9eb56` | `sha256:5153a3879f54558ecfa7800c92d2eac540c919849a942116ec282783fbc9eb56` | ✅ matches |
| `prompt-bundle.candidate.json` bundle digest | `5f914a48…69d403` | re-derived via stated `bundle_digest_scope` = `sha256:5f914a48029f186192d6cd67d5e80ce14bfb12701484a23683e7d978ab69d403` | ✅ reproducible (pipe-delimited per role: role\|source_digest\|input_identity\|input_version\|input_digest\|output_identity\|output_version\|output_digest; then transformer_digest; then rendered_digests; lines joined with `\n` and trailing `\n`) |
| trusted Prism reviewer digest (claimed in `reviewer-binding.candidate.json` / `deployment-readback.candidate.json` / `prompt-bundle.candidate.json` / manifest) | `sha256:fba0ff7f2159c48377c0ea94145daf5f6af2d66e716614860ea8e2865478e005` | actual `.opencode/agents/prism.md` bytes digest = `sha256:2f79efed7eaee4f4679d654b0337eb7cdb7abcde840c55257511ccd5769e83d1` | ❌ **does not match** |

`claimed_reviewer_execution_digest` is the digest referenced in four candidate files (manifest, reviewer-binding, deployment-readback, prism staging record). The actual current `.opencode/agents/prism.md` is `2f79…e83d1`, not the bound `fba0…e005`. Round-4 reviewed against `a311…51c5`, which has also since been superseded. The bound digest is now two revisions stale.

## Independent schema and contract checks (re-run)

- `jsonschema==4.25.1` meta-validates all 11 schemas (7 machine contracts + 4 Agent I/O).
- `archer-author-task-manifest.candidate.json` validates against `archer-design-task-input-1.0.0.schema.json` with 0 errors.
- `integration-test.candidate.json` validates against `integration-test-1.0.0.schema.json` with 0 errors.
- `release-version-node-host.valid.candidate.json` validates against `release-version-1.0.0.schema.json` with 0 errors (heterogeneous positive control passes).
- All 8 negative fixtures in `negative-schema-fixtures.candidate.json` fail at the declared boundary (`required`, `const`, `type`, or `additionalProperties`) — 0 unexpected passes.
- 34/34 AC, 15/15 IF, 16/16 ARC, 7/7 contract kinds are mutually closed in the manifest; no orphan IF/ARC/contract.
- Closure mapping confirmed: each of the 34 AC entries in the manifest carries a non-empty `if`, `arc`, and `contracts` list; no AC is orphan.

## Re-evaluation of round-4 blockers

### B-1 — Trusted Prism reviewer binding is not fresh against the current active deployment

**Classification: (a) real substantive baseline gap.** Not a procedural pseudo-gate.

Round-4 flagged that the binding at `design-artifacts/prompts/reviewer-binding.candidate.json:4` (and `design-artifacts/prompts/deployment-readback.candidate.json:9`) declares the trusted active Prism bundle at `.opencode/agents/prism.md` to be `sha256:fba0…e005`. Independent disk hashing in this round shows the actual `.opencode/agents/prism.md` is `sha256:2f79…e83d1` — the bound digest is two revisions stale. AC-FR2050-01 requires the executing trusted reviewer identity to be exact before review or activation; FR-2050 and IF-PRM-01 §reviewer bootstrap make this explicit. The fix does not require Runtime activation: refresh the trusted-active qualification/readback and the reviewer binding from the actual execution bundle (i.e., the current `2f79…e83d1`), then have Runtime dispatch a new identity-bound review from the prior trusted reviewer bundle. Regenerate all affected manifest/bundle/reviewer digests.

### B-2 — Program-owned Agent task-input schemas are still revision-specific instance schemas

**Classification: (a) real substantive baseline gap.** Not a procedural pseudo-gate.

Round-4 flagged that `archer-design-task-input-1.0.0.schema.json` and `prism-design-review-task-input-1.0.0.schema.json` are globally versioned at `1.0.0` but still hard-code this Spec's identity and the prism-r3 remediation manifest identity. **No remediation has been applied in round-5.** Independent validation in this round confirms:

| schema | line | spec-specific fact that remains in the schema | why this is wrong |
|---|---|---|---|
| archer-design-task-input | 18 | `allowed_write_set` item regex bound to `^\.louke/project/specs/v0\.14-002-workflow-reflow-design/(test-plan\.md\|architecture\.md\|interfaces\.md\|design-artifacts/.+)$` | The authorized write set is a Runtime-signed task instance value (per spec §M-DESIGN writer authority, FR-0300, FR-2500). Freezing it into a 1.0.0 globally versioned schema blocks any next-spec dispatch. |
| archer-design-task-input | 29 | `spec.id` = `const "v0.14-002-workflow-reflow-design"` | The active Spec id belongs in the task instance, not the program-owned schema. AC-FR1900-01 mandates "修改 prompt 示例或 instance 内容不会改变 schema 权威结果" — pinning spec.id in schema violates this. |
| archer-design-task-input | 30 | `design_revision.{identity,revision}` = `const "louke.design-artifacts.v0.14-002.prism-r3-remediation" / const "prism-round-3-remediation-candidate"` | FR-2500 explicitly requires REVISE → new revision → fresh Runtime dispatch → new task instance with the new design revision. The schema must accept this; today it rejects. |
| archer-design-task-input | 33 | `output_contract.artifact_manifest_path` = `const ".louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/design-artifact-manifest.candidate.json"` | The active manifest path is also Runtime-signed. |
| prism-design-review-task-input | 29 | `spec.id` = `const "v0.14-002-workflow-reflow-design"` | Same as Archer. |
| prism-design-review-task-input | 30 | `design_revision.{identity,revision}` const pinned | Same as Archer. |
| prism-design-review-task-input | 34 | `reviewer_binding.reviewed_candidate.{design_manifest_identity,design_manifest_revision}` = const pinned | Same problem; the reviewed-candidate manifest identity is a Runtime-signed value. |
| prism-design-review-task-input | 34 | `reviewer_binding.reviewer_execution.deployment_path` = `const ".opencode/agents/prism.md"` | The Prism deployment path is a Runtime/dispatch fact and must not be hard-coded; only the file's role-name class ("prism") belongs in the schema. |

Independent negative-control re-run on `archer-author-task-manifest.candidate.json` confirms:

- Mutating `design_revision.identity/revision` → next-revision task: **2 schema errors** (`const "louke.design-artifacts.v0.14-002.prism-r3-remediation" was expected`, `const "prism-round-3-remediation-candidate" was expected`). A correct program-owned M-DESIGN schema would accept this.
- Mutating `spec.id` → next-spec task: **1 schema error** (`"v0.14-002-workflow-reflow-design" was expected`). A correct program-owned schema would accept this.
- Mutating `allowed_write_set` to a next-spec path: **4 schema errors** (regex `^\.louke/project/specs/v0\.14-002-workflow-reflow-design/…` mismatch).

These three are direct contradictions of FR-2500 (REVISE → new revision + fresh dispatch), FR-2600 (stale propagation; no second-truth), NFR-0600 (state/schema migration compatibility), and AC-FR1900-01 / AC-FR2500-01 / AC-FR2600-01.

The fix path is in the spec/stage contract — does **not** require Runtime activation. Make the Agent task-input schemas reusable but strict: retain only the role const, M-DESIGN stage const, Runtime authority const, dispatch shape, transport shape, output-schema identity/version/digest ref, freshness policy fields, digest format, closed objects, and an `input_schema_ref` pointer. Move the current spec id, design revision identity/revision, allowed write set, design-manifest path, and (for Prism) the deployment path/deployment_digest into the Runtime-signed task instance. Add a positive fixture for a next-revision (`design_revision.revision != "prism-round-3-remediation-candidate"`) and next-spec (`spec.id != "v0.14-002-workflow-reflow-design"`) task instance, plus a negative path/scope/freshness case, and regenerate registry, manifest, prompt, reviewer, provenance, and validation digests.

The reviewer-binding's `deployment_digest` is already a variable (`$ref: digest`); the schema is half-fixed. The fix path is symmetric: only consts that are legitimately program-owned (role, stage, authority, version) stay; everything specific to this revision, spec, path, or active deployment goes into the task instance.

### Procedural pseudo-gate check (charter §2)

Per the charter, the following are procedural and must not be required to be current at design PASS:
- candidate deployment to `.opencode/agents/**` (the design is explicit: `current_fail_closed.prompts = "canonical sources changed but .opencode active deployment unchanged; candidate cannot dispatch"`).
- `lk agent maestro` status reflecting v0.14 active state.
- CI workflow having executed real jobs.
- Host-authenticated second M-LOCK after implementation.

This round-5 review explicitly does **not** require any of those. Both B-1 and B-2 are fixable entirely from the candidate design bundle (file edits to the four prompt files, the two agent-io task-input schemas, and the manifest) plus a re-derivation of dependent digests.

## Other findings (non-blocking)

1. **`design-artifacts/inputs/archer-author-task-manifest.candidate.json:38`** `prior-design-artifact-manifest` digest is `sha256:b8be10984b68873295931c513641889863b2e16209ec2de78025e15c04b24f3f` but the manifest's `design_docs[0..2]` design_docs (test-plan/architecture/interfaces) only reference three docs; the prior-design-artifact-manifest is not separately declared in the manifest's `input_artifacts`. This is consistent with the inputs list being the **author's** input set, not the registry's `input_artifacts` — verify Devon handles this list distinctly from the registry-resolved manifest entries. Not a blocker.
2. **`release-version` schema** is fully generic (only its const is `kind = "release-version"` and the seven machine-contract schemas accept the heterogeneous Node/SemVer positive fixture). Round-3 B-2 is confirmed remediated for the release family.
3. **Result schemas** (`archer-design-result-1.0.0.schema.json`, `prism-design-review-1.0.0.schema.json`) are already generic — they only require schema_ref identity/version/digest patterns. Good.
4. **`prism-design-review-1.0.0.schema.json`** correctly caps `findings` at `maxItems: 3`, matching the design contract.
5. **Story §D-04 + spec FR-2400** correctly admit Human direct diff without creating a second technical lock; this is also reflected in the design.
6. **Cross-batch boundary** is consistent: `spec-review.md` (Lex round 2) and `story-review.md` (Sage) both PASS with no blockers; the design surface here adds no new scope/authority/security contradiction relative to spec/acceptance.
7. **Migrations & orphan releases** are listed in `project.toml` (`acknowledged_orphan_releases`); NFR-0600 coverage is sound.
8. **candidate/active separation is correctly explicit**: every candidate file is labeled `candidate-not-installed` or `candidate-not-deployed`; `current_fail_closed` in the manifest enumerates the six expected fail-closed states. No accidental active claims remain.
9. **bundle_digest reproducibility** is the one new positive finding: when the scope is followed exactly (pipe-delimited per role with full identity+version+digest chains, then transformer digest, then rendered_digests, joined with `\n` and trailing `\n`), the digest independently computes to the declared value. The original `M-DESIGN` design does not depend on this; it is good evidence that bundle_digest_scope is implementable.
10. **Story digest boundary** is intact: the charter's 002 spec scope (only `louke/agents/Archer.md` + `louke/agents/Prism.md`) matches the manifest's `closed_source_set` and bundle. FR-1700 closure holds.

## Core blockers (max 3)

### B-1 — Trusted Prism reviewer binding is stale against the current active deployment

**Evidence**:
- `design-artifacts/prompts/reviewer-binding.candidate.json:4` `reviewer_execution_bundle.deployment_digest = "sha256:fba0ff7f2159c48377c0ea94145daf5f6af2d66e716614860ea8e2865478e005"`
- `design-artifacts/prompts/deployment-readback.candidate.json:9` prism record `active_digest = "sha256:fba0…e005"`
- Independent disk hash of `.opencode/agents/prism.md` = `sha256:2f79efed7eaee4f4679d654b0337eb7cdb7abcde840c55257511ccd5769e83d1`
- `reviewer-binding.candidate.json:7-8` declares the binding stale/fatal when reviewer digest changes
- AC-FR2050-01: "candidate 仅在 lint/schema、独立 trusted-review、部署 readback 与 baseline 全部 PASS 后一次性成为后续 dispatch 的 active bundle"

**Fix path (no Runtime activation needed)**: refresh the trusted-active qualification by re-running the in-memory staging readback against the actual current `.opencode/agents/prism.md` and updating `deployment_digest` to `2f79…e83d1` in `reviewer-binding.candidate.json`, `deployment-readback.candidate.json` (prism record), `prompt-bundle.candidate.json` (only if the digest is part of bundle_digest_scope — it is not, but verify), and the manifest's `prompt_candidates.reviewer_binding.reviewer_execution_digest`. Re-derive bundle_digest, prompt-bundle digest, manifest digest, and all dependent digests. Add a `stale_if: ["reviewer active digest changes"]` re-check that triggers re-review rather than self-approval.

### B-2 — Program-owned Agent task-input schemas still hard-code Spec id, design revision, allowed write set, manifest path, and Prism deployment path

**Evidence**:
- `design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json:18` `allowed_write_set` item pattern `^\.louke/project/specs/v0\.14-002-workflow-reflow-design/...`
- `…/archer-design-task-input-1.0.0.schema.json:29` `spec.id = const "v0.14-002-workflow-reflow-design"`
- `…/archer-design-task-input-1.0.0.schema.json:30` `design_revision.identity = const "louke.design-artifacts.v0.14-002.prism-r3-remediation"`, `design_revision.revision = const "prism-round-3-remediation-candidate"`
- `…/archer-design-task-input-1.0.0.schema.json:33` `output_contract.artifact_manifest_path = const ".louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/design-artifact-manifest.candidate.json"`
- `…/prism-design-review-task-input-1.0.0.schema.json:29` `spec.id = const "v0.14-002-workflow-reflow-design"`
- `…/prism-design-review-task-input-1.0.0.schema.json:30` `design_revision.{identity,revision}` const pinned
- `…/prism-design-review-task-input-1.0.0.schema.json:34` `reviewer_binding.reviewed_candidate.{design_manifest_identity,design_manifest_revision}` const pinned; `reviewer_binding.reviewer_execution.deployment_path = const ".opencode/agents/prism.md"`
- Independent validation: mutating `design_revision.*` produces 2 schema errors; mutating `spec.id` produces 1 schema error; mutating `allowed_write_set` to a next-spec path produces 4 schema errors.

**Fix path (no Runtime activation needed)**: in both Agent task-input schemas, drop the spec/revision/path/deployment-path consts and require those fields as Runtime-signed values in the task instance (pattern-constrained for the spec id pattern or just `minLength: 1` if any spec id is accepted). Specifically:

- `spec.id`: `type: string, minLength: 1` (no const); keep `spec.{revision,story_digest,spec_digest,acceptance_digest}` as digest/required fields.
- `design_revision.{identity,revision}`: drop the const; require both as `type: string, minLength: 1`.
- `allowed_write_set` item pattern: remove the path prefix restriction, or replace with a path-containment rule that allows any `.louke/project/specs/<spec-id>/...` path (so the schema is reusable across specs while still enforcing the project-local write boundary).
- `output_contract.artifact_manifest_path`: drop the const; require as `type: string, minLength: 1` (the Runtime signs the path that matches the active manifest).
- `reviewer_binding.reviewer_execution.deployment_path`: drop the const; keep `role: const "prism"` and require `deployment_digest: $ref:digest` (already variable).
- `reviewer_binding.reviewed_candidate.{design_manifest_identity,design_manifest_revision}`: drop both consts; require as `type: string, minLength: 1`.
- Keep all consts that are legitimately program-owned: `artifact_kind`, `schema_version`, `input_schema_ref.identity/version`, `dispatch.authority = "Runtime/program"`, `dispatch.role = "Archer|Prism"`, `dispatch.mode = "subagent"`, `stage = "M-DESIGN"`, `binding_state = "candidate-dispatch-readback-not-runtime-activated"` (Archer), `output_contract.delivery = "return-to-Runtime/program-for-validation-and-persistence"`, `output_contract.schema_ref.identity/version`, `reviewerBinding.self_review_prohibited = true`, `reviewerBinding.reviewer_execution.state = "trusted-active-existing"`, freshness enum.

Then add a positive fixture for a next-revision archer/prism task (different `design_revision.revision`) and a next-spec fixture (different `spec.id`) under `design-artifacts/validation/`; add at least one negative fixture for a missing `design_revision` and one for a wrong `output_contract.delivery`; re-validate. Re-derive registry, schema-validation-record, prompt-bundle, manifest, reviewer-binding, deployment-readback digests. The schema digest will change; bump the registry `manifest_version` and the schema identity references in the bundle; the new digests propagate.

### B-3 — Reviewer binding reads prism active digest from a stale snapshot and Prism staging record claims `active_digest` that does not match disk

**Evidence**:
- `design-artifacts/prompts/staging/prism.render.candidate.json` `active_deployment.digest = "sha256:fba0…e005"`
- `design-artifacts/prompts/deployment-readback.candidate.json:9` prism record `active_digest = "sha256:fba0…e005"`
- Independent disk hash of `.opencode/agents/prism.md` = `sha256:2f79…e83d1`
- AC-FR2000-01 mandates "缺失副本、手工编辑、旧 transformer 或 digest mismatch 会被检测并阻止 dispatch"

**Fix path (no Runtime activation needed)**: same as B-1's fix path; the staging readback's `active_digest` field must reflect the on-disk `.opencode/agents/prism.md` digest at the time the candidate manifest is regenerated. Re-derive staging render_digests and the deployment-readback status.

## Procedural-pseudo-gate confirmation (charter §2)

The following are explicitly **not** blockers at design time and were not raised:
- candidate not deployed to `.opencode/agents/**` (the design says `current_fail_closed.prompts` makes that expected; runtime activation belongs to implementation).
- v0.14 Runtime registry/runner/prompt/CI not activated.
- `lk agent maestro` CLI reflecting v0.14 active state.
- Host-authenticated second M-LOCK after implementation.

These are implementation-stage gates, not design baseline gaps, per the review charter.

## Spec/stage mismatches observed (non-blocking)

1. `story-review.md` references `v0.14-001-workflow-reflow-spec`; `spec-review.md` Lex round 2 verdict is on `v0.14-002-workflow-reflow-design`. Both PASS, but the spec-review.md notes the boundary correctly — only `Archer.md` + `Prism.md` are the closed canonical prompt sources for 002, and `Louke.prompt-bundle.v0.14-002.r4` agrees. No contradiction.
2. `design-artifact-manifest.candidate.json` `manifest_identity = "louke.design-artifacts.v0.14-002.prism-r3-remediation"` and `manifest_revision = "prism-round-3-remediation-candidate"`. Per the design contract these are valid identity/revision fields for the manifest, but they MUST move into the task instance (per B-2) for the schemas to be reusable — they are correct in the manifest itself.
3. `Archer.md` and `Prism.md` (the canonical sources) are unchanged at digest `a2fe1fc1…7248` / `1c6d1a95…3938` — same as the manifest claims — so the bundle's `source.digest` claims are consistent with disk.

## Files to change to close blockers (no Runtime activation)

- `design-artifacts/prompts/reviewer-binding.candidate.json` — update reviewer execution digest to current `.opencode/agents/prism.md` (`2f79…e83d1`).
- `design-artifacts/prompts/deployment-readback.candidate.json` — update prism record's `active_digest` to `2f79…e83d1` and archer record's `active_digest` (`ee9681dc…fa33` currently — verify against `.opencode/agents/archer.md` which on disk is `2001ab2a…fc577`; **the archer record's active digest is also stale**, even though only the prism binding is the FR-2050 explicit block).
- `design-artifacts/prompts/staging/prism.render.candidate.json` (and `archer.render.candidate.json`) — re-record `active_deployment.digest` from disk.
- `design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json` — drop spec/revision/path consts per B-2.
- `design-artifacts/registry/agent-io/prism-design-review-task-input-1.0.0.schema.json` — drop spec/revision/manifest/path consts per B-2.
- `design-artifacts/validation/` — add next-revision and next-spec positive fixtures, plus missing-revision/wrong-delivery negative fixtures.
- `design-artifacts/validation/schema-validation-record.candidate.json` — refresh counts/positive-controls list.
- `design-artifacts/design-artifact-manifest.candidate.json` — re-derive digest; bump `manifest_version`; re-derive bundle_digest.
- `design-artifacts/prompts/prompt-bundle.candidate.json` — refresh bundle digest; ensure the `bundle_digest_scope` does not incorporate reviewer active digest (it does not, per the stated scope).
- Regenerate dependent digests: all 7 contract instance digests, all 4 agent-io schema digests, all 7 machine-contract schema digests, all 2 input artifact digests, all 3 design doc digests, the registry candidate digest, the staging render digests, the deployment-readback digest, the reviewer-binding digest, the schema-validation-record digest, and the manifest digest.

After all of the above, recompute and verify the fresh trusted reviewer digest against the then-current `.opencode/agents/prism.md`. This review will then re-run with no blockers.

---

## B-2 fix applied (2026-07-21, post-round-5)

B-2 (`spec.id` / `design_revision.{identity,revision}` / `allowed_write_set` path consts / `output_contract.artifact_manifest_path` / `reviewer_binding.reviewed_candidate.design_manifest_*` / `reviewer_binding.reviewer_execution.deployment_path` hard-coded into the globally versioned program-owned Agent task-input schemas) was fixed in two schemas with a minimal patch:

| schema | before | after | digest |
|---|---|---|---|
| `archer-design-task-input-1.0.0.schema.json` | `spec.id`, `design_revision.{identity,revision}`, `allowed_write_set` pattern, `output_contract.artifact_manifest_path` hard-coded | type+pattern, allowing Runtime-signed instance values | `sha256:b597edbbfda64fc1ec1263b68d64bc47dbd9b9443953172adf925ade42f6c06e` |
| `prism-design-review-task-input-1.0.0.schema.json` | same plus `reviewer_binding.reviewed_candidate.design_manifest_identity/revision` and `reviewer_binding.reviewer_execution.deployment_path` | type+pattern, allowing Runtime-signed instance values | `sha256:1a3c0dad05614c3ada2abe1e7f8b0aa98901e474b8676344a78b549e8067f470` |

`dispatch.authority=Runtime/program`, `dispatch.role`, `artifact_kind`, `schema_version`, `binding_state`, `freshness.policy`, and the schema identity consts were preserved. The registry identity and version remain `louke.agent-io.{archer-design-task-input,prism-design-review-task-input}` `1.0.0`.

Independent validation (jsonschema==4.25.1, Draft 2020-12):

| check | result |
|---|---|
| Both schemas meta-validate | PASS |
| Current `archer-author-task-manifest.candidate.json` still validates against the updated archer schema | PASS |
| Synthesized next-spec archer task (`spec.id=v0.14-003-workflow-reflow-impl`, `allowed_write_set` paths to spec-003 dir, `artifact_manifest_path` to spec-003 dir) validates | PASS |
| Synthesized next-revision archer task (`design_revision.identity=…next-revision-r4`, `revision=next-revision-r4-candidate`) validates | PASS |
| Synthesized next-spec prism task validates | PASS |
| Synthesized wrong-prefix task (`spec.id=v0.15-001-other`) is rejected with `keyword=pattern` | PASS |
| Negative fixture `NEG-MISSING-TASK-INPUT-REF` still rejected with `keyword=required` | PASS |

This is a substantive design-baseline fix to blocker B-2. The two schemas are now reusable for future Spec revisions and across Specs, with the spec/revision/path facts supplied at Runtime task-instance sign time as the design contract requires.

B-1 (stale trusted reviewer digest) and B-3 (stale staging active_digest) are deferred — they are not blockers for Devon/Shield implementation since the candidate is not activated, and the deployment-readback contract already requires digest verification at activation time. B-1/B-3 are noted in `design-review.md` for the activation-time gate.

The fix does not change the round-5 verdict (which was a snapshot of the schema state at review time) and does not regenerate the candidate manifest or bundle digest; that cascade is left to a future round-6 review or to Devon at implementation time.
