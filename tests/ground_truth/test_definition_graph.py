"""Ground-truth: independent expected topology for the ``new_feature`` workflow.

This is the *ground-truth* side of a drift-detection pair (gap-analysis §3
P1-1 / §4 Batch 3, issue #178 S5). It reads a hand-authored JSON fixture and
independently verifies the fixture is internally self-consistent using only
the Python standard library -- it does NOT import ``louke``. The matching
product-side check lives in ``tests/unit/runtime``: the catalog's
``new_feature`` definition must produce a structurally equivalent graph.

If either side changes without the other, the pair detects the drift: a
ground-truth test proves "we expect this shape", and the unit test proves
"the runtime produces this shape"; agreement between them is the contract.

AC references: FR-1201 (workflow graph nodes/edges), FR-1701 (catalog
validation), gap-analysis §3 P1-1 / §4 Batch 3.
"""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "expected_new_feature_topology.json"
)


def _load_expected() -> dict:
    """Load and return the hand-authored expected topology fixture."""
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _terminal_nodes(nodes: list[str], edges: list[dict]) -> set[str]:
    """Return node ids with no outgoing edge (independent terminal detection)."""
    sources = {edge["from_step"] for edge in edges}
    return {node for node in nodes if node not in sources}


def _reachable_from(start: str, edges: list[dict]) -> set[str]:
    """Return node ids reachable from ``start`` via a BFS over edges."""
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge["from_step"], []).append(edge["to_step"])
    seen: set[str] = set()
    queue = [start]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency.get(current, []))
    return seen


def _max_depth(start: str, edges: list[dict]) -> int:
    """Return the longest acyclic path length (in edges) from ``start``.

    The ``new_feature`` graph is a simple chain, so the longest path equals
    the edge count; computed recursively with memoisation for generality.
    """
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge["from_step"], []).append(edge["to_step"])
    memo: dict[str, int] = {}

    def depth(node: str) -> int:
        if node in memo:
            return memo[node]
        successors = adjacency.get(node, [])
        memo[node] = 0 if not successors else 1 + max(depth(s) for s in successors)
        return memo[node]

    return depth(start)


def test_fixture_shape_matches_new_feature_contract() -> None:
    """The fixture itself carries the expected ``new_feature`` identity fields."""
    expected = _load_expected()
    assert expected["definition_id"] == "new_feature"
    assert expected["version"] == "1"
    assert expected["start_step"] == "start"


def test_node_count_is_six() -> None:
    """The ``new_feature`` graph has exactly six nodes."""
    expected = _load_expected()
    assert len(expected["nodes"]) == 6


def test_edge_count_is_five() -> None:
    """The ``new_feature`` graph has exactly five directed edges."""
    expected = _load_expected()
    assert len(expected["edges"]) == 5


def test_terminal_node_is_complete() -> None:
    """The single terminal (zero-out-degree) node is ``complete``."""
    expected = _load_expected()
    terminals = _terminal_nodes(expected["nodes"], expected["edges"])
    assert terminals == {"complete"}


def test_all_nodes_reachable_from_start() -> None:
    """Every node is reachable from ``start`` (no orphan required steps)."""
    expected = _load_expected()
    reachable = _reachable_from(expected["start_step"], expected["edges"])
    assert reachable == set(expected["nodes"])


def test_max_depth_equals_edge_count_for_chain() -> None:
    """The ``new_feature`` chain depth equals its edge count (5 edges)."""
    expected = _load_expected()
    assert _max_depth(expected["start_step"], expected["edges"]) == 5


def test_edges_form_single_chain() -> None:
    """The edges form a single unbranched chain start -> ... -> complete."""
    expected = _load_expected()
    by_source: dict[str, dict] = {}
    for edge in expected["edges"]:
        assert edge["from_step"] not in by_source, "a node has >1 outgoing edge"
        by_source[edge["from_step"]] = edge
    # Every non-terminal node has exactly one outgoing edge.
    terminals = _terminal_nodes(expected["nodes"], expected["edges"])
    assert len(by_source) == len(expected["nodes"]) - len(terminals)
