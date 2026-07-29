"""
API-Tests über FastAPI TestClient – isoliert, kein laufender Server nötig.
Spiegelt die Checks aus test_poc.py (Live-E2E), aber pytest-fähig.
"""

from __future__ import annotations


def test_create_node_and_get_it(api_client):
    resp = api_client.post(
        "/nodes",
        json={"name": "Root", "reasoning": "weil", "summary": "s", "issuer": "tester"},
    )
    assert resp.status_code == 201
    node = resp.json()
    assert node["reifegrad"] == 0.0

    fetched = api_client.get(f"/nodes/{node['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == node["id"]


def test_get_unknown_node_is_404(api_client):
    resp = api_client.get("/nodes/does-not-exist")
    assert resp.status_code == 404


def test_accept_node_raises_reifegrad_and_root_stats(api_client):
    root = api_client.post(
        "/nodes",
        json={"name": "Root", "reasoning": "weil", "summary": "s", "issuer": "tester"},
    ).json()

    before = api_client.get("/tree/stats").json()
    assert before["root_reifegrad"] == 0.0

    accept = api_client.post(
        f"/nodes/{root['id']}/accept",
        json={"issuer": "tester", "reason": "entschieden"},
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    after = api_client.get("/tree/stats").json()
    assert after["root_reifegrad"] == 1.0
    assert after["completion_percentage"] == 100.0


def test_create_node_with_unknown_parent_is_404(api_client):
    resp = api_client.post(
        "/nodes",
        json={
            "name": "Child",
            "reasoning": "weil",
            "summary": "s",
            "issuer": "tester",
            "parentId": "missing-parent",
        },
    )
    assert resp.status_code == 404


def test_actions_endpoint_lists_audit_log(api_client):
    node = api_client.post(
        "/nodes",
        json={"name": "Root", "reasoning": "weil", "summary": "s", "issuer": "tester"},
    ).json()
    api_client.post(f"/nodes/{node['id']}/accept", json={"issuer": "tester", "reason": "ok"})

    actions = api_client.get("/actions", params={"knoten_id": node["id"]}).json()
    assert len(actions) >= 1
    assert any(a["knotenId"] == node["id"] for a in actions)


def test_reject_node_sets_inactive(api_client):
    node = api_client.post(
        "/nodes",
        json={"name": "Root", "reasoning": "weil", "summary": "s", "issuer": "tester"},
    ).json()

    resp = api_client.post(
        f"/nodes/{node['id']}/reject",
        json={"issuer": "tester", "reason": "verworfen"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is False
    assert body["status"] == "rejected"
