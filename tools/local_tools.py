"""
Spider Framework – Direkt-DB-Tool-Wrapper für AI-Agents (in-process, ohne HTTP).

`LocalSpiderTools` bietet exakt dieselbe Methodenfläche wie der HTTP-`SpiderTools`,
ruft aber die Geschäftslogik aus `spider.server.api` **direkt im Prozess** auf
(diese Funktionen nutzen nur `get_db()`, keinen Request-Kontext). Dadurch:

  - kein laufender API-Server nötig (schnell, tokenarm, keine "Server nicht erreichbar"-Fehler),
  - keine Code-Duplizierung: die Orchestrierung (Auto-Action, Stats, accept/reject) bleibt
    einzige Quelle in `server/api.py`.

Welche Datenbank verwendet wird, steuert die Umgebungsvariable `SPIDER_DB_PATH`
(siehe `spider.db.database.get_db`). Der von `spider-init` erzeugte Shim setzt sie
auf die Projekt-DB `<projekt>/.spider/spider.db`, bevor diese Klasse importiert wird.

Für den Netzwerk-/Remote-Fall existiert weiterhin `SpiderTools` (HTTP) – der von
`spider-init` erzeugte Shim wählt anhand von `SPIDER_BASE_URL` automatisch zwischen beiden.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import HTTPException

from spider.server import api
from spider.server.schemas import NodeCreate, NodeUpdate, NodeReject, NodeAccept, ActionCreate
from spider.tools.agent_tools import SpiderAPIError


def _dump(obj):
    """Pydantic-Model(e) → plain dict/list (Parität zur JSON-Antwort der HTTP-Variante)."""
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def _wrap(fn, *args, **kwargs):
    """Ruft einen api-Handler auf und übersetzt HTTPException → SpiderAPIError (Verhaltensparität)."""
    try:
        return _dump(fn(*args, **kwargs))
    except HTTPException as e:
        raise SpiderAPIError(f"HTTP {e.status_code}: {e.detail}") from e


class LocalSpiderTools:
    """
    In-Process-Tool-Wrapper für das Spider-Framework (Direkt-DB-Zugriff).
    Drop-in-kompatibel zu `spider.tools.agent_tools.SpiderTools`.
    """

    # -----------------------------------------------------------------------
    # Node-Tools
    # -----------------------------------------------------------------------

    def create_node(
        self,
        name: str,
        reasoning: str,
        summary: str,
        issuer: str,
        parent_id: Optional[str] = None,
        status: str = "open",
        synonyms: str = "",
    ) -> dict:
        """Erstellt einen neuen Entscheidungsknoten (inkl. automatischem Audit-Log-Eintrag)."""
        return _wrap(api.create_node, NodeCreate(
            name=name,
            reasoning=reasoning,
            summary=summary,
            issuer=issuer,
            parentId=parent_id,
            status=status,
            synonyms=synonyms,
        ))

    def get_node(self, node_id: str) -> dict:
        """Gibt einen einzelnen Knoten anhand seiner ID zurück."""
        return _wrap(api.get_node, node_id)

    def get_all_nodes(self, active_only: bool = False) -> list:
        """Gibt alle Knoten als flache Liste zurück."""
        return _wrap(api.get_all_nodes, active_only=active_only)

    def get_children(self, node_id: str) -> list:
        """Gibt alle direkten Kindknoten eines Knotens zurück."""
        return _wrap(api.get_children, node_id)

    def update_node(
        self,
        node_id: str,
        issuer: str,
        reason: str,
        name: Optional[str] = None,
        reasoning: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
        synonyms: Optional[str] = None,
    ) -> dict:
        """Aktualisiert Felder eines bestehenden Knotens (confidence/reifegrad werden nicht gesetzt)."""
        body = NodeUpdate(
            reason=reason,
            issuer=issuer,
            name=name,
            reasoning=reasoning,
            summary=summary,
            status=status,
            synonyms=synonyms,
        )
        return _wrap(api.update_node, node_id, body)

    def reject_node(self, node_id: str, issuer: str, reason: str) -> dict:
        """Lehnt einen Entscheidungsknoten ab (active=False, status='rejected')."""
        return _wrap(api.reject_node, node_id, NodeReject(issuer=issuer, reason=reason))

    def accept_node(self, node_id: str, issuer: str, reason: str) -> dict:
        """Akzeptiert einen Entscheidungsknoten als finale Entscheidung (status='accepted')."""
        return _wrap(api.accept_node, node_id, NodeAccept(issuer=issuer, reason=reason))

    # -----------------------------------------------------------------------
    # Baum-Tools
    # -----------------------------------------------------------------------

    def get_tree(self) -> list:
        """Gibt den kompletten Planungsbaum als flache Liste zurück."""
        return _wrap(api.get_tree_flat)

    def get_tree_nested(self) -> list:
        """Gibt den Baum als verschachteltes JSON zurück (Root → Children → ...)."""
        return _wrap(api.get_tree_nested)

    def get_tree_stats(self) -> dict:
        """Gibt Statistiken über den aktuellen Planungsbaum zurück (Fortschritt via root_reifegrad)."""
        return _wrap(api.get_tree_stats)

    # -----------------------------------------------------------------------
    # Action-Tools
    # -----------------------------------------------------------------------

    def add_action(
        self,
        knoten_id: str,
        issuer: str,
        reason: str,
        action_description: str,
        change: Optional[dict] = None,
    ) -> dict:
        """Fügt einen manuellen Audit-Log-Eintrag hinzu."""
        return _wrap(api.create_action, ActionCreate(
            knotenId=knoten_id,
            issuer=issuer,
            reason=reason,
            actionDescription=action_description,
            change=json.dumps(change or {}),
        ))

    def get_actions(self, knoten_id: Optional[str] = None) -> list:
        """Gibt alle Actions zurück, optional gefiltert nach Node."""
        return _wrap(api.get_actions, knoten_id=knoten_id)

    # -----------------------------------------------------------------------
    # Komfort-Methoden (Parität zu SpiderTools)
    # -----------------------------------------------------------------------

    def is_server_running(self) -> bool:
        """Direkt-DB-Zugriff ist immer verfügbar (kein Server nötig)."""
        return True

    def get_planning_progress(self) -> str:
        """Lesbarer Fortschrittsbericht (für Agent-Logs und Statusmeldungen)."""
        stats = self.get_tree_stats()
        return (
            f"Spider Planungsfortschritt: {stats['completion_percentage']}% | "
            f"Knoten: {stats['total_nodes']} gesamt, "
            f"{stats['accepted_nodes']} akzeptiert, "
            f"{stats['rejected_nodes']} abgelehnt, "
            f"{stats['open_nodes']} offen | "
            f"Root-Reifegrad: {stats['root_reifegrad']:.3f}"
        )


class ReadOnlyViolation(NotImplementedError):
    """Wird geworfen, wenn ein read-only Tool eine schreibende Operation versucht."""


class ReadOnlySpiderTools:
    """
    Read-only Sicht auf die Spider-Tools für **Subagents**.

    Lese-Methoden werden an ein beliebiges Tools-Objekt delegiert
    (`LocalSpiderTools` oder HTTP-`SpiderTools`); **alle schreibenden Methoden
    werfen `ReadOnlyViolation`**. So kann ein Subagent den Entscheidungsbaum für
    Kontext lesen, ihn aber technisch nicht verändern – nur der Orchestrator schreibt.

    Verwendung:
        ro = ReadOnlySpiderTools()                 # Direkt-DB, read-only
        ro = ReadOnlySpiderTools(existing_tools)    # bestehendes Tools-Objekt absichern
    """

    #: Methoden, die in read-only-Modus gesperrt sind.
    WRITE_METHODS = ("create_node", "update_node", "reject_node", "accept_node", "add_action")

    def __init__(self, inner: Optional[object] = None):
        self._inner = inner if inner is not None else LocalSpiderTools()

    # --- erlaubte Lese-Operationen (Delegation) ---------------------------
    def get_node(self, node_id: str) -> dict:
        return self._inner.get_node(node_id)

    def get_all_nodes(self, active_only: bool = False) -> list:
        return self._inner.get_all_nodes(active_only)

    def get_children(self, node_id: str) -> list:
        return self._inner.get_children(node_id)

    def get_tree(self) -> list:
        return self._inner.get_tree()

    def get_tree_nested(self) -> list:
        return self._inner.get_tree_nested()

    def get_tree_stats(self) -> dict:
        return self._inner.get_tree_stats()

    def get_actions(self, knoten_id: Optional[str] = None) -> list:
        return self._inner.get_actions(knoten_id)

    def is_server_running(self) -> bool:
        return self._inner.is_server_running()

    def get_planning_progress(self) -> str:
        return self._inner.get_planning_progress()

    # --- gesperrte Schreib-Operationen ------------------------------------
    def _blocked(self, name: str):
        raise ReadOnlyViolation(
            f"'{name}' ist im read-only-Modus gesperrt. Subagents dürfen Spider nicht "
            f"verändern – melde das gewünschte Ergebnis an den Orchestrator zurück, "
            f"der die Datenbank aktualisiert."
        )

    def create_node(self, *args, **kwargs):
        self._blocked("create_node")

    def update_node(self, *args, **kwargs):
        self._blocked("update_node")

    def reject_node(self, *args, **kwargs):
        self._blocked("reject_node")

    def accept_node(self, *args, **kwargs):
        self._blocked("accept_node")

    def add_action(self, *args, **kwargs):
        self._blocked("add_action")
