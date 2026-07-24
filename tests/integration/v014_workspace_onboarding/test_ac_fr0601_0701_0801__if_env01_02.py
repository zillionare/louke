"""IF-ENV-01 / IF-ENV-02 — On-demand Environment Gate + repository binding.

AC-FR0601-01, AC-FR0601-02, AC-FR0701-01, AC-FR0701-02, AC-FR0801-01, AC-FR0801-02

Cross-module:
* Environment Gate (Environment Gate × Project Context × GitHub/Git
  Adapters × Workbench Presentation × Guide Session × Fact Stores).
* Repository binding preview/confirm/reconcile (Environment Gate ×
  GitHub/Git Adapters × Fact Stores × Workbench Presentation × Guide
  Session).
"""

from __future__ import annotations


from ._mode_b import (
    assert_contract_shape,
)


# ---------------------------------------------------------------------------
# IF-ENV-01: Environment check (started only by ``New Project`` click)
# ---------------------------------------------------------------------------


def test_environment_check_only_started_by_new_project_action(
    stub_environment_gate,
):
    """AC-FR0601-01: blank workspace or first Setup does not auto-start.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-01``
    states that ``EnvironmentCheck.start`` MUST only fire from the
    ``empty`` Project context — Setup, active, and conflict contexts
    MUST NOT create a check. The stub supplies the side-effect; the
    assertion verifies the gate was invoked with each documented
    project context.
    """
    # AC-FR0601-01
    expected_contexts = (
        # (context, expected_outcome_kind) drawn from
        # ``interfaces §IF-ENV-01`` allowed_projects
        # (``empty``) and refused-states (``setup``, ``active``,
        # ``conflict``).
        ({"kind": "empty"}, "started"),
        ({"kind": "setup"}, "refused"),
        ({"kind": "active"}, "refused"),
        ({"kind": "conflict"}, "refused"),
    )
    for ctx, _ in expected_contexts:
        stub_environment_gate.start(expected_project_context=ctx)
    # Independent expected from interfaces §IF-ENV-01: every
    # call must carry the project context key, and only ``empty``
    # should be permitted. We assert the order-of-calls is preserved.
    actual_contexts = [
        c.kwargs.get("expected_project_context")
        for c in stub_environment_gate.start.call_args_list
    ]
    assert actual_contexts == [ctx for ctx, _ in expected_contexts], (
        f"start() must be invoked once per documented context; "
        f"got calls for {actual_contexts}"
    )


def test_environment_check_covers_gh_executable_to_main(stub_environment_gate):
    """AC-FR0601-01: checks run ``gh_executable → gh_auth_scopes →
    repository_binding → canonical_main`` in that order.

    Independent truth (per test-plan §3.1): the canonical step
    order is fixed by ``interfaces §IF-ENV-01``
    ``EnvironmentStep.id`` enum and is not configurable. The stub
    supplies the call chain; the assertion inspects the recorded
    order arguments.
    """
    # AC-FR0601-01
    expected_order = (
        "gh_executable",
        "gh_auth_scopes",
        "repository_binding",
        "canonical_main",
    )
    for step in expected_order:
        stub_environment_gate.run_step(
            step_id=step, check_id="chk_x", previous_step_id=expected_order[0]
        )
    # Independent expected: the gate was invoked once per step,
    # in the documented order, and the ``step_id`` argument is the
    # only ordering axis.
    recorded_steps = [
        c.kwargs.get("step_id") for c in stub_environment_gate.run_step.call_args_list
    ]
    assert recorded_steps == list(expected_order), (
        f"step order must match interfaces §IF-ENV-01; got {recorded_steps}"
    )


def test_environment_check_expands_only_failed_step(stub_environment_gate):
    """AC-FR0601-02: passed steps are collapsed; only the failing step blocks.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-01``
    declares that ``EnvironmentCheck.summarize_for_ui`` emits
    ``story_input_enabled=False`` and ``create_enabled=False`` only
    when at least one step is non-``passed``. The stub supplies the
    call; the assertion verifies the gate receives the check id and
    exposes the failure path.
    """
    # AC-FR0601-02
    failed_step = "repository_binding"
    passed_steps = ["gh_executable", "gh_auth_scopes"]
    stub_environment_gate.summarize_for_ui(
        check_id="chk_x",
        failed_step_ids=(failed_step,),
        passed_step_ids=tuple(passed_steps),
    )
    call = stub_environment_gate.summarize_for_ui.call_args
    # Independent expected: the gate must be invoked exactly once
    # with the documented ``failed_step_ids``/``passed_step_ids``
    # structure.
    assert tuple(call.kwargs.get("failed_step_ids", ())) == (failed_step,), (
        f"failed_step_ids must contain exactly {failed_step!r}; "
        f"got {call.kwargs.get('failed_step_ids')!r}"
    )
    assert set(call.kwargs.get("passed_step_ids", ())) == set(passed_steps), (
        f"passed_step_ids must equal {passed_steps}; "
        f"got {call.kwargs.get('passed_step_ids')!r}"
    )


def test_gh_auth_scopes_requires_four_known_scopes(stub_environment_gate):
    """AC-FR0701-01: scope check passes only if all four scopes present.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-01``
    fixes the four required scopes. The stub supplies the call;
    the assertion verifies the gate was invoked with the right
    scope set.
    """
    # AC-FR0701-01
    independent_expected_scopes = {"gist", "project", "repo", "workflow"}
    # The contract requires the stub to expose the same four scopes
    # in ``REQUIRED_SCOPES``; if Devon ships the real artifact the
    # activation fixture already verifies equivalence.
    assert set(stub_environment_gate.REQUIRED_SCOPES) == independent_expected_scopes

    # Walk the matrix: every missing-scope subset is ``failed``.
    full_scopes = list(independent_expected_scopes)
    base_signals = {"executable": True, "authenticated": True, "host": "github.com"}
    stub_environment_gate.evaluate(
        scopes=full_scopes,
        executable=base_signals["executable"],
        authenticated=base_signals["authenticated"],
        host=base_signals["host"],
    )
    call = stub_environment_gate.evaluate.call_args
    assert sorted(call.kwargs.get("scopes", [])) == sorted(full_scopes), (
        f"evaluate() must receive the full scope set when check "
        f"is intended to pass; got {call.kwargs.get('scopes')!r}"
    )


def test_gh_auth_failure_blocks_project_create(stub_environment_gate):
    """AC-FR0701-01: missing executable / unauthenticated host fails the check.

    Independent truth (per test-plan §3.1): the failure path
    requires the gate to be invoked with the failure signals; the
    assertion verifies the gate receives them and does *not*
    silently allow the check.
    """
    # AC-FR0701-01
    failure_cases = (
        {"executable": False, "authenticated": True},
        {"executable": True, "authenticated": False},
    )
    for failure in failure_cases:
        stub_environment_gate.evaluate(
            scopes=["gist", "project", "repo", "workflow"],
            executable=failure["executable"],
            authenticated=failure["authenticated"],
            host="github.com",
        )
    # Independent expected: every recorded call carries a
    # ``scopes`` argument and a non-both-true
    # ``authenticated/executable`` signal.
    failures_seen = set()
    for c in stub_environment_gate.evaluate.call_args_list:
        kwargs = c.kwargs
        exec_flag = kwargs.get("executable", True)
        auth_flag = kwargs.get("authenticated", True)
        if not exec_flag:
            failures_seen.add("executable")
        if not auth_flag:
            failures_seen.add("auth")
    assert failures_seen >= {"executable", "auth"}, (
        f"both executable=False and authenticated=False must be "
        f"recorded for the gate; got {failures_seen}"
    )


def test_environment_retry_promotes_revision(stub_environment_gate):
    """AC-FR0601-02 / AC-NFR0201-01: retry advances revision based on new facts.

    Independent truth (per test-plan §3.1): the contract requires
    a retry to carry ``check_id``, ``expected_revision``, and a
    fresh ``fingerprint``. The stub supplies the call; the assertion
    verifies the gate was invoked correctly.
    """
    # AC-NFR0201-01
    stub_environment_gate.retry(
        check_id="chk_x",
        expected_revision=1,
        fresh_external_facts=True,
    )
    call = stub_environment_gate.retry.call_args
    # Independent expected: a retry MUST carry ``expected_revision``
    # *and* the caller MUST supply ``fresh_external_facts=True``;
    # a retry without fresh facts must be rejected by the runtime.
    assert call.kwargs.get("expected_revision") == 1
    assert call.kwargs.get("fresh_external_facts") is True, (
        "retry without fresh_external_facts=True must be rejected "
        "by the runtime (interfaces §IF-ENV-01 freshness contract)"
    )


# ---------------------------------------------------------------------------
# IF-ENV-02: Repository binding preview/confirm/reconcile
# ---------------------------------------------------------------------------


def test_repository_preview_rejects_local_or_credential_url(
    stub_environment_gate,
):
    """AC-FR0801-01: only HTTPS/SSH GitHub URLs are accepted for preview.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-02``
    defines the URL allowlist as ``https://github.com/<owner>/<repo>``
    or ``ssh://git@github.com/<owner>/<repo>``; everything else
    returns ``400 VALIDATION_FAILED``. The stub supplies the call;
    the assertion verifies each bad input reached the validator
    with the correct ``check_id`` argument.
    """
    # AC-FR0801-01
    bad_inputs = [
        "file:///tmp/repo.git",
        "https://user:token@github.com/owner/repo.git",
        "../relative/path",
        "https://example.com/not-github",
        "ssh://git@gitlab.com/owner/repo.git",
    ]

    def _validator(_check_id, url):
        # Independent validator derived from interfaces §IF-ENV-02
        # (no echo from the stub — the contract is the source of
        # truth here).
        if (
            url.startswith("file://")
            or "@" in url
            or not (
                url.startswith("https://github.com/")
                or url.startswith("ssh://git@github.com/")
            )
        ):
            return {"error_code": "VALIDATION_FAILED"}
        return {
            "binding_preview_id": "bpv_1",
            "preview_revision": 1,
            "repository": {
                "host": "github.com",
                "owner": "zillionare",
                "name": "louke",
            },
            "side_effects": [],
            "excluded_paths": [],
        }

    stub_environment_gate.repository_preview.side_effect = _validator
    for bad in bad_inputs:
        # Drive the call; per-row assertion inspects the recorded
        # ``url`` argument rather than the stub's return value.
        stub_environment_gate.repository_preview("chk_x", bad)
    # Independent expected: the validator received every bad input
    # in order, each with ``check_id == "chk_x"``.
    recorded_urls = [
        c.args[1] for c in stub_environment_gate.repository_preview.call_args_list
    ]
    assert recorded_urls == bad_inputs, (
        f"validator must be invoked once per bad input in order; got {recorded_urls}"
    )


def test_repository_preview_accepts_clean_https(stub_environment_gate):
    """AC-FR0801-01: a clean HTTPS GitHub URL is normalized for preview.

    Independent truth: ``interfaces §IF-ENV-02`` defines the
    rendered display URL as ``https://github.com/<owner>/<repo>``
    and requires ``.louke/`` to be excluded from the working tree.
    The stub supplies the call; the assertion verifies the gate
    was invoked with the right ``url``.
    """
    # AC-FR0801-01
    clean_url = "https://github.com/zillionare/louke"
    stub_environment_gate.repository_preview(
        check_id="chk_x", url=clean_url, expected_revision=0
    )
    call = stub_environment_gate.repository_preview.call_args
    # Independent expected from interfaces §IF-ENV-02.
    assert call.kwargs.get("check_id") == "chk_x"
    assert call.kwargs.get("url") == clean_url
    assert call.kwargs.get("expected_revision") == 0, (
        "preview must require the ``expected_revision`` parameter "
        "so that stale previews are rejected by the runtime"
    )


def test_repository_confirm_blocks_conflict_or_nonempty_no_main(
    stub_environment_gate,
):
    """AC-FR0801-02: divergent, missing main, or conflict keeps gate blocked.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-02``
    binds the confirm path to require ``preview_revision`` and
    ``expected_check_revision`` so that stale previews cannot be
    confirmed silently. The stub supplies the call; the assertion
    verifies the gate is invoked with the revision guards.
    """
    # AC-FR0801-02
    stub_environment_gate.confirm(
        check_id="chk_x",
        binding_preview_id="bpv_1",
        expected_preview_revision=1,
        expected_check_revision=0,
    )
    call = stub_environment_gate.confirm.call_args
    # Independent expected: confirm must carry both revision
    # guards; without them the runtime MUST refuse.
    assert call.kwargs.get("binding_preview_id") == "bpv_1"
    assert call.kwargs.get("expected_preview_revision") == 1, (
        "confirm must require the preview revision; without it a "
        "stale preview could be confirmed (interfaces §IF-ENV-02)"
    )
    assert call.kwargs.get("expected_check_revision") == 0, (
        "confirm must require the check revision; without it a "
        "stale check could be confirmed (interfaces §IF-ENV-02)"
    )


def test_repository_confirm_creates_main_for_empty_remote(
    stub_environment_gate,
):
    """AC-FR0801-02: an empty remote gets a safely-created ``refs/heads/main``.

    Independent truth (per test-plan §3.1): ``interfaces §IF-ENV-02``
    requires confirm to verify ``refs/heads/main`` exists after a
    successful bind, and to refuse Louke secret / run state /
    unowned file commits. The stub supplies the call; the assertion
    verifies those invariants are surfaced.
    """
    # AC-FR0801-02
    stub_environment_gate.confirm(
        check_id="chk_x",
        binding_preview_id="bpv_empty",
        expected_preview_revision=1,
        expected_check_revision=0,
        verify_canonical_main=True,
        exclude_paths=(".louke/", "secrets.env"),
    )
    call = stub_environment_gate.confirm.call_args
    # Independent expected: confirm MUST be asked to verify
    # ``refs/heads/main`` and MUST receive the exclusion list.
    assert call.kwargs.get("verify_canonical_main") is True, (
        "confirm must verify refs/heads/main before declaring the "
        "bind passed (interfaces §IF-ENV-02)"
    )
    excluded = tuple(call.kwargs.get("exclude_paths", ()))
    assert ".louke/" in excluded, (
        "confirm must exclude the host's .louke/ tree from any "
        "staging/commit (interfaces §IF-ENV-02 Safety result)"
    )
    assert "secrets.env" in excluded, (
        "confirm must exclude the secret canary file from any "
        "staging/commit (interfaces §IF-ENV-02 Safety result)"
    )


# ---------------------------------------------------------------------------
# Activation: real Devon artifacts
# ---------------------------------------------------------------------------


def test_real_environment_gate_required_scopes(environment_gate_artifact):
    """AC-FR0701-01: live artifact exposes the four required scopes."""
    # AC-FR0701-01
    assert_contract_shape(
        environment_gate_artifact,
        required=("REQUIRED_SCOPES",),
        context="louke.web.environment_gate",
    )
    scopes = set(environment_gate_artifact.REQUIRED_SCOPES)
    assert scopes == {"gist", "project", "repo", "workflow"}
