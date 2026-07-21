"""FR-0300: Task graph program validation & Prism review.

Runtime validates the implementation task DAG for duplicate id, missing
dependency, cycle, write-scope conflict, orphan AC/task, and missing
implementation/verification responsibility.  Prism independently reviews
the graph for implementability, testability and design consistency.  Any
graph change creates a new revision and makes the old review stale.
Design gaps return to M-DESIGN (no Human); product gaps return to
M-SPEC/M-ACC only via Human.  Devon does not improvise design
(AC-FR0300-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "TASK_DUPLICATE_ID",
    "TASK_DEPENDENCY_MISSING",
    "TASK_GRAPH_CYCLE",
    "TASK_SCOPE_CONFLICT",
    "TASK_AC_ORPHAN",
    "TASK_ORPHAN",
    "TASK_MANIFEST_INCOMPLETE",
    "TASK_ROUTE_INVALID",
)


class TaskGraphValidationError(Exception):
    """A fail-closed task-graph validation rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Diagnostic:
    """A single validation diagnostic.

    Attributes:
        code: Stable error code from :data:`ERROR_CODES`.
        task_id: Task id the diagnostic concerns, if applicable.
        message: Human-readable diagnostic message.
    """

    code: str
    task_id: str = ""
    message: str = ""


@dataclass(frozen=True)
class ValidationReport:
    """Result of :meth:`TaskGraphValidator.validate`.

    Attributes:
        status: ``pass`` or ``fail``.
        diagnostics: Tuple of :class:`Diagnostic` describing every failure.
        graph_revision: The validated graph revision.
    """

    status: str
    diagnostics: tuple[Diagnostic, ...] = ()
    graph_revision: str = ""


@dataclass(frozen=True)
class PrismVerdict:
    """A Prism review verdict attached to a graph revision.

    Attributes:
        verdict: ``PASS`` or ``REVISE``.
        review_id: Stable review identity.
        subject_digest: ``sha256:<hex>`` of the reviewed graph bytes.
        status: ``current`` (default) or ``stale`` once a newer revision
            arrives.
    """

    verdict: str
    review_id: str
    subject_digest: str
    status: str = "current"


@dataclass(frozen=True)
class GapRoute:
    """A return-upstream route for an unaddressable graph gap.

    Attributes:
        target: ``M-DESIGN`` for technical gaps, ``M-SPEC/M-ACC`` for product.
        requires_human: ``True`` only for product gaps.
        evidence: Tuple of evidence anchors supporting the route.
    """

    target: str
    requires_human: bool
    evidence: tuple[str, ...] = ()


def route_gap(kind: str, *, evidence: tuple[str, ...] = ()) -> GapRoute:
    """Route an unaddressable gap to its definition target (AC-FR0300-01).

    Args:
        kind: ``design`` for a technical/design gap or ``product`` for a
            requirements/Acceptance gap.  Any other value raises
            ``TASK_ROUTE_INVALID`` (Devon does not improvise design).
        evidence: Tuple of evidence anchors (review id, finding id, ...).

    Returns:
        A :class:`GapRoute` with the target stage and Human-required flag.

    Raises:
        TaskGraphValidationError: With ``TASK_ROUTE_INVALID`` if ``kind`` is
            not ``design`` or ``product``.
    """
    if kind == "design":
        return GapRoute(target="M-DESIGN", requires_human=False, evidence=evidence)
    if kind == "product":
        return GapRoute(target="M-SPEC/M-ACC", requires_human=True, evidence=evidence)
    raise TaskGraphValidationError(
        "TASK_ROUTE_INVALID",
        f"unknown gap kind {kind!r}; only 'design' and 'product' are allowed",
    )


class TaskGraphValidator:
    """Program validator + Prism review store for task graphs (AC-FR0300-01)."""

    def __init__(self) -> None:
        self._reviews: dict[str, PrismVerdict] = {}

    def validate(self, graph: dict[str, Any]) -> ValidationReport:
        """Validate a task graph and return a :class:`ValidationReport`.

        Args:
            graph: Mapping with ``run_id``, ``baseline_id``,
                ``graph_revision``, ``requirements`` and ``tasks``.

        Returns:
            A :class:`ValidationReport` with ``status`` in ``pass|fail``.
        """
        diagnostics: list[Diagnostic] = []
        tasks = list(graph.get("tasks", []) or [])
        requirements = graph.get("requirements", {}) or {}

        ids: set[str] = set()
        for task in tasks:
            tid = task.get("task_id", "")
            if tid in ids:
                diagnostics.append(
                    Diagnostic("TASK_DUPLICATE_ID", tid, f"duplicate task_id {tid}")
                )
            ids.add(tid)
            if not task.get("devon_responsibility") or not task.get(
                "shield_responsibility"
            ):
                diagnostics.append(
                    Diagnostic(
                        "TASK_MANIFEST_INCOMPLETE",
                        tid,
                        "missing devon/shield responsibility",
                    )
                )
            if (
                not task.get("fr_ids")
                and not task.get("nfr_ids")
                and not task.get("ac_ids")
            ):
                diagnostics.append(
                    Diagnostic("TASK_ORPHAN", tid, "task has no FR/NFR/AC ownership")
                )

        for task in tasks:
            for dep in task.get("depends_on", []) or []:
                if dep not in ids:
                    diagnostics.append(
                        Diagnostic(
                            "TASK_DEPENDENCY_MISSING",
                            task.get("task_id", ""),
                            f"depends on unknown {dep}",
                        )
                    )

        diagnostics.extend(self._detect_cycles(tasks))
        diagnostics.extend(self._detect_scope_conflicts(tasks))
        diagnostics.extend(self._detect_ac_orphans(tasks, requirements))

        status = "fail" if diagnostics else "pass"
        return ValidationReport(
            status=status,
            diagnostics=tuple(diagnostics),
            graph_revision=str(graph.get("graph_revision", "")),
        )

    def _detect_cycles(self, tasks: list[dict[str, Any]]) -> list[Diagnostic]:
        by_id = {t.get("task_id", ""): t for t in tasks}
        visited: dict[str, int] = {}

        def dfs(node: str, path: list[str]) -> list[Diagnostic]:
            state = visited.get(node)
            if state == 0:
                return [
                    Diagnostic(
                        "TASK_GRAPH_CYCLE", node, "cycle: " + " -> ".join(path + [node])
                    )
                ]
            if state == 1:
                return []
            visited[node] = 0
            diags: list[Diagnostic] = []
            for dep in by_id.get(node, {}).get("depends_on", []) or []:
                diags.extend(dfs(dep, path + [node]))
            visited[node] = 1
            return diags

        out: list[Diagnostic] = []
        for task in tasks:
            out.extend(dfs(task.get("task_id", ""), []))
        return out

    def _detect_scope_conflicts(self, tasks: list[dict[str, Any]]) -> list[Diagnostic]:
        by_id = {t.get("task_id", ""): t for t in tasks}
        scopes = {
            t.get("task_id", ""): set(t.get("write_scopes", []) or []) for t in tasks
        }

        def is_ancestor(a: str, b: str) -> bool:
            stack = list(by_id.get(b, {}).get("depends_on", []) or [])
            seen: set[str] = set()
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                if cur == a:
                    return True
                stack.extend(by_id.get(cur, {}).get("depends_on", []) or [])
            return False

        out: list[Diagnostic] = []
        for i, t1 in enumerate(tasks):
            for t2 in tasks[i + 1 :]:
                a, b = t1.get("task_id", ""), t2.get("task_id", "")
                if is_ancestor(a, b) or is_ancestor(b, a):
                    continue
                overlap = scopes[a] & scopes[b]
                if overlap:
                    out.append(
                        Diagnostic(
                            "TASK_SCOPE_CONFLICT",
                            a,
                            f"tasks {a} and {b} share {sorted(overlap)}",
                        )
                    )
        return out

    def _detect_ac_orphans(
        self, tasks: list[dict[str, Any]], requirements: dict[str, Any]
    ) -> list[Diagnostic]:
        covered: set[str] = set()
        for task in tasks:
            for ac in task.get("ac_ids", []) or []:
                covered.add(ac)
        required = set(requirements.get("ac_ids", []) or [])
        orphan = sorted(required - covered)
        if orphan:
            return [Diagnostic("TASK_AC_ORPHAN", "", f"orphan AC ids: {orphan}")]
        return []

    def attach_prism_review(self, graph: dict[str, Any], verdict: PrismVerdict) -> None:
        """Attach a Prism review verdict to the graph's revision.

        Marks any prior verdict for a different revision as ``stale``.
        """
        revision = str(graph.get("graph_revision", ""))
        for existing_rev, existing in list(self._reviews.items()):
            if existing_rev != revision and existing.status == "current":
                self._reviews[existing_rev] = PrismVerdict(
                    verdict=existing.verdict,
                    review_id=existing.review_id,
                    subject_digest=existing.subject_digest,
                    status="stale",
                )
        self._reviews[revision] = verdict

    def current_prism_review(self, graph_revision: str) -> PrismVerdict | None:
        """Return the current Prism verdict for ``graph_revision`` or ``None``."""
        return self._reviews.get(graph_revision)

    def can_advance(self, graph: dict[str, Any]) -> bool:
        """Return ``True`` only when program validation and Prism PASS are current."""
        report = self.validate(graph)
        if report.status != "pass":
            return False
        revision = str(graph.get("graph_revision", ""))
        verdict = self._reviews.get(revision)
        if verdict is None or verdict.status != "current" or verdict.verdict != "PASS":
            return False
        return True
