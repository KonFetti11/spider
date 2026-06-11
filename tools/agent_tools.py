"""
Spider Framework – Tool-Wrapper für AI-Agents.

Diese Funktionen sind als Tools für Claude / OpenAI Function-Calling konzipiert.
Jede Funktion kommuniziert mit dem lokalen Spider-HTTP-Server (default: localhost:8765).

Verwendung in einem Agent-System:
    from spider.tools.agent_tools import SpiderTools
    tools = SpiderTools(base_url="http://localhost:8765")

    # Neuen Knoten erstellen:
    node = tools.create_node(
        name="Datenbankauswahl",
        reasoning="Wir müssen entscheiden, welche Datenbank wir verwenden",
        summary="Evaluierung von SQLite vs PostgreSQL",
        issuer="agent-001",
        parent_id="root-001"
    )
"""

from __future__ import annotations

import json
from typing import Optional
import urllib.request
import urllib.error
import urllib.parse

DEFAULT_BASE_URL = "http://127.0.0.1:8765"


class SpiderAPIError(Exception):
    """Fehler bei der Kommunikation mit dem Spider-Server."""
    pass


class SpiderTools:
    """
    Tool-Wrapper für AI-Agents zum Zugriff auf das Spider-Framework.
    Nutzt nur die Python-Standardbibliothek (keine externen Abhängigkeiten).
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # -----------------------------------------------------------------------
    # HTTP-Hilfsmethoden
    # -----------------------------------------------------------------------

    def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                detail = json.loads(error_body).get("detail", error_body)
            except Exception:
                detail = error_body
            raise SpiderAPIError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise SpiderAPIError(
                f"Spider-Server nicht erreichbar unter {self.base_url}. "
                f"Starte den Server mit: python -m spider.server.main"
            ) from e

    def _get(self, path: str) -> dict:
        return self._request("GET", path)

    def _post(self, path: str, data: dict) -> dict:
        return self._request("POST", path, data)

    def _patch(self, path: str, data: dict) -> dict:
        return self._request("PATCH", path, data)

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
        """
        Erstellt einen neuen Entscheidungsknoten im Planungsbaum.

        Args:
            name:      Anzeigename des Knotens (kurz und präzise)
            reasoning: Warum wird dieser Knoten erstellt? Welche Entscheidung steht an?
            summary:   Kurze Zusammenfassung des Knoteninhalt
            issuer:    Identifikation des Erstellers (Agent-Name oder User-ID)
            parent_id: ID des übergeordneten Knotens (None = Root-Knoten)
            status:    Initialer Status: 'open' | 'in_progress'
            synonyms:  Kommagetrennte alternative Bezeichnungen

        Returns:
            dict: Der erstellte Node als Dictionary

        Wann verwenden:
            - Bei jeder neuen Entscheidungsoption oder Alternative
            - Beim Aufteilen eines Problems in Teilprobleme
            - Beim Identifizieren eines neuen Planungsbereichs
        """
        payload = {
            "name": name,
            "reasoning": reasoning,
            "summary": summary,
            "issuer": issuer,
            "status": status,
            "synonyms": synonyms,
        }
        if parent_id:
            payload["parentId"] = parent_id
        return self._post("/nodes", payload)

    def get_node(self, node_id: str) -> dict:
        """
        Gibt einen einzelnen Knoten anhand seiner ID zurück.

        Args:
            node_id: ID des Knotens

        Returns:
            dict: Node-Daten inkl. confidence und reifegrad
        """
        return self._get(f"/nodes/{node_id}")

    def get_all_nodes(self, active_only: bool = False) -> list:
        """
        Gibt alle Knoten als flache Liste zurück.

        Args:
            active_only: Wenn True, nur aktive (nicht abgelehnte) Knoten

        Returns:
            list: Liste aller Node-Dictionaries
        """
        path = "/nodes?active_only=true" if active_only else "/nodes"
        return self._get(path)

    def get_children(self, node_id: str) -> list:
        """
        Gibt alle direkten Kindknoten eines Knotens zurück.

        Args:
            node_id: ID des Elternknotens

        Returns:
            list: Liste der direkten Kindknoten
        """
        return self._get(f"/nodes/{node_id}/children")

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
        """
        Aktualisiert Felder eines bestehenden Knotens.

        Args:
            node_id:   ID des zu aktualisierenden Knotens
            issuer:    Wer nimmt die Änderung vor?
            reason:    Warum wird die Änderung vorgenommen? (Pflichtfeld)
            name:      Neuer Anzeigename (optional)
            reasoning: Neue Begründung (optional)
            summary:   Neue Zusammenfassung (optional)
            status:    Neuer Status (optional)
            synonyms:  Neue Synonyme (optional)

        Returns:
            dict: Aktualisierter Node
        """
        payload = {"issuer": issuer, "reason": reason}
        if name is not None:
            payload["name"] = name
        if reasoning is not None:
            payload["reasoning"] = reasoning
        if summary is not None:
            payload["summary"] = summary
        if status is not None:
            payload["status"] = status
        if synonyms is not None:
            payload["synonyms"] = synonyms
        return self._patch(f"/nodes/{node_id}", payload)

    def reject_node(self, node_id: str, issuer: str, reason: str) -> dict:
        """
        Lehnt einen Entscheidungsknoten ab.
        Setzt active=False, status='rejected', rejectionDate (automatisch).
        Der Knoten bleibt im Baum sichtbar (historische Nachvollziehbarkeit).

        Args:
            node_id: ID des abzulehnenden Knotens
            issuer:  Wer lehnt ab?
            reason:  Warum wird abgelehnt? (ausführliche Begründung empfohlen)

        Returns:
            dict: Aktualisierter Node

        Wann verwenden:
            - Wenn eine Alternative/Option als ungeeignet bewertet wurde
            - Wenn eine Entscheidung zugunsten einer anderen Option fällt
            - WICHTIG: Immer die spezifische Begründung angeben
        """
        return self._post(f"/nodes/{node_id}/reject", {"issuer": issuer, "reason": reason})

    def accept_node(self, node_id: str, issuer: str, reason: str) -> dict:
        """
        Akzeptiert einen Entscheidungsknoten als finale Entscheidung.
        Setzt status='accepted', acceptionDate (automatisch).

        Args:
            node_id: ID des zu akzeptierenden Knotens
            issuer:  Wer akzeptiert?
            reason:  Begründung der Entscheidung

        Returns:
            dict: Aktualisierter Node

        Wann verwenden:
            - Wenn eine finale Entscheidung für diesen Bereich getroffen wurde
            - Wenn alle Alternativen bewertet wurden und diese die beste ist
            - WICHTIG: Zuerst alle Alternativen mit reject_node ablehnen
        """
        return self._post(f"/nodes/{node_id}/accept", {"issuer": issuer, "reason": reason})

    # -----------------------------------------------------------------------
    # Baum-Tools
    # -----------------------------------------------------------------------

    def get_tree(self) -> list:
        """
        Gibt den kompletten Planungsbaum als flache Liste zurück.
        Baumstruktur ergibt sich aus parentId-Referenzen.

        Returns:
            list: Alle Nodes, optimal für Traversierung und Analyse

        Wann verwenden:
            - Zu Beginn einer Session (Überblick über den aktuellen Stand)
            - Vor dem Erstellen neuer Knoten (Duplikate vermeiden)
        """
        return self._get("/tree")

    def get_tree_nested(self) -> list:
        """
        Gibt den Baum als verschachteltes JSON zurück (Root → Children → ...).

        Returns:
            list: Verschachtelte Baumstruktur
        """
        return self._get("/tree/nested")

    def get_tree_stats(self) -> dict:
        """
        Gibt Statistiken über den aktuellen Planungsbaum zurück.
        Zeigt den Gesamtfortschritt über den reifegrad des Root-Knotens.

        Returns:
            dict mit: total_nodes, active_nodes, rejected_nodes, accepted_nodes,
                      root_reifegrad, completion_percentage

        Wann verwenden:
            - Am Anfang jeder Session (Fortschrittsbericht)
            - Um zu prüfen ob der Planungsprozess abgeschlossen ist (reifegrad == 1.0)
        """
        return self._get("/tree/stats")

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
        """
        Fügt einen manuellen Audit-Log-Eintrag hinzu.
        Für Aktionen, die nicht über Standard-Endpunkte abgedeckt sind.

        Args:
            knoten_id:          ID des betroffenen Knotens
            issuer:             Wer führt die Aktion aus?
            reason:             Warum?
            action_description: Was wurde getan?
            change:             Dict mit {field: {old: ..., new: ...}} (optional)

        Returns:
            dict: Erstellte Action
        """
        return self._post("/actions", {
            "knotenId": knoten_id,
            "issuer": issuer,
            "reason": reason,
            "actionDescription": action_description,
            "change": json.dumps(change or {}),
        })

    def get_actions(self, knoten_id: Optional[str] = None) -> list:
        """
        Gibt alle Actions zurück, optional gefiltert nach Node.

        Args:
            knoten_id: Filter nach Node-ID (optional)

        Returns:
            list: Liste der Action-Dictionaries (chronologisch)
        """
        path = f"/actions?knoten_id={knoten_id}" if knoten_id else "/actions"
        return self._get(path)

    # -----------------------------------------------------------------------
    # Komfort-Methoden
    # -----------------------------------------------------------------------

    def is_server_running(self) -> bool:
        """Prüft ob der Spider-Server erreichbar ist."""
        try:
            self._get("/health")
            return True
        except SpiderAPIError:
            return False

    def get_planning_progress(self) -> str:
        """
        Gibt einen lesbaren Fortschrittsbericht zurück.
        Nützlich für Agent-Logs und Statusmeldungen.
        """
        try:
            stats = self.get_tree_stats()
            return (
                f"Spider Planungsfortschritt: {stats['completion_percentage']}% | "
                f"Knoten: {stats['total_nodes']} gesamt, "
                f"{stats['accepted_nodes']} akzeptiert, "
                f"{stats['rejected_nodes']} abgelehnt, "
                f"{stats['open_nodes']} offen | "
                f"Root-Reifegrad: {stats['root_reifegrad']:.3f}"
            )
        except SpiderAPIError as e:
            return f"Spider-Server nicht verfügbar: {e}"

