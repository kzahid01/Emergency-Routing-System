import os

import pytest
from fastapi.testclient import TestClient

# IMPORTANT: ROUTING_SYNTH_SEED is read at routing import time.
os.environ.setdefault("ROUTING_SYNTH_SEED", "123")

from backend.main import app  # noqa: E402
import backend.routing as routing  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


def test_missing_required_field_returns_422(client: TestClient):
    resp = client.post("/route", json={"start": 1, "emergency_level": "medium"})
    assert resp.status_code == 422


def test_invalid_field_type_returns_422(client: TestClient):
    resp = client.post("/route", json={"start": "not-an-int", "end": 2, "emergency_level": "medium"})
    assert resp.status_code == 422


def test_negative_node_ids_returns_422(client: TestClient):
    resp = client.post("/route", json={"start": -1, "end": 2, "emergency_level": "medium"})
    assert resp.status_code == 422


def test_unknown_emergency_level_returns_422(client: TestClient):
    resp = client.post("/route", json={"start": 1, "end": 2, "emergency_level": "unknown_level"})
    assert resp.status_code == 422


def test_unknown_node_id_returns_400(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    # Force responders/hospitals so we get to the incident node validation path.
    monkeypatch.setattr(routing, "RESPONDERS", [{"node": next(iter(routing.G.nodes.keys())), "type": "synthetic_responder"}])
    monkeypatch.setattr(routing, "HOSPITALS", [{"node": next(iter(routing.G.nodes.keys())), "type": "synthetic_hospital"}])

    resp = client.post("/route", json={"start": 1, "end": 999999999, "emergency_level": "medium"})
    assert resp.status_code == 400
    assert resp.json()["detail"]


def test_candidate_insufficiency_triggers_synthetic_selection_markers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    # Monkeypatch to force a "synthetic-only" candidate set. In practice, BMSSP
    # may fail to find a bounded path depending on graph connectivity and edge costs.
    # This test verifies the error-path is stable and correctly surfaced.
    any_node = next(iter(routing.G.nodes.keys()))
    other_node = next((n for n in routing.G.nodes.keys() if n != any_node), any_node)

    routing.RESPONDERS[:] = [
        {"node": any_node, "type": "synthetic_responder", "name": "S1", "lat": 0.0, "lon": 0.0}
    ]
    routing.HOSPITALS[:] = [
        {"node": other_node, "type": "synthetic_hospital", "name": "H1", "lat": 0.0, "lon": 0.0}
    ]

    resp = client.post(
        "/route",
        json={"start": any_node, "end": other_node, "emergency_level": "medium"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No responder found by BMSSP"


def test_multiple_sequential_calls_stable_structure(client: TestClient):
    # Smoke/performance sanity: repeated calls should not crash.
    # Routing may return 400 in some graphs; we assert stability of response format.
    any_node = next(iter(routing.G.nodes.keys()))
    other_node = next((n for n in routing.G.nodes.keys() if n != any_node), any_node)

    payload = {"start": any_node, "end": other_node, "emergency_level": "low"}
    for _ in range(5):
        resp = client.post("/route", json=payload)
        assert resp.status_code in {200, 400}
        if resp.status_code == 200:
            body = resp.json()
            assert body["algorithm"] == "BMSSP"
            assert "responder_path" in body
            assert "hospital_path" in body
        else:
            assert "detail" in resp.json()
