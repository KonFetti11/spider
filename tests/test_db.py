"""
Unittests für spider.db.database – reifegrad/confidence-Berechnung,
protected fields, Audit-Log-Zeitstempel-Identität.

Siehe CLAUDE.md "Architecture invariants" – diese Tests decken genau die
dort beschriebenen Invarianten ab.
"""

from __future__ import annotations

import json

from spider.db.models import Node, now_ms


def make_node(id, parentId=None, issuer="tester", name="n", **kw) -> Node:
    ts = now_ms()
    return Node(
        id=id,
        parentId=parentId,
        active=True,
        reasoning="weil",
        summary="s",
        creationDate=ts,
        issuer=issuer,
        name=name,
        lastChange=ts,
        **kw,
    )


def test_leaf_node_unaccepted_has_zero_reifegrad(db):
    db.create_node(make_node("leaf-1"))
    node = db.get_node("leaf-1")
    assert node.reifegrad == 0.0


def test_leaf_node_accepted_has_full_reifegrad(db):
    db.create_node(make_node("leaf-1"))
    db.accept_node("leaf-1", issuer="agent", reason="entschieden")
    node = db.get_node("leaf-1")
    assert node.reifegrad == 1.0


def test_leaf_node_rejected_has_full_reifegrad(db):
    """Reifegrad misst ob EINE Entscheidung getroffen wurde – Ablehnung zählt auch."""
    db.create_node(make_node("leaf-1"))
    db.reject_node("leaf-1", issuer="agent", reason="verworfen")
    node = db.get_node("leaf-1")
    assert node.reifegrad == 1.0
    assert node.active is False


def test_internal_node_reifegrad_is_average_of_children(db):
    db.create_node(make_node("root-1"))
    db.create_node(make_node("child-1", parentId="root-1"))
    db.create_node(make_node("child-2", parentId="root-1"))

    db.accept_node("child-1", issuer="agent", reason="ok")
    # child-2 bleibt offen -> root reifegrad soll 0.5 sein
    root = db.get_node("root-1")
    assert root.reifegrad == 0.5

    db.reject_node("child-2", issuer="agent", reason="verworfen")
    root = db.get_node("root-1")
    assert root.reifegrad == 1.0


def test_recalculate_ancestors_propagates_multiple_levels(db):
    db.create_node(make_node("root-1"))
    db.create_node(make_node("mid-1", parentId="root-1"))
    db.create_node(make_node("leaf-1", parentId="mid-1"))

    assert db.get_node("root-1").reifegrad == 0.0

    db.accept_node("leaf-1", issuer="agent", reason="ok")

    assert db.get_node("mid-1").reifegrad == 1.0
    assert db.get_node("root-1").reifegrad == 1.0


def test_update_node_cannot_write_protected_fields(db):
    """confidence/reifegrad/id/creationDate dürfen nicht direkt per update_node gesetzt werden."""
    db.create_node(make_node("leaf-1"))
    original = db.get_node("leaf-1")

    db.update_node(
        "leaf-1",
        {"confidence": 0.9, "reifegrad": 0.9, "id": "hacked", "creationDate": 0, "summary": "neu"},
        issuer="agent",
        reason="versuch",
    )

    updated = db.get_node("leaf-1")
    assert updated.id == "leaf-1"
    assert updated.creationDate == original.creationDate
    assert updated.reifegrad == 0.0          # weiterhin unentschieden -> 0.0, nicht 0.9
    assert updated.summary == "neu"          # unprotected Feld wird normal übernommen


def test_update_node_creates_action_with_matching_timestamp(db):
    db.create_node(make_node("leaf-1"))
    updated = db.update_node("leaf-1", {"summary": "geändert"}, issuer="agent", reason="klarstellung")

    actions = db.get_actions("leaf-1")
    assert len(actions) == 1
    assert actions[0].date == updated.lastChange


def test_accept_and_reject_log_actions(db):
    db.create_node(make_node("leaf-1"))
    db.accept_node("leaf-1", issuer="agent-a", reason="entschieden")

    db.create_node(make_node("leaf-2"))
    db.reject_node("leaf-2", issuer="agent-b", reason="verworfen")

    actions_1 = db.get_actions("leaf-1")
    actions_2 = db.get_actions("leaf-2")
    assert len(actions_1) == 1 and actions_1[0].issuer == "agent-a"
    assert len(actions_2) == 1 and actions_2[0].issuer == "agent-b"

    change = json.loads(actions_2[0].change)
    assert change["active"]["new"] == 0
    assert change["status"]["new"] == "rejected"


def test_get_root_nodes_and_children(db):
    db.create_node(make_node("root-1"))
    db.create_node(make_node("root-2"))
    db.create_node(make_node("child-1", parentId="root-1"))

    roots = db.get_root_nodes()
    assert {r.id for r in roots} == {"root-1", "root-2"}
    assert [c.id for c in db.get_children("root-1")] == ["child-1"]
