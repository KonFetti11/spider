"""
Spider Framework – FastAPI-Anwendung (REST-API).

Alle Datenbankzugriffe der AI laufen über diesen Server.
Basis-URL: http://localhost:8765
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Optional, List

# Projektwurzel im Suchpfad
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from spider.db.database import get_db
from spider.db.models import Node, Action, now_ms
from spider.server.schemas import (
    NodeCreate, NodeUpdate, NodeReject, NodeAccept,
    NodeResponse, NodeTreeResponse,
    ActionCreate, ActionResponse,
    SuccessResponse, ErrorResponse, TreeStatsResponse,
)

# ---------------------------------------------------------------------------
# App-Instanz
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Spider – AI Traceability Framework",
    description=(
        "Lokaler HTTP-Server für das Spider-Framework. "
        "Ermöglicht AI-Agents den strukturierten Zugriff auf den Entscheidungsbaum."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _node_to_response(node: Node) -> NodeResponse:
    return NodeResponse(**node.to_dict())


def _action_to_response(action: Action) -> ActionResponse:
    return ActionResponse(**action.to_dict())


def _build_tree_response(node_dict: dict) -> NodeTreeResponse:
    """Konvertiert ein verschachteltes Node-Dict rekursiv in NodeTreeResponse."""
    children = [_build_tree_response(c) for c in node_dict.pop("children", [])]
    return NodeTreeResponse(**node_dict, children=children)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Info"])
def root():
    return {"name": "Spider API", "version": "0.1.0", "status": "running"}


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Node-Endpunkte
# ---------------------------------------------------------------------------

@app.get("/nodes", response_model=List[NodeResponse], tags=["Nodes"])
def get_all_nodes(active_only: bool = Query(False, description="Nur aktive Nodes zurückgeben")):
    """Gibt alle Nodes zurück (flache Liste). Baumstruktur über parentId erschließbar."""
    db = get_db()
    nodes = db.get_all_nodes()
    if active_only:
        nodes = [n for n in nodes if n.active]
    return [_node_to_response(n) for n in nodes]


@app.get("/nodes/{node_id}", response_model=NodeResponse, tags=["Nodes"])
def get_node(node_id: str):
    """Gibt einen einzelnen Node anhand seiner ID zurück."""
    db = get_db()
    node = db.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' nicht gefunden")
    return _node_to_response(node)


@app.get("/nodes/{node_id}/children", response_model=List[NodeResponse], tags=["Nodes"])
def get_children(node_id: str):
    """Gibt alle direkten Kindknoten eines Nodes zurück."""
    db = get_db()
    parent = db.get_node(node_id)
    if parent is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' nicht gefunden")
    return [_node_to_response(n) for n in db.get_children(node_id)]


@app.get("/nodes/root/list", response_model=List[NodeResponse], tags=["Nodes"])
def get_root_nodes():
    """Gibt alle Root-Nodes zurück (parentId = None)."""
    db = get_db()
    return [_node_to_response(n) for n in db.get_root_nodes()]


@app.post("/nodes", response_model=NodeResponse, status_code=201, tags=["Nodes"])
def create_node(body: NodeCreate):
    """
    Erstellt einen neuen Entscheidungsknoten im Baum.

    **AI-Agents**: Ruft diesen Endpunkt auf, wenn eine neue Entscheidungsoption
    oder ein neuer Planungsbereich identifiziert wird.
    """
    db = get_db()

    # Parent prüfen
    if body.parentId:
        if db.get_node(body.parentId) is None:
            raise HTTPException(status_code=404, detail=f"Parent-Node '{body.parentId}' nicht gefunden")

    ts = now_ms()
    node = Node(
        id=body.id or str(uuid.uuid4()),
        parentId=body.parentId,
        active=body.active,
        name=body.name,
        reasoning=body.reasoning,
        summary=body.summary,
        issuer=body.issuer,
        status=body.status,
        synonyms=body.synonyms,
        taskRef=body.taskRef,
        taskMarkdown=body.taskMarkdown,
        creationDate=ts,
        lastChange=ts,
    )

    created = db.create_node(node)

    # Auto-Action
    action = Action(
        id=str(uuid.uuid4()),
        date=ts,
        knotenId=created.id,
        issuer=body.issuer,
        reason=body.reasoning,
        actionDescription=f"Node '{body.name}' erstellt",
        change="{}",
    )
    db.create_action(action)

    return _node_to_response(created)


@app.patch("/nodes/{node_id}", response_model=NodeResponse, tags=["Nodes"])
def update_node(node_id: str, body: NodeUpdate):
    """
    Aktualisiert Felder eines bestehenden Nodes.
    Das Feld `reason` ist Pflicht und wird im Audit-Log gespeichert.
    confidence und reifegrad werden automatisch neu berechnet.
    """
    db = get_db()
    if db.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' nicht gefunden")

    updates = body.model_dump(exclude_none=True, exclude={"reason"})
    issuer = updates.pop("issuer", "unknown")

    updated = db.update_node(node_id, updates, issuer=issuer, reason=body.reason)
    if updated is None:
        raise HTTPException(status_code=500, detail="Update fehlgeschlagen")
    return _node_to_response(updated)


@app.post("/nodes/{node_id}/reject", response_model=NodeResponse, tags=["Nodes"])
def reject_node(node_id: str, body: NodeReject):
    """
    Lehnt einen Knoten ab. Setzt active=False, status='rejected', rejectionDate.
    **AI-Agents**: Aufrufen wenn eine Option/Entscheidung verworfen wird.
    """
    db = get_db()
    if db.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' nicht gefunden")
    result = db.reject_node(node_id, issuer=body.issuer, reason=body.reason)
    return _node_to_response(result)


@app.post("/nodes/{node_id}/accept", response_model=NodeResponse, tags=["Nodes"])
def accept_node(node_id: str, body: NodeAccept):
    """
    Akzeptiert einen Knoten. Setzt status='accepted', acceptionDate.
    **AI-Agents**: Aufrufen wenn eine Entscheidung final getroffen wird.
    """
    db = get_db()
    if db.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' nicht gefunden")
    result = db.accept_node(node_id, issuer=body.issuer, reason=body.reason)
    return _node_to_response(result)


# ---------------------------------------------------------------------------
# Baum-Endpunkte
# ---------------------------------------------------------------------------

@app.get("/tree", tags=["Tree"])
def get_tree_flat():
    """
    Gibt alle Nodes als flache Liste zurück.
    Baumstruktur ergibt sich aus parentId-Referenzen.
    Optimiert für die D3.js-Visualisierung.
    """
    db = get_db()
    return db.get_tree()


@app.get("/tree/nested", tags=["Tree"])
def get_tree_nested():
    """
    Gibt den vollständigen Baum als verschachteltes JSON zurück.
    Root-Nodes enthalten ihre Children als 'children'-Array.
    """
    db = get_db()
    return db.get_tree_nested()


@app.get("/tree/stats", response_model=TreeStatsResponse, tags=["Tree"])
def get_tree_stats():
    """
    Gibt Statistiken über den aktuellen Planungsbaum zurück.
    Zeigt den Gesamtfortschritt (reifegrad des Root-Knotens).
    """
    db = get_db()
    nodes = db.get_all_nodes()
    roots = db.get_root_nodes()

    root_reifegrad = roots[0].reifegrad if roots else 0.0
    root_confidence = roots[0].confidence if roots else 0.0

    return TreeStatsResponse(
        total_nodes=len(nodes),
        active_nodes=sum(1 for n in nodes if n.active),
        rejected_nodes=sum(1 for n in nodes if n.status == "rejected"),
        accepted_nodes=sum(1 for n in nodes if n.status == "accepted"),
        open_nodes=sum(1 for n in nodes if n.status == "open"),
        in_progress_nodes=sum(1 for n in nodes if n.status == "in_progress"),
        root_reifegrad=root_reifegrad,
        root_confidence=root_confidence,
        completion_percentage=round(root_reifegrad * 100, 1),
    )


# ---------------------------------------------------------------------------
# Action-Endpunkte
# ---------------------------------------------------------------------------

@app.get("/actions", response_model=List[ActionResponse], tags=["Actions"])
def get_actions(knoten_id: Optional[str] = Query(None, description="Filter nach Node-ID")):
    """Gibt alle Actions zurück, optional gefiltert nach knotenId."""
    db = get_db()
    return [_action_to_response(a) for a in db.get_actions(knoten_id)]


@app.get("/actions/{action_id}", response_model=ActionResponse, tags=["Actions"])
def get_action(action_id: str):
    """Gibt eine einzelne Action anhand ihrer ID zurück."""
    db = get_db()
    action = db.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' nicht gefunden")
    return _action_to_response(action)


@app.post("/actions", response_model=ActionResponse, status_code=201, tags=["Actions"])
def create_action(body: ActionCreate):
    """
    Erstellt manuell einen Audit-Log-Eintrag.
    **AI-Agents**: Für Aktionen, die nicht über die Standard-Endpunkte abgedeckt sind.
    """
    db = get_db()
    if db.get_node(body.knotenId) is None:
        raise HTTPException(status_code=404, detail=f"Node '{body.knotenId}' nicht gefunden")

    ts = now_ms()
    action = Action(
        id=str(uuid.uuid4()),
        date=ts,
        knotenId=body.knotenId,
        issuer=body.issuer,
        reason=body.reason,
        actionDescription=body.actionDescription,
        change=body.change,
    )
    db.create_action(action)
    return _action_to_response(action)

