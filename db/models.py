"""
Spider Framework – Datenklassen für Node und Action.

Node:    Repräsentiert einen Entscheidungsknoten im Planungsbaum.
Action:  Dokumentiert jede Änderung an einem Node (Audit-Log).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List
import time
import json


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def now_ms() -> int:
    """Aktueller Unix-Timestamp in Millisekunden."""
    return int(time.time() * 1000)


def to_dict(obj) -> dict:
    """Serialisiert eine Dataclass rekursiv in ein Dict."""
    return asdict(obj)


def to_json(obj) -> str:
    """Serialisiert eine Dataclass in einen JSON-String."""
    return json.dumps(asdict(obj), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Node-Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """
    Repräsentiert einen Knoten im Entscheidungsbaum.

    Felder:
        id              – Eindeutiger Bezeichner (UUID/String)
        parentId        – Referenz auf den Elternknoten (None = Root)
        active          – Ob der Knoten aktiv ist (nicht abgelehnt)
        reasoning       – Begründung, warum dieser Knoten existiert
        summary         – Kurze Zusammenfassung des Knotens
        creationDate    – Erstellungsdatum (Unix ms)
        rejectionDate   – Ablehnungsdatum (Unix ms, None wenn nicht abgelehnt)
        rejectionReason – Begründung der Ablehnung
        acceptionDate   – Akzeptierungsdatum (Unix ms, None wenn nicht akzeptiert)
        acceptionReason – Begründung der Akzeptierung
        issuer          – Ersteller/Veränderer (Agent-Name oder User)
        confidence      – Konfidenz 0.0–1.0 (abgeleitet von Children, 0 wenn neu)
        reifegrad       – Reifegrad 0.0–1.0 (rekursiv aus Children berechnet)
        status          – Aktueller Status: 'open' | 'accepted' | 'rejected' | 'in_progress'
        name            – Anzeigename des Knotens
        synonyms        – Kommagetrennte Synonyme/alternative Bezeichnungen
        taskRef         – Link/Pfad zur Datei mit der Aufgabenstellung (optional)
        taskMarkdown    – Aufgabenstellung als Markdown-Inhalt, direkt im Knoten (optional)
        lastChange      – Letzter Änderungszeitpunkt (Unix ms)
    """
    id: str
    parentId: Optional[str]
    active: bool
    reasoning: str
    summary: str
    creationDate: int
    issuer: str
    name: str

    # Optionale Felder mit Defaults
    rejectionDate: Optional[int] = None
    rejectionReason: Optional[str] = None
    acceptionDate: Optional[int] = None
    acceptionReason: Optional[str] = None
    synonyms: str = ""
    status: str = "open"                 # open | accepted | rejected | in_progress
    taskRef: str = ""                    # Link/Pfad zur Aufgabenstellungs-Datei
    taskMarkdown: str = ""                # Aufgabenstellung als Markdown-Inhalt

    # Berechnete Felder (werden automatisch aus der DB-Logik gesetzt)
    confidence: float = 0.0             # 0.0 für neue Knoten; Durchschnitt der Children
    reifegrad: float = 0.0              # 0.0 neu; 1.0 wenn alle Entscheidungen darunter getroffen

    lastChange: int = field(default_factory=now_ms)

    # ------------------------------------------------------------------
    # Serialisierung
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_row(cls, row: dict) -> "Node":
        """Erstellt einen Node aus einer SQLite-Row (dict)."""
        return cls.from_dict(row)


# ---------------------------------------------------------------------------
# Action-Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class Action:
    """
    Dokumentiert eine Änderung an einem Node (unveränderliches Audit-Log).

    Felder:
        id                – Eindeutiger Bezeichner
        date              – Zeitstempel (Unix ms) – IDENTISCH mit lastChange des
                            zugehörigen Node zum Zeitpunkt der Änderung
        knotenId          – Referenz auf den betroffenen Node
        issuer            – Ausführender Agent oder User
        reason            – Warum wurde die Änderung vorgenommen?
        actionDescription – Kurze Beschreibung der Aktion (z. B. "Node akzeptiert")
        change            – JSON-String mit den geänderten Feldern {field: {old, new}}
    """
    id: str
    date: int                    # identisch mit Node.lastChange → Rückverfolgbarkeit
    knotenId: str
    issuer: str
    reason: str
    actionDescription: str
    change: str                  # JSON-String: {"fieldName": {"old": ..., "new": ...}}

    # ------------------------------------------------------------------
    # Serialisierung
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "Action":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_row(cls, row: dict) -> "Action":
        return cls.from_dict(row)

    def get_change_dict(self) -> dict:
        """Deserialisiert das change-Feld als Python-Dict."""
        try:
            return json.loads(self.change)
        except (json.JSONDecodeError, TypeError):
            return {}

