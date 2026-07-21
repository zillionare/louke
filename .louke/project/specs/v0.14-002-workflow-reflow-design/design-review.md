---
reviewer: Prism
stage: M-DESIGN
review_round: 4
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
observed_reviewer_execution_digest: sha256:a3112e71e9a8c655f1e8259ef11db170881442423a80cabeb2dad2d9691e51c5
---

# M-DESIGN Independent Technical Review - Round 4

## Verdict

**REJECT**

The round-3 authority and release-schema blockers are remediated. Two current, design-baseline blockers remain. This review does not require activation of the candidate registry, runner, prompt bundle, CI, or Runtime target state. It does require an exact trusted-review binding and reusable program-owned task schemas, both necessary to implement the specified revise loop.

## Evidence summary

- Current disk hashes for Story, Spec, and Acceptance match the required digests. The candidate manifest independently recomputes to `sha256:5153a3879f54558ecfa7800c92d2eac540c919849a942116ec282783fbc9eb56`.
- All 35 manifest-declared artifact byte digests checked (inputs, documents, registry, 11 schemas, 7 contracts, prompt/staging/validation/runner artifacts) match current disk bytes.
- With `jsonschema==4.25.1`, all 11 schemas meta-validate; all 7 Louke contract instances, the Archer task positive control, and the Node/package.json/SemVer release positive fixture validate. Each of the 8 declared negative mutations fails at the declared schema boundary (`required`, `const`, `type`, or `additionalProperties`).
- Original B-1 is remediated in the candidate design: the Archer and Prism task schemas fix `dispatch.authority` to `Runtime/program`, providers are opaque execution transport metadata, and delivery returns to Runtime for validation/persistence. Architecture section 3 and the candidate prompt sources agree.
- Original B-2 is remediated: `release-version-1.0.0.schema.json` fixes only the strict generic envelope/mapping/types/closed objects; release-specific Louke values reside in the instance. The heterogeneous Node positive fixture proves the same schema accepts non-Python host facts.
- The documentation and manifest explicitly close 34 AC, 15 IF, 16 ARC, and 7 contract kinds, with required layers, fixtures, commands, ground truth, recovery, and fail-closed candidate-not-installed behavior. No plain literal secret/password/API-key hit was found in candidate JSON artifacts.

## Core blockers

### B-1 - Trusted Prism reviewer binding is not fresh against the current active deployment

`design-artifacts/prompts/reviewer-binding.candidate.json:4` and `deployment-readback.candidate.json:9` bind the trusted active reviewer at `.opencode/agents/prism.md` to `sha256:fba0...e005`. Fresh disk hashing of that exact path produces `sha256:a311...51c5`, not the bound digest. The binding declares this condition stale/fatal (`reviewer-binding.candidate.json:8-9`), and IF-PRM-01 / FR-2050 require the executing trusted reviewer identity to be exact before review or activation.

This does not demand candidate activation. It prevents this candidate review evidence from being current: the claimed trusted reviewer is not the deployed reviewer on disk. Refresh the trusted-active qualification/readback and reviewer binding from the real execution bundle, then have Runtime dispatch a new identity-bound review; if that active bundle is not eligible, establish a valid trusted bundle first. Regenerate all affected manifest/bundle/reviewer digests.

### B-2 - Program-owned Agent task-input schemas are still revision-specific instance schemas

`registry/agent-io/archer-design-task-input-1.0.0.schema.json:18,29-30,33` hard-codes this Spec path, Spec ID, remediation revision identity/revision, and artifact-manifest path. `prism-design-review-task-input-1.0.0.schema.json:29-30,34` hard-codes the same Spec and remediation revision. Both are registered as globally program-owned schemas with fixed identity and version `1.0.0`. Independent mutations of the valid Archer task to a new Spec ID, a next design revision, or its corresponding authorized write path each fail schema validation.

This contradicts FR-2500: a REVISE must create a new Archer revision while freshness requires a new Runtime dispatch. The active `1.0.0` schema would reject that next task unless Runtime mutates/re-publishes a supposedly program-owned schema for every revision, defeating registry identity/version semantics and the reusable M-DESIGN program contract required by FR-1900, FR-2600, and NFR-0600.

Make the Agent task schemas reusable but strict: retain fixed role, M-DESIGN stage, Runtime authority, transport shape, output schema identity, digest formats, closed objects, and path-containment rules; put the current Spec ID, design revision, authorized path set, reviewed-manifest identity/digest, and delivery artifact path only in the Runtime-signed task instance. Add a valid next-revision task fixture plus negative path/scope/freshness cases, then regenerate registry, manifest, prompt, reviewer, provenance, and validation records.

## Non-blocking observations

- Candidate-versus-active separation is correctly explicit. Do not activate candidate artifacts merely to resolve this review.
- The current `design-review.md` replacement makes the prior author-task input stale by its stated freshness policy, as expected after a review result; Runtime must issue a new task if another author remediation occurs.

## Files changed

- `.louke/project/specs/v0.14-002-workflow-reflow-design/design-review.md`
