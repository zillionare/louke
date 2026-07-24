# v0.14-004 workspace-onboarding — fixtures

This directory holds **no** fixtures of its own. Mode B v0.14-004 uses
the pre-existing host fixtures (notably
`tests/fixtures/v014_workflow_reflow/harness.py`) for the OpenCode
stand-in and isolated workspace, plus per-test synthetic hosts built
in `tests/integration/v014_workspace_onboarding/_mode_b.py`.

## Why no fixtures here?

Mode B requires every test to:

1. Use ``importlib.util.find_spec`` to detect Devon artifacts, falling
   back to a ``MagicMock`` contract check; no fixture injection of
   real ``louke.web.*`` modules is needed because the helper queries
   them through the public ``find_spec`` API.
2. Run inside a synthetic host project (per ``test-plan`` §3.2 and
   Shield §3.3); the ``synthetic_host_project`` context manager in
   ``_mode_b`` seeds ``.louke/project/project.toml`` with a per-run
   ``workspace_id_marker`` so two tests cannot collide.
3. Verify that the host project's registry does not leak Louke's own
   schema (see ``test_ac_synthetic_host__isolation`` in the integration
   suite); this is what the synthetic host fixture guards.

## External stand-ins

The v0.14-004 tests do **not** spin up new external stand-ins. The
existing v0.14-001 OpenCode stand-in already speaks the public OpenCode
HTTP protocol and records every call into a JSON-Lines ledger; that
satisfies the test-plan §2.4 ``opencode-matrix`` requirement of
``list成功/run失败|单模型成功|全失败|timeout|malformed``.

The Git stand-in (``git init -b main`` + a local bare remote) is
provided by ``harness.synthetic_bare_remote`` for IF-ENV-02.

## Secret canary

The synthetic host project never holds a real secret. The
``test_synthetic_host_setup_state_does_not_persist_real_secret`` test
proves this by emitting a per-run canary of the form
``SECRET_V014004_<random8hex>`` and scanning every file in the
synthetic project tree for the canary.
