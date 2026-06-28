"""
Spider Framework – MCP-Server (stdio) für Claude Code & andere MCP-Clients.

Stellt die Spider-Tools als **native MCP-Tools** bereit (statt Terminal-Aufrufe des
Shims). Greift direkt auf die Projekt-DB zu (`LocalSpiderTools`, kein HTTP-Server nötig).
Die Datenbank wird über die Projekt-.env bestimmt (`.spider/.env`, via `spider.config`).

Start (i.d.R. durch den MCP-Client via .mcp.json):
    python -m spider.mcp_server

Voraussetzung: das MCP-SDK (`pip install -e ".[mcp]"`  bzw.  `pip install mcp`).
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from spider.config import load_project_env
from spider.tools.local_tools import LocalSpiderTools

# Projekt-.env laden, damit SPIDER_DB_PATH auf die Projekt-DB zeigt.
load_project_env()

mcp = FastMCP("spider")
_tools = LocalSpiderTools()


# ---------------------------------------------------------------------------
# Node-Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def spider_create_node(
    name: str,
    reasoning: str,
    summary: str,
    issuer: str,
    parent_id: Optional[str] = None,
    status: str = "open",
    synonyms: str = "",
) -> dict:
    """Erstellt einen neuen Entscheidungsknoten im Planungsbaum (mit Auto-Audit-Eintrag).
    parent_id=None => Root-Knoten. Für jede Entscheidung/Alternative aufrufen."""
    return _tools.create_node(
        name=name, reasoning=reasoning, summary=summary, issuer=issuer,
        parent_id=parent_id, status=status, synonyms=synonyms,
    )


@mcp.tool()
def spider_get_node(node_id: str) -> dict:
    """Gibt einen einzelnen Knoten anhand seiner ID zurück (inkl. confidence/reifegrad)."""
    return _tools.get_node(node_id)


@mcp.tool()
def spider_get_children(node_id: str) -> list:
    """Gibt alle direkten Kindknoten eines Knotens zurück."""
    return _tools.get_children(node_id)


@mcp.tool()
def spider_update_node(
    node_id: str,
    issuer: str,
    reason: str,
    name: Optional[str] = None,
    reasoning: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
    synonyms: Optional[str] = None,
) -> dict:
    """Aktualisiert Felder eines Knotens. `reason` ist Pflicht (Audit-Log).
    confidence/reifegrad werden automatisch berechnet, nie direkt gesetzt."""
    return _tools.update_node(
        node_id, issuer=issuer, reason=reason, name=name, reasoning=reasoning,
        summary=summary, status=status, synonyms=synonyms,
    )


@mcp.tool()
def spider_reject_node(node_id: str, issuer: str, reason: str) -> dict:
    """Lehnt einen Knoten ab (active=False, status='rejected'). Begründung angeben."""
    return _tools.reject_node(node_id, issuer=issuer, reason=reason)


@mcp.tool()
def spider_accept_node(node_id: str, issuer: str, reason: str) -> dict:
    """Akzeptiert einen Knoten als finale Entscheidung (status='accepted')."""
    return _tools.accept_node(node_id, issuer=issuer, reason=reason)


# ---------------------------------------------------------------------------
# Baum-Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def spider_get_tree() -> list:
    """Gibt den kompletten Planungsbaum als flache Liste zurück (Struktur über parentId)."""
    return _tools.get_tree()


@mcp.tool()
def spider_get_tree_stats() -> dict:
    """Gibt Fortschrittsstatistiken zurück (total/accepted/rejected/open nodes,
    root_reifegrad, completion_percentage). Zu Session-Beginn aufrufen."""
    return _tools.get_tree_stats()


# ---------------------------------------------------------------------------
# Action-Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def spider_add_action(
    knoten_id: str,
    issuer: str,
    reason: str,
    action_description: str,
    change: Optional[dict] = None,
) -> dict:
    """Fügt einen manuellen Audit-Log-Eintrag zu einem Knoten hinzu."""
    return _tools.add_action(
        knoten_id=knoten_id, issuer=issuer, reason=reason,
        action_description=action_description, change=change,
    )


@mcp.tool()
def spider_get_actions(knoten_id: Optional[str] = None) -> list:
    """Gibt Audit-Log-Einträge zurück, optional gefiltert nach Knoten-ID."""
    return _tools.get_actions(knoten_id=knoten_id)


def main() -> None:
    load_project_env()
    mcp.run()  # stdio-Transport (Standard)


if __name__ == "__main__":
    main()
