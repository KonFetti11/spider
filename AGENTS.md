# AGENTS.md – Spider AI Traceability Framework

> Diese Datei beschreibt das **Spider-Framework** für Coding-Agents, die das Framework
> selbst implementieren oder erweitern sollen. Sie ist die Bauanleitung für das Projekt.
>
> Für die Nutzungsanleitung in Zielprojekten → siehe `templates/AGENTS.md`

---

## Was ist Spider?

Spider ist ein **POC-Framework zur Nachvollziehbarkeit von AI-Agent-Entscheidungen**.
Es zwingt Coding-Agents dazu, jeden Entscheidungsschritt als Knoten in einem persistenten
Baumgraphen zu dokumentieren. Ziel ist die vollständige Planungstransparenz für
menschliche Reviewer.

**Kernidee**: Die AI baut einen **Planungsbaum** auf, in dem jede Entscheidung,
jede Alternative und jede Ablehnung als Knoten mit Begründung dokumentiert wird.
Ein `reifegrad = 1.0` am Root-Knoten bedeutet: Alle Entscheidungen sind getroffen.

---

## Projektstruktur

```
spider/
├── db/
│   ├── __init__.py
│   ├── models.py          # Dataclasses: Node, Action
│   ├── database.py        # SQLite CRUD + reifegrad/confidence-Berechnung
│   └── seed.py            # Testdaten (POC-Demo)
├── server/
│   ├── __init__.py
│   ├── schemas.py         # Pydantic-Schemas (Request/Response)
│   ├── api.py             # FastAPI-App (alle REST-Endpunkte)
│   └── main.py            # Uvicorn-Einstiegspunkt
├── tools/
│   ├── __init__.py
│   ├── agent_tools.py     # Python-Wrapper-Klasse SpiderTools
│   └── tool_schemas.py    # JSON-Schemas für Claude/OpenAI function-calling
├── visualization/
│   ├── __init__.py
│   ├── serve.py           # FastAPI-Visualisierungsserver (Port 8766)
│   └── tree.html          # Interaktive D3.js-Baumvisualisierung
├── templates/
│   └── AGENTS.md          # Nutzungsanleitung für Zielprojekte
├── data/                  # SQLite-Datenbankdatei (auto-erstellt)
│   └── spider.db
├── AGENTS.md              # Diese Datei (Bauanleitung)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Implementierungsreihenfolge (WICHTIG)

Implementiere in dieser Reihenfolge, da spätere Phasen auf früheren aufbauen:

### Phase 1: Datenmodell (`db/`)
1. `db/models.py` – Dataclasses `Node` und `Action` mit allen Pflichtfeldern
2. `db/database.py` – SQLite-Schema + CRUD + **Berechnungslogik**
3. `db/seed.py` – Testdaten für POC-Demo

**Kritische Berechnungslogik:**
- `reifegrad` eines Knotens = rekursiver Durchschnitt der Children-Reifegrade
- Blattknoten-Reifegrad = `1.0` wenn `acceptionDate` gesetzt ODER `active=False` (abgelehnt)
- Blattknoten-Reifegrad = `0.0` wenn noch keine Entscheidung getroffen
- `confidence` = Durchschnitt der Children-confidence; bei Blattknoten aus DB-Wert
- Bei jeder Schreiboperation: Alle Vorfahren neu berechnen (`_recalculate_ancestors`)

### Phase 2: HTTP-Server (`server/`)
4. `server/schemas.py` – Pydantic-Modelle (confidence/reifegrad sind READ-ONLY)
5. `server/api.py` – FastAPI REST-Endpunkte
6. `server/main.py` – Uvicorn-Einstiegspunkt

**Kritische API-Konventionen:**
- `confidence` und `reifegrad` werden NIEMALS direkt über die API geschrieben
- Jede Schreiboperation (create/update/reject/accept) erstellt automatisch einen Action-Eintrag
- `POST /nodes/{id}/reject` und `POST /nodes/{id}/accept` sind dedizierte Endpunkte
- CORS muss aktiviert sein (`allow_origins=["*"]`) für den Visualisierungsserver

### Phase 3: AI-Tools (`tools/`)
7. `tools/agent_tools.py` – SpiderTools-Klasse mit HTTP-Wrappern
8. `tools/tool_schemas.py` – JSON-Schemas für function-calling

**Konventionen:**
- Nur `urllib` (Standard-Bibliothek) verwenden – keine externen HTTP-Abhängigkeiten
- Alle Methoden müssen ausführliche Docstrings haben (wann verwenden?)
- `SpiderAPIError` werfen wenn Server nicht erreichbar

### Phase 4: Visualisierung (`visualization/`)
9. `visualization/serve.py` – FastAPI-Server auf Port 8766
10. `visualization/tree.html` – D3.js-interaktiver Baum

**Visualisierungsanforderungen:**
- D3.js via CDN (keine lokale Installation)
- Drag & Drop (d3.zoom mit translate)
- Mausrad-Zoom (d3.zoom mit scale)
- Hover-Tooltip mit ALLEN Node-Feldern
- Aktive Knoten: farbig nach Status
- Inaktive Knoten: grau, transparent, gestrichelte Links
- Reifegrad als Ring/Fortschrittsbalken pro Knoten
- Auto-Refresh alle 5 Sekunden

### Phase 5: Templates & Dokumentation
11. `templates/AGENTS.md` – Nutzungsanleitung für Zielprojekte
12. `README.md` – Schnellstart + Einbindungsstrategie
13. `requirements.txt` – Python-Abhängigkeiten

---

## Datenklassen (Pflichtfelder)

### Node
```python
@dataclass
class Node:
    id: str                          # UUID
    parentId: Optional[str]          # None = Root
    active: bool                     # False = abgelehnt
    reasoning: str                   # Warum existiert dieser Knoten?
    summary: str                     # Kurze Zusammenfassung
    creationDate: int                # Unix ms
    issuer: str                      # Agent/User-ID
    name: str                        # Anzeigename

    # Optionale Felder
    rejectionDate: Optional[int]     # Unix ms
    rejectionReason: Optional[str]
    acceptionDate: Optional[int]     # Unix ms
    acceptionReason: Optional[str]
    synonyms: str = ""
    status: str = "open"             # open|accepted|rejected|in_progress

    # Berechnete Felder (READ-ONLY, niemals direkt setzen)
    confidence: float = 0.0          # 0.0–1.0
    reifegrad: float = 0.0           # 0.0–1.0

    lastChange: int                  # Unix ms
```

### Action
```python
@dataclass
class Action:
    id: str
    date: int             # Unix ms – IDENTISCH mit Node.lastChange
    knotenId: str         # Referenz auf Node
    issuer: str
    reason: str
    actionDescription: str
    change: str           # JSON: {"field": {"old": ..., "new": ...}}
```

---

## API-Endpunkte (Übersicht)

| Method | Path                        | Beschreibung                    |
|--------|-----------------------------|---------------------------------|
| GET    | /nodes                      | Alle Nodes (flach)              |
| GET    | /nodes/{id}                 | Einzelner Node                  |
| GET    | /nodes/{id}/children        | Direktkinder                    |
| POST   | /nodes                      | Node erstellen                  |
| PATCH  | /nodes/{id}                 | Node aktualisieren              |
| POST   | /nodes/{id}/reject          | Node ablehnen                   |
| POST   | /nodes/{id}/accept          | Node akzeptieren                |
| GET    | /tree                       | Baum flach (für Visualisierung) |
| GET    | /tree/nested                | Baum verschachtelt              |
| GET    | /tree/stats                 | Fortschrittsstatistiken         |
| GET    | /actions                    | Alle Actions                    |
| POST   | /actions                    | Manuelle Action erstellen       |

---

## Konventionen & Qualitätsanforderungen

### Timestamp-Konsistenz
- ALLE Timestamps in **Unix Millisekunden** (int)
- `Action.date` MUSS identisch sein mit `Node.lastChange` der zugehörigen Operation
- Diese Konsistenz ermöglicht die zeitliche Rückverfolgbarkeit

### reifegrad-Semantik
- Ein Knoten mit `reifegrad = 1.0` bedeutet: **Alle Entscheidungen darunter sind getroffen**
- Abgelehnte Knoten (`active=False`) zählen als `reifegrad = 1.0` (Entscheidung getroffen)
- Das Ziel des Planungsprozesses: `root.reifegrad == 1.0`

### Fehlerbehandlung
- Server gibt HTTP 404 wenn Node nicht gefunden
- `SpiderAPIError` mit klarer Fehlermeldung wenn Server nicht erreichbar
- Alle schreibenden Operationen in DB-Transaktionen (Rollback bei Fehler)

### POC-Grenzen (bewusste Vereinfachungen)
- Keine Authentifizierung (lokaler Server)
- Keine Mehrbenutzer-Unterstützung
- SQLite statt PostgreSQL (kein separater DB-Server)
- Kein Soft-Delete (abgelehnte Nodes bleiben dauerhaft)

---

## Setup & Start

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Testdaten einfügen
python -m spider.db.seed

# API-Server starten (Port 8765)
python -m spider.server.main

# Visualisierungsserver starten (Port 8766)
python -m spider.visualization.serve

# Visualisierung öffnen
# http://localhost:8766
```

---

## Tests (POC-Mindestanforderungen)

Verifiziere nach Implementierung:
1. Seed-Skript läuft ohne Fehler durch
2. API-Server startet und `/docs` ist erreichbar
3. `GET /tree/stats` zeigt `root_reifegrad < 1.0` (unvollständiger Baum in Seed-Daten)
4. `POST /nodes/{id}/accept` erhöht den reifegrad des Parents
5. Visualisierungsserver zeigt Baum im Browser
6. Hover-Tooltip zeigt alle Node-Felder an

---

## Nächste Schritte nach POC-Validierung

Falls der POC erfolgreich ist, sind folgende Erweiterungen geplant:
- **Rückwirkende Integration**: Import von Entscheidungsprotokollen aus laufenden Projekten
- **Authentifizierung**: API-Keys für Multi-Agent-Szenarien
- **PostgreSQL-Migration**: Für persistente Produktionsumgebungen
- **Export-Funktion**: Entscheidungsbaum als PDF/Markdown-Report
- **Webhook-Support**: Benachrichtigungen bei Reifegrad-Schwellwerten

