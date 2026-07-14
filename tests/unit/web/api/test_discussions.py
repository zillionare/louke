"""TestClient tests for the /api/v12/discussions sub-app (FR-1901).

AC references covered:
- AC-FR1901-07: POST / creates a thread and returns its id; the persisted
  canonical form uses speaker/depth/status syntax that round-trips.
- AC-FR1901-07: GET /{thread_id} returns the canonical serialized form.
- AC-FR1901-07: POST /parse parses a canonical form; non-round-trippable input
  is rejected with a 400 and a reason.
- Round-trip: to_canonical then parse_canonical returns equivalent data.
"""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from louke.web.api.discussions import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory discussions sub-app."""
    return TestClient(create_app())


def test_create_thread_returns_thread_id(client: TestClient) -> None:
    """AC-FR1901-07: POST / creates a thread and returns 201 with thread id."""
    resp = client.post(
        "/",
        json={
            "doc_id": "spec.md",
            "anchor": "section-3",
            "speaker": "alice",
            "body": "needs clarification",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["thread_id"].startswith("thread_")
    assert body["doc_id"] == "spec.md"


def test_get_canonical_returns_speaker_depth_status(client: TestClient) -> None:
    """AC-FR1901-07: GET /{thread_id} returns the canonical speaker/depth/status form."""
    create_resp = client.post(
        "/",
        json={
            "doc_id": "spec.md",
            "anchor": "section-3",
            "speaker": "alice",
            "body": "needs clarification",
        },
    )
    thread_id = create_resp.json()["thread_id"]
    resp = client.get(f"/{thread_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["thread_id"] == thread_id
    canonical = body["canonical"]
    parsed = json.loads(canonical)
    # Canonical form must use speaker/depth/status syntax.
    assert parsed["speaker"] == "alice"
    assert parsed["depth"] == 1
    assert parsed["status"] == "open"


def test_parse_canonical_returns_parsed_dict(client: TestClient) -> None:
    """AC-FR1901-07: POST /parse parses a canonical form into a dict."""
    canonical = json.dumps(
        {
            "speaker": "bob",
            "depth": 2,
            "status": "resolved",
            "body": "fixed in commit abc",
            "anchor": "section-5",
            "doc_id": "architecture.md",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    resp = client.post("/parse", json={"canonical": canonical})
    assert resp.status_code == 200
    body = resp.json()
    parsed = body["parsed"]
    assert parsed["speaker"] == "bob"
    assert parsed["depth"] == 2
    assert parsed["status"] == "resolved"


def test_parse_invalid_canonical_returns_400(client: TestClient) -> None:
    """AC-FR1901-07: POST /parse with non-round-trippable input returns 400."""
    resp = client.post("/parse", json={"canonical": "not-valid-json"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "reason" in body


def test_round_trip_canonical_then_parse(client: TestClient) -> None:
    """AC-FR1901-07: to_canonical then parse_canonical returns equivalent data."""
    create_resp = client.post(
        "/",
        json={
            "doc_id": "test-plan.md",
            "anchor": "ac-3",
            "speaker": "carol",
            "body": "add edge case",
        },
    )
    thread_id = create_resp.json()["thread_id"]
    canonical_resp = client.get(f"/{thread_id}")
    canonical = canonical_resp.json()["canonical"]
    parse_resp = client.post("/parse", json={"canonical": canonical})
    assert parse_resp.status_code == 200
    parsed = parse_resp.json()["parsed"]
    assert parsed["speaker"] == "carol"
    assert parsed["depth"] == 1
    assert parsed["status"] == "open"
    assert parsed["body"] == "add edge case"
    assert parsed["anchor"] == "ac-3"
    assert parsed["doc_id"] == "test-plan.md"


def test_get_unknown_thread_returns_404(client: TestClient) -> None:
    """AC-FR1901-07: GET /{thread_id} for unknown thread returns 404."""
    resp = client.get("/thread_nonexistent")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"
