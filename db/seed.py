"""
Spider Framework – Seed-Daten für POC-Demonstration.

Erstellt einen realistischen Planungsbaum für ein fiktives
AI-Agenten-Projekt mit 3 Ebenen, aktiven/inaktiven Knoten
und zugehörigen Action-Einträgen.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

# Projektwurzel im Suchpfad
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.database import Database, DEFAULT_DB_PATH
from db.models import Node, Action


def _id() -> str:
    return str(uuid.uuid4())


def _ts(offset_ms: int = 0) -> int:
    """Gibt einen Timestamp zurück, versetzt um offset_ms."""
    return 1_749_000_000_000 + offset_ms  # fester Basis-Timestamp für reproduzierbare Seeds


def seed(db: Database):
    print("Seeding Spider-Datenbank...")

    # -----------------------------------------------------------------------
    # Ebene 0 – Root
    # -----------------------------------------------------------------------
    root_id = "root-001"
    root = Node(
        id=root_id,
        parentId=None,
        active=True,
        name="KI-Planungsystem v1",
        reasoning="Zentraler Ausgangspunkt des gesamten Planungsbaums. Alle Entscheidungen gehen von hier aus.",
        summary="Root-Knoten des Spider-POC-Projekts",
        creationDate=_ts(0),
        issuer="system",
        status="in_progress",
        synonyms="root, hauptknoten",
        lastChange=_ts(100),
    )

    # -----------------------------------------------------------------------
    # Ebene 1 – Hauptbereiche
    # -----------------------------------------------------------------------
    arch_id = "arch-001"
    arch = Node(
        id=arch_id,
        parentId=root_id,
        active=True,
        name="Architektur & Technologie-Stack",
        reasoning="Fundamental für alle weiteren Entscheidungen. Muss zuerst geklärt werden.",
        summary="Entscheidungen zu Programmiersprache, Framework und Datenbank",
        creationDate=_ts(1_000),
        issuer="agent-planner",
        status="in_progress",
        synonyms="tech stack, architektur",
        lastChange=_ts(1_100),
    )

    ux_id = "ux-001"
    ux = Node(
        id=ux_id,
        parentId=root_id,
        active=True,
        name="UI/UX & Visualisierung",
        reasoning="Nutzer müssen den Entscheidungsbaum intuitiv bedienen können.",
        summary="Alle Entscheidungen zur Benutzeroberfläche und Visualisierung",
        creationDate=_ts(1_200),
        issuer="agent-planner",
        status="in_progress",
        synonyms="frontend, visualisierung",
        lastChange=_ts(1_300),
    )

    deploy_id = "deploy-001"
    deploy = Node(
        id=deploy_id,
        parentId=root_id,
        active=True,
        name="Deployment & Integration",
        reasoning="Das Framework muss in bestehende AI-Projekte integrierbar sein.",
        summary="Deployment-Strategie, Paketerstellung, Einbindung in Projekte",
        creationDate=_ts(1_400),
        issuer="agent-planner",
        status="open",
        synonyms="deployment, integration",
        lastChange=_ts(1_500),
    )

    # -----------------------------------------------------------------------
    # Ebene 2 – Architektur-Kindknoten
    # -----------------------------------------------------------------------
    py_id = "lang-python"
    py_node = Node(
        id=py_id,
        parentId=arch_id,
        active=True,
        name="Python als Hauptsprache",
        reasoning="Python ist der Standard für AI/ML-Tooling. Große Bibliotheksauswahl.",
        summary="Entscheidung: Python 3.11+",
        creationDate=_ts(2_000),
        issuer="agent-planner",
        status="accepted",
        acceptionDate=_ts(2_500),
        acceptionReason="Consensus: Python hat beste AI-Ökosystem-Abdeckung",
        confidence=0.9,
        synonyms="python, python3",
        lastChange=_ts(2_500),
    )

    java_id = "lang-java"
    java_node = Node(
        id=java_id,
        parentId=arch_id,
        active=False,
        name="Java als Hauptsprache",
        reasoning="Java wurde als Alternative evaluiert (Typsicherheit, Performance).",
        summary="Alternative: Java 21 – abgelehnt",
        creationDate=_ts(2_100),
        issuer="agent-planner",
        status="rejected",
        rejectionDate=_ts(2_400),
        rejectionReason="Zu wenig AI-native Bibliotheken; schlechtere Integration mit LLM-SDKs",
        confidence=0.2,
        synonyms="java",
        lastChange=_ts(2_400),
    )

    fastapi_id = "fw-fastapi"
    fastapi_node = Node(
        id=fastapi_id,
        parentId=arch_id,
        active=True,
        name="FastAPI als HTTP-Server",
        reasoning="FastAPI bietet automatische OpenAPI-Dokumentation und asynchrone Performance.",
        summary="Entscheidung: FastAPI + Uvicorn",
        creationDate=_ts(2_200),
        issuer="agent-planner",
        status="accepted",
        acceptionDate=_ts(2_600),
        acceptionReason="FastAPI erfüllt alle Anforderungen: Pydantic-Validierung, async, OpenAPI",
        confidence=0.85,
        synonyms="fastapi, uvicorn",
        lastChange=_ts(2_600),
    )

    sqlite_id = "db-sqlite"
    sqlite_node = Node(
        id=sqlite_id,
        parentId=arch_id,
        active=True,
        name="SQLite als lokale Datenbank",
        reasoning="POC benötigt keine externe DB. SQLite ist zero-config und einbettbar.",
        summary="Entscheidung: SQLite3 (built-in Python)",
        creationDate=_ts(2_300),
        issuer="agent-planner",
        status="accepted",
        acceptionDate=_ts(2_700),
        acceptionReason="SQLite ausreichend für POC; kein externer Datenbankserver benötigt",
        confidence=0.95,
        synonyms="sqlite, sqlite3",
        lastChange=_ts(2_700),
    )

    # -----------------------------------------------------------------------
    # Ebene 2 – UX-Kindknoten
    # -----------------------------------------------------------------------
    d3_id = "viz-d3"
    d3_node = Node(
        id=d3_id,
        parentId=ux_id,
        active=True,
        name="D3.js für interaktiven Baum",
        reasoning="D3.js bietet maximale Flexibilität für Baumvisualisierungen ohne Python-Abhängigkeit.",
        summary="Entscheidung: D3.js v7 via CDN",
        creationDate=_ts(3_000),
        issuer="agent-planner",
        status="accepted",
        acceptionDate=_ts(3_500),
        acceptionReason="D3.js best-in-class für interaktive Graphen; keine zusätzliche Abhängigkeit",
        confidence=0.88,
        synonyms="d3, d3.js, visualisierung",
        lastChange=_ts(3_500),
    )

    pyvis_id = "viz-pyvis"
    pyvis_node = Node(
        id=pyvis_id,
        parentId=ux_id,
        active=False,
        name="Pyvis für Baumvisualisierung",
        reasoning="Pyvis wurde als Python-native Alternative evaluiert.",
        summary="Alternative: Pyvis – abgelehnt",
        creationDate=_ts(3_100),
        issuer="agent-planner",
        status="rejected",
        rejectionDate=_ts(3_400),
        rejectionReason="Pyvis weniger flexibel für Custom-Interaktion; begrenzte Styling-Optionen",
        confidence=0.3,
        synonyms="pyvis",
        lastChange=_ts(3_400),
    )

    hover_id = "ux-hover"
    hover_node = Node(
        id=hover_id,
        parentId=ux_id,
        active=True,
        name="Hover-Tooltips mit Node-Details",
        reasoning="Nutzer müssen alle relevanten Felder eines Knotens schnell einsehen können.",
        summary="Hover zeigt: name, summary, status, confidence, reifegrad, issuer",
        creationDate=_ts(3_200),
        issuer="agent-planner",
        status="in_progress",
        confidence=0.0,
        synonyms="tooltip, hover",
        lastChange=_ts(3_200),
    )

    # -----------------------------------------------------------------------
    # Ebene 2 – Deployment-Kindknoten
    # -----------------------------------------------------------------------
    pkg_id = "deploy-pkg"
    pkg_node = Node(
        id=pkg_id,
        parentId=deploy_id,
        active=True,
        name="Python-Package (pip-installierbar)",
        reasoning="Einfache Einbindung in bestehende Python-Projekte via pip.",
        summary="spider als pip-installierbares Package",
        creationDate=_ts(4_000),
        issuer="agent-planner",
        status="open",
        confidence=0.0,
        synonyms="pip, package",
        lastChange=_ts(4_000),
    )

    docker_id = "deploy-docker"
    docker_node = Node(
        id=docker_id,
        parentId=deploy_id,
        active=True,
        name="Docker-Container für Server",
        reasoning="Optionaler Docker-Support für isolierten Betrieb des Spider-Servers.",
        summary="Dockerfile für den FastAPI-Spider-Server",
        creationDate=_ts(4_100),
        issuer="agent-planner",
        status="open",
        confidence=0.0,
        synonyms="docker, container",
        lastChange=_ts(4_100),
    )

    agents_md_id = "deploy-agentsmd"
    agents_md_node = Node(
        id=agents_md_id,
        parentId=deploy_id,
        active=True,
        name="AGENTS.md Template für Zielprojekte",
        reasoning="Coding Agents benötigen eine klare Anleitung, wie sie das Spider-Framework nutzen.",
        summary="Wiederverwendbare AGENTS.md-Vorlage",
        creationDate=_ts(4_200),
        issuer="agent-planner",
        status="accepted",
        acceptionDate=_ts(4_500),
        acceptionReason="Template ist fertig und getestet",
        confidence=0.9,
        synonyms="agents.md, claude.md, prompt",
        lastChange=_ts(4_500),
    )

    # -----------------------------------------------------------------------
    # Alle Nodes in DB einfügen (Reihenfolge: erst Eltern, dann Kinder)
    # -----------------------------------------------------------------------
    all_nodes = [
        root, arch, ux, deploy,
        py_node, java_node, fastapi_node, sqlite_node,
        d3_node, pyvis_node, hover_node,
        pkg_node, docker_node, agents_md_node,
    ]
    for node in all_nodes:
        db.create_node(node)
        print(f"  ✓ Node erstellt: {node.name} [{node.id}]")

    # -----------------------------------------------------------------------
    # Actions (Audit-Log)
    # -----------------------------------------------------------------------
    actions = [
        Action(
            id=_id(), date=_ts(2_400), knotenId=java_id, issuer="agent-planner",
            reason="Java bietet keine ausreichende AI-Bibliotheksunterstützung",
            actionDescription="Node abgelehnt",
            change=json.dumps({"status": {"old": "open", "new": "rejected"},
                               "active": {"old": True, "new": False}}),
        ),
        Action(
            id=_id(), date=_ts(2_500), knotenId=py_id, issuer="agent-planner",
            reason="Python ist der AI-Standard",
            actionDescription="Node akzeptiert",
            change=json.dumps({"status": {"old": "open", "new": "accepted"},
                               "acceptionDate": {"old": None, "new": _ts(2_500)}}),
        ),
        Action(
            id=_id(), date=_ts(2_600), knotenId=fastapi_id, issuer="agent-planner",
            reason="FastAPI erfüllt alle Anforderungen",
            actionDescription="Node akzeptiert",
            change=json.dumps({"status": {"old": "open", "new": "accepted"}}),
        ),
        Action(
            id=_id(), date=_ts(2_700), knotenId=sqlite_id, issuer="agent-planner",
            reason="SQLite ausreichend für POC",
            actionDescription="Node akzeptiert",
            change=json.dumps({"status": {"old": "open", "new": "accepted"}}),
        ),
        Action(
            id=_id(), date=_ts(3_400), knotenId=pyvis_id, issuer="agent-planner",
            reason="Pyvis hat zu wenig Flexibilität",
            actionDescription="Node abgelehnt",
            change=json.dumps({"status": {"old": "open", "new": "rejected"},
                               "active": {"old": True, "new": False}}),
        ),
        Action(
            id=_id(), date=_ts(3_500), knotenId=d3_id, issuer="agent-planner",
            reason="D3.js ist die beste Wahl für interaktive Graphen",
            actionDescription="Node akzeptiert",
            change=json.dumps({"status": {"old": "open", "new": "accepted"}}),
        ),
        Action(
            id=_id(), date=_ts(4_500), knotenId=agents_md_id, issuer="agent-planner",
            reason="AGENTS.md Template fertig entwickelt",
            actionDescription="Node akzeptiert",
            change=json.dumps({"status": {"old": "open", "new": "accepted"}}),
        ),
        Action(
            id=_id(), date=_ts(1_100), knotenId=root_id, issuer="system",
            reason="Projektstart",
            actionDescription="Root-Node initialisiert",
            change=json.dumps({"status": {"old": None, "new": "in_progress"}}),
        ),
    ]

    for action in actions:
        db.create_action(action)
        print(f"  ✓ Action erstellt: {action.actionDescription} [{action.knotenId}]")

    # -----------------------------------------------------------------------
    # Abschlussbericht
    # -----------------------------------------------------------------------
    root_node = db.get_node(root_id)
    print(f"\n{'='*60}")
    print(f"Seed abgeschlossen!")
    print(f"  Nodes gesamt:   {len(all_nodes)}")
    print(f"  Actions gesamt: {len(actions)}")
    print(f"  Root reifegrad: {root_node.reifegrad:.2f}")
    print(f"  Root confidence:{root_node.confidence:.2f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import os

    # Projekt-.env laden, damit der Seed in die Projekt-DB schreibt (SPIDER_DB_PATH).
    from spider.config import load_project_env
    load_project_env()

    db_path = os.environ.get("SPIDER_DB_PATH", str(DEFAULT_DB_PATH))
    print(f"Datenbank: {db_path}")

    # Bestehende DB löschen für sauberen Seed
    from pathlib import Path
    p = Path(db_path)
    if p.exists():
        p.unlink()
        print("Bestehende Datenbank gelöscht.")

    db = Database(Path(db_path))
    seed(db)

