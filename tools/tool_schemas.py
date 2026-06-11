"""
Spider Framework – JSON-Schemas der AI-Tools.

Diese Schemas können direkt in System-Prompts für Claude/OpenAI eingebettet werden.
Sie beschreiben exakt die Parameter jedes Tools und wann es verwendet werden soll.

Verwendung:
    from spider.tools.tool_schemas import SPIDER_TOOL_SCHEMAS
    # In OpenAI-API:
    response = client.chat.completions.create(tools=SPIDER_TOOL_SCHEMAS, ...)
    # In Anthropic-API:
    response = client.messages.create(tools=SPIDER_TOOL_SCHEMAS, ...)
"""

from __future__ import annotations
from typing import List

SPIDER_TOOL_SCHEMAS: List[dict] = [

    # ------------------------------------------------------------------
    # create_node
    # ------------------------------------------------------------------
    {
        "name": "spider_create_node",
        "description": (
            "Erstellt einen neuen Entscheidungsknoten im Spider-Planungsbaum. "
            "WANN VERWENDEN: Bei jeder neuen Entscheidungsoption, Alternative oder "
            "Teilproblem. Vor dem Erstellen prüfen ob ein ähnlicher Knoten bereits "
            "existiert (spider_get_tree). Alternatives und konkurrierende Optionen "
            "als Geschwisterknoten (gleicher parentId) anlegen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Kurzer, präziser Anzeigename (max. 60 Zeichen)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Warum wird dieser Knoten erstellt? Welche Entscheidungsfrage steht dahinter? (ausführlich)"
                },
                "summary": {
                    "type": "string",
                    "description": "Kurze Zusammenfassung der Entscheidungsoption (1-2 Sätze)"
                },
                "issuer": {
                    "type": "string",
                    "description": "Identifikation des Agents oder Users (z.B. 'claude-agent-001')"
                },
                "parent_id": {
                    "type": "string",
                    "description": "ID des übergeordneten Knotens. None nur für Root-Knoten (max. 1 Root)."
                },
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress"],
                    "description": "Initialer Status. 'in_progress' wenn sofort bearbeitet wird.",
                    "default": "open"
                },
                "synonyms": {
                    "type": "string",
                    "description": "Kommagetrennte alternative Bezeichnungen (optional)"
                }
            },
            "required": ["name", "reasoning", "summary", "issuer"]
        }
    },

    # ------------------------------------------------------------------
    # spider_get_node
    # ------------------------------------------------------------------
    {
        "name": "spider_get_node",
        "description": (
            "Gibt einen einzelnen Knoten anhand seiner ID zurück, inkl. "
            "aktuellem reifegrad und confidence. "
            "WANN VERWENDEN: Vor dem Aktualisieren/Ablehnen/Akzeptieren eines Knotens."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "ID des Knotens"
                }
            },
            "required": ["node_id"]
        }
    },

    # ------------------------------------------------------------------
    # spider_get_tree
    # ------------------------------------------------------------------
    {
        "name": "spider_get_tree",
        "description": (
            "Gibt den gesamten Planungsbaum als flache Liste zurück. "
            "WANN VERWENDEN: Am Anfang jeder Session, vor dem Erstellen neuer Knoten "
            "(Duplikate vermeiden), zur Orientierung im aktuellen Planungsstand."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "Wenn true, nur aktive (nicht abgelehnte) Knoten zurückgeben",
                    "default": False
                }
            },
            "required": []
        }
    },

    # ------------------------------------------------------------------
    # spider_get_tree_stats
    # ------------------------------------------------------------------
    {
        "name": "spider_get_tree_stats",
        "description": (
            "Gibt Statistiken und Fortschrittsmetriken des Planungsbaums zurück. "
            "Zeigt completion_percentage (root_reifegrad × 100). "
            "Planungsphase ist abgeschlossen wenn completion_percentage == 100. "
            "WANN VERWENDEN: Am Anfang und Ende jeder Session als Fortschrittsbericht."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    # ------------------------------------------------------------------
    # spider_update_node
    # ------------------------------------------------------------------
    {
        "name": "spider_update_node",
        "description": (
            "Aktualisiert Metadaten eines bestehenden Knotens. "
            "confidence und reifegrad werden automatisch neu berechnet. "
            "WANN VERWENDEN: Wenn sich die Bewertung, Zusammenfassung oder der "
            "Status eines Knotens ändert. Das Feld 'reason' ist Pflicht."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "ID des zu aktualisierenden Knotens"
                },
                "issuer": {
                    "type": "string",
                    "description": "Wer nimmt die Änderung vor?"
                },
                "reason": {
                    "type": "string",
                    "description": "Warum wird die Änderung vorgenommen? (Pflichtfeld für Audit-Log)"
                },
                "name": {"type": "string", "description": "Neuer Name (optional)"},
                "reasoning": {"type": "string", "description": "Neue Begründung (optional)"},
                "summary": {"type": "string", "description": "Neue Zusammenfassung (optional)"},
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "accepted", "rejected"],
                    "description": "Neuer Status (optional)"
                },
                "synonyms": {"type": "string", "description": "Neue Synonyme (optional)"}
            },
            "required": ["node_id", "issuer", "reason"]
        }
    },

    # ------------------------------------------------------------------
    # spider_reject_node
    # ------------------------------------------------------------------
    {
        "name": "spider_reject_node",
        "description": (
            "Lehnt einen Entscheidungsknoten ab (active=False, status='rejected'). "
            "Der Knoten verbleibt im Baum für historische Nachvollziehbarkeit. "
            "Abgelehnte Knoten zählen als reifegrad=1.0 (Entscheidung getroffen). "
            "WANN VERWENDEN: Wenn eine Option/Alternative als ungeeignet bewertet wurde. "
            "WICHTIG: Immer eine ausführliche Begründung angeben. "
            "WICHTIG: Alle Alternativen eines Bereichs müssen entweder rejected oder "
            "accepted sein, bevor der Parent als vollständig gilt."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "ID des abzulehnenden Knotens"
                },
                "issuer": {
                    "type": "string",
                    "description": "Wer lehnt ab?"
                },
                "reason": {
                    "type": "string",
                    "description": "Ausführliche Begründung der Ablehnung"
                }
            },
            "required": ["node_id", "issuer", "reason"]
        }
    },

    # ------------------------------------------------------------------
    # spider_accept_node
    # ------------------------------------------------------------------
    {
        "name": "spider_accept_node",
        "description": (
            "Akzeptiert einen Entscheidungsknoten als finale Entscheidung. "
            "Setzt status='accepted', acceptionDate. "
            "WANN VERWENDEN: Wenn eine finale Entscheidung für diesen Planungsbereich "
            "getroffen wurde und alle Alternativen bewertet/abgelehnt sind. "
            "WICHTIG: Ein Knoten sollte nur akzeptiert werden wenn seine Geschwister "
            "rejected oder ebenfalls accepted sind."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "ID des zu akzeptierenden Knotens"
                },
                "issuer": {
                    "type": "string",
                    "description": "Wer akzeptiert?"
                },
                "reason": {
                    "type": "string",
                    "description": "Begründung der Akzeptierung"
                }
            },
            "required": ["node_id", "issuer", "reason"]
        }
    },

    # ------------------------------------------------------------------
    # spider_add_action
    # ------------------------------------------------------------------
    {
        "name": "spider_add_action",
        "description": (
            "Fügt einen manuellen Audit-Log-Eintrag hinzu. "
            "WANN VERWENDEN: Für wichtige Überlegungen, Analysen oder Ereignisse, "
            "die nicht über create/reject/accept abgebildet sind. "
            "Z.B.: 'Externe Recherche durchgeführt', 'Stakeholder befragt', "
            "'Technische Bewertung abgeschlossen'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "knoten_id": {
                    "type": "string",
                    "description": "ID des betroffenen Knotens"
                },
                "issuer": {
                    "type": "string",
                    "description": "Wer führt die Aktion aus?"
                },
                "reason": {
                    "type": "string",
                    "description": "Warum?"
                },
                "action_description": {
                    "type": "string",
                    "description": "Was wurde getan/entschieden?"
                },
                "change": {
                    "type": "object",
                    "description": "Optionales Dict mit {field: {old: ..., new: ...}}"
                }
            },
            "required": ["knoten_id", "issuer", "reason", "action_description"]
        }
    },

    # ------------------------------------------------------------------
    # spider_get_children
    # ------------------------------------------------------------------
    {
        "name": "spider_get_children",
        "description": (
            "Gibt alle direkten Kindknoten eines Knotens zurück. "
            "WANN VERWENDEN: Um den Fortschritt eines Bereichs zu prüfen "
            "oder bevor neue Kindknoten erstellt werden."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "ID des Elternknotens"
                }
            },
            "required": ["node_id"]
        }
    },
]


# ---------------------------------------------------------------------------
# Anthropic-kompatibles Format
# ---------------------------------------------------------------------------

def get_anthropic_tools() -> List[dict]:
    """Gibt die Tool-Schemas im Anthropic-API-Format zurück."""
    return SPIDER_TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# OpenAI-kompatibles Format
# ---------------------------------------------------------------------------

def get_openai_tools() -> List[dict]:
    """Gibt die Tool-Schemas im OpenAI-API-Format zurück."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            }
        }
        for schema in SPIDER_TOOL_SCHEMAS
    ]

