"""
Spider Framework – SQLite-Datenbankschicht.

Verantwortlichkeiten:
  - Schema-Erstellung (Nodes + Actions)
  - CRUD-Operationen
  - Automatische Neuberechnung von confidence und reifegrad nach jeder Änderung
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List

from spider.db.models import Node, Action, now_ms

# Standard-Datenbankpfad (kann per Umgebungsvariable überschrieben werden)
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "spider.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_NODES = """
CREATE TABLE IF NOT EXISTS nodes (
    id              TEXT PRIMARY KEY,
    parentId        TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    reasoning       TEXT NOT NULL DEFAULT '',
    summary         TEXT NOT NULL DEFAULT '',
    creationDate    INTEGER NOT NULL,
    rejectionDate   INTEGER,
    rejectionReason TEXT,
    acceptionDate   INTEGER,
    acceptionReason TEXT,
    issuer          TEXT NOT NULL DEFAULT '',
    confidence      REAL NOT NULL DEFAULT 0.0,
    reifegrad       REAL NOT NULL DEFAULT 0.0,
    status          TEXT NOT NULL DEFAULT 'open',
    name            TEXT NOT NULL DEFAULT '',
    synonyms        TEXT NOT NULL DEFAULT '',
    lastChange      INTEGER NOT NULL
);
"""

SCHEMA_ACTIONS = """
CREATE TABLE IF NOT EXISTS actions (
    id                TEXT PRIMARY KEY,
    date              INTEGER NOT NULL,
    knotenId          TEXT NOT NULL,
    issuer            TEXT NOT NULL DEFAULT '',
    reason            TEXT NOT NULL DEFAULT '',
    actionDescription TEXT NOT NULL DEFAULT '',
    change            TEXT NOT NULL DEFAULT '{}'
);
"""


# ---------------------------------------------------------------------------
# Datenbankverbindung
# ---------------------------------------------------------------------------

class Database:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute(SCHEMA_NODES)
            conn.execute(SCHEMA_ACTIONS)

    # -----------------------------------------------------------------------
    # Hilfsmethoden
    # -----------------------------------------------------------------------

    def _row_to_node(self, row) -> Node:
        d = dict(row)
        d["active"] = bool(d["active"])
        return Node.from_row(d)

    def _row_to_action(self, row) -> Action:
        return Action.from_row(dict(row))

    # -----------------------------------------------------------------------
    # reifegrad / confidence Berechnung
    # -----------------------------------------------------------------------

    def _get_children(self, node_id: str, conn) -> List[Node]:
        cursor = conn.execute(
            "SELECT * FROM nodes WHERE parentId = ?", (node_id,)
        )
        return [self._row_to_node(r) for r in cursor.fetchall()]

    def calculate_reifegrad(self, node_id: str, conn=None) -> float:
        """
        Rekursive Berechnung des Reifegrads:
        - Kein Child + active=True + acceptionDate gesetzt → 1.0
        - Kein Child + active=False (abgelehnt) → 1.0 (Entscheidung getroffen)
        - Kein Child + active=True + kein acceptionDate → 0.0
        - Hat Children → Durchschnitt der Children-Reifegrade
        """
        def _calc(nid: str, c) -> float:
            children = self._get_children(nid, c)
            if not children:
                # Blattknoten: Entscheidung ist getroffen wenn akzeptiert ODER abgelehnt
                row = c.execute("SELECT active, acceptionDate FROM nodes WHERE id = ?", (nid,)).fetchone()
                if row is None:
                    return 0.0
                active = bool(row["active"])
                accepted = row["acceptionDate"] is not None
                if accepted or not active:
                    return 1.0
                return 0.0
            # Interner Knoten: Durchschnitt der Children
            child_grades = [_calc(ch.id, c) for ch in children]
            return sum(child_grades) / len(child_grades)

        if conn is not None:
            return _calc(node_id, conn)
        with self._conn() as c:
            return _calc(node_id, c)

    def calculate_confidence(self, node_id: str, conn=None) -> float:
        """
        Konfidenz eines Knotens:
        - Kein Child → 0.0 (neu / noch nicht bewertet)
        - Hat Children → Durchschnitt der Children-confidence-Werte
        """
        def _calc(nid: str, c) -> float:
            children = self._get_children(nid, c)
            if not children:
                row = c.execute("SELECT confidence FROM nodes WHERE id = ?", (nid,)).fetchone()
                return row["confidence"] if row else 0.0
            vals = [_calc(ch.id, c) for ch in children]
            return sum(vals) / len(vals)

        if conn is not None:
            return _calc(node_id, conn)
        with self._conn() as c:
            return _calc(node_id, c)

    def _recalculate_ancestors(self, node_id: str, conn):
        """Berechnet reifegrad und confidence aller Vorfahren eines Knotens neu."""
        # Pfad nach oben traversieren
        cursor = conn.execute("SELECT parentId FROM nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        if row and row["parentId"]:
            parent_id = row["parentId"]
            rg = self.calculate_reifegrad(parent_id, conn)
            cf = self.calculate_confidence(parent_id, conn)
            conn.execute(
                "UPDATE nodes SET reifegrad = ?, confidence = ?, lastChange = ? WHERE id = ?",
                (rg, cf, now_ms(), parent_id),
            )
            self._recalculate_ancestors(parent_id, conn)

    # -----------------------------------------------------------------------
    # Node CRUD
    # -----------------------------------------------------------------------

    def create_node(self, node: Node) -> Node:
        """Erstellt einen neuen Node und aktualisiert Vorfahren."""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO nodes
                   (id, parentId, active, reasoning, summary, creationDate,
                    rejectionDate, rejectionReason, acceptionDate, acceptionReason,
                    issuer, confidence, reifegrad, status, name, synonyms, lastChange)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    node.id, node.parentId, int(node.active),
                    node.reasoning, node.summary, node.creationDate,
                    node.rejectionDate, node.rejectionReason,
                    node.acceptionDate, node.acceptionReason,
                    node.issuer, node.confidence, node.reifegrad,
                    node.status, node.name, node.synonyms, node.lastChange,
                ),
            )
            self._recalculate_ancestors(node.id, conn)
        return self.get_node(node.id)

    def get_node(self, node_id: str) -> Optional[Node]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
            return self._row_to_node(row) if row else None

    def get_all_nodes(self) -> List[Node]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM nodes ORDER BY creationDate").fetchall()
            return [self._row_to_node(r) for r in rows]

    def get_children(self, node_id: str) -> List[Node]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE parentId = ? ORDER BY creationDate", (node_id,)
            ).fetchall()
            return [self._row_to_node(r) for r in rows]

    def get_root_nodes(self) -> List[Node]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE parentId IS NULL ORDER BY creationDate"
            ).fetchall()
            return [self._row_to_node(r) for r in rows]

    def update_node(self, node_id: str, updates: dict, issuer: str, reason: str) -> Optional[Node]:
        """
        Aktualisiert einen Node. Erstellt automatisch einen Action-Eintrag.
        confidence und reifegrad werden NICHT direkt geschrieben – sie werden berechnet.
        """
        protected = {"id", "creationDate", "confidence", "reifegrad"}
        updates = {k: v for k, v in updates.items() if k not in protected}

        old_node = self.get_node(node_id)
        if old_node is None:
            return None

        ts = now_ms()
        updates["lastChange"] = ts

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [node_id]

        # Änderungsprotokoll
        old_dict = old_node.to_dict()
        change_log = {
            k: {"old": old_dict.get(k), "new": v}
            for k, v in updates.items()
            if k != "lastChange" and old_dict.get(k) != v
        }

        with self._conn() as conn:
            conn.execute(f"UPDATE nodes SET {set_clause} WHERE id = ?", values)
            self._recalculate_ancestors(node_id, conn)

            # Reifegrad des Knotens selbst neu berechnen
            rg = self.calculate_reifegrad(node_id, conn)
            cf = self.calculate_confidence(node_id, conn)
            conn.execute(
                "UPDATE nodes SET reifegrad = ?, confidence = ? WHERE id = ?",
                (rg, cf, node_id),
            )

            # Action-Eintrag
            action = Action(
                id=str(uuid.uuid4()),
                date=ts,
                knotenId=node_id,
                issuer=issuer,
                reason=reason,
                actionDescription=f"Node aktualisiert: {', '.join(change_log.keys())}",
                change=json.dumps(change_log, ensure_ascii=False),
            )
            conn.execute(
                """INSERT INTO actions (id, date, knotenId, issuer, reason, actionDescription, change)
                   VALUES (?,?,?,?,?,?,?)""",
                (action.id, action.date, action.knotenId, action.issuer,
                 action.reason, action.actionDescription, action.change),
            )
        return self.get_node(node_id)

    def reject_node(self, node_id: str, issuer: str, reason: str) -> Optional[Node]:
        """Lehnt einen Knoten ab (active=False, status='rejected')."""
        ts = now_ms()
        return self.update_node(
            node_id,
            {"active": 0, "status": "rejected", "rejectionDate": ts, "rejectionReason": reason},
            issuer=issuer,
            reason=reason,
        )

    def accept_node(self, node_id: str, issuer: str, reason: str) -> Optional[Node]:
        """Akzeptiert einen Knoten (status='accepted', acceptionDate gesetzt)."""
        ts = now_ms()
        return self.update_node(
            node_id,
            {"status": "accepted", "acceptionDate": ts, "acceptionReason": reason},
            issuer=issuer,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Action CRUD
    # -----------------------------------------------------------------------

    def create_action(self, action: Action) -> Action:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO actions (id, date, knotenId, issuer, reason, actionDescription, change)
                   VALUES (?,?,?,?,?,?,?)""",
                (action.id, action.date, action.knotenId, action.issuer,
                 action.reason, action.actionDescription, action.change),
            )
        return action

    def get_actions(self, knoten_id: Optional[str] = None) -> List[Action]:
        with self._conn() as conn:
            if knoten_id:
                rows = conn.execute(
                    "SELECT * FROM actions WHERE knotenId = ? ORDER BY date", (knoten_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM actions ORDER BY date").fetchall()
            return [self._row_to_action(r) for r in rows]

    def get_action(self, action_id: str) -> Optional[Action]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
            return self._row_to_action(row) if row else None

    # -----------------------------------------------------------------------
    # Baumstruktur
    # -----------------------------------------------------------------------

    def get_tree(self) -> List[dict]:
        """
        Gibt alle Nodes als flache Liste zurück.
        Die Baumstruktur ergibt sich aus parentId-Referenzen.
        """
        return [n.to_dict() for n in self.get_all_nodes()]

    def get_tree_nested(self, parent_id: Optional[str] = None) -> List[dict]:
        """Gibt den Baum als verschachteltes JSON zurück."""
        with self._conn() as conn:
            if parent_id is None:
                rows = conn.execute(
                    "SELECT * FROM nodes WHERE parentId IS NULL ORDER BY creationDate"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM nodes WHERE parentId = ? ORDER BY creationDate", (parent_id,)
                ).fetchall()

            result = []
            for row in rows:
                node_dict = dict(row)
                node_dict["active"] = bool(node_dict["active"])
                node_dict["children"] = self.get_tree_nested(node_dict["id"])
                result.append(node_dict)
            return result


# ---------------------------------------------------------------------------
# Singleton-Instanz
# ---------------------------------------------------------------------------
import os

_db_instance: Optional[Database] = None


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        db_path = os.environ.get("SPIDER_DB_PATH", str(DEFAULT_DB_PATH))
        _db_instance = Database(Path(db_path))
    return _db_instance

