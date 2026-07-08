# louke v0.7.3

This release packages the completed v0.7 workflow hardening work that landed
after v0.7.2.

## Highlights

- Harden stage gates so `M-ARCH` and `M-TESTPLAN` pass verdicts must come from
  real reviewer commands, not self-recorded artifacts.
- Add standardized stage result artifacts and make `Maestro advance` consume
  those artifacts with provenance checks.
- Fix `lk board opencode` so bundled skills are installed into
  `.opencode/skill/` and consistently use the `lk-` prefix.
- Finish the historical contract cleanup so docs, prompts, CLI examples, and
  tests all align on `lk agent <role>`.

## What changed

| Area | Change |
|---|---|
| Stage gates | `Prism` and `Sage` now emit reviewer artifacts through `review-arch` / `review-testplan`; `record-*` commands can no longer mint `pass` for gated review stages. |
| Maestro enforcement | `Maestro` now validates reviewer artifact provenance, including `source_command == "review"` and stable `contract_bundle_hash` checks. |
| Stage results | Archer / Prism / Keeper / Sage artifacts are normalized under `.louke/project/stage-results/{spec_id}/{stage}/`, with waiver support and stricter gate consumption. |
| Board install | `lk board opencode` now installs bundled skills under `.opencode/skill/` and normalizes the `lk-` prefix to avoid collisions. |
| Prompt and docs | Agent prompts and README files now consistently use `lk agent <role>` and the current Librarian `distill` contract. |
| Test coverage | Added regression tests for reviewer-artifact tampering, board skill installation, CLI contract alignment, and related workflow drift. |

## Verification

- Full bats suite passes on the release candidate workspace before tagging.
- Release automation remains tag-driven: pushing `v0.7.3` triggers the existing
  GitHub Actions workflow to build and publish the wheel/sdist.
