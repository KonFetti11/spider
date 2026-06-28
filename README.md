# 🕷 Spider – AI Traceability Framework

**POC-Framework zur Nachvollziehbarkeit von AI-Agent-Entscheidungen.**

Spider zwingt Coding-Agents dazu, jeden Entscheidungsschritt als Knoten in einem
persistenten Baumgraphen zu dokumentieren. Das Ergebnis ist ein vollständig
nachvollziehbarer Planungsbaum, der für menschliche Reviewer transparent und
interaktiv visualisierbar ist.

---

## Kernkonzept

```
Root-Knoten (reifegrad = 0.0 → 1.0)
├── Planungsbereich A
│   ├── ✓ Option 1 (akzeptiert)  → reifegrad = 1.0
│   └── ✗ Option 2 (abgelehnt)  → reifegrad = 1.0
└── Planungsbereich B
    └── ? Option X (offen)       → reifegrad = 0.0
```

- **reifegrad = 1.0** am Root = Alle Entscheidungen getroffen → Planungsphase abgeschlossen
- Jede Entscheidung (accept/reject) wird mit Begründung dokumentiert
- Alle Änderungen erzeugen automatisch einen unveränderlichen **Audit-Log (Actions)**

---

## Schnellstart

```bash
# 1. Installieren (editable, inkl. optionalem MCP-Server)
pip install -e ".[mcp]"

# 2. Demo-Daten laden (in ./.spider/spider.db)
python -m spider.db.seed

# 3. Visualisierung starten (wählt freien Port, gibt die URL aus)
python -m spider.launch

# Optional: HTTP-API – nur für Netzwerk-/Remote-Zugriff (Port 8765, Docs unter /docs)
python -m spider.server.main
```

> Für die Einbindung in **eigene** Projekte nicht den obigen Demo-Flow nutzen, sondern
> `spider-init` – siehe [Einbindung in ein neues Projekt](#einbindung-in-ein-neues-projekt).

---

## Projektstruktur

```
spider/
├── db/
│   ├── models.py      # Dataclasses: Node, Action
│   ├── database.py    # SQLite CRUD + reifegrad/confidence-Berechnung
│   └── seed.py        # Demo-Testdaten
├── server/
│   ├── schemas.py     # Pydantic Request/Response-Modelle
│   ├── api.py         # FastAPI REST-Endpunkte
│   └── main.py        # Uvicorn-Einstiegspunkt (Port 8765)
├── tools/
│   ├── agent_tools.py # SpiderTools-Klasse für AI-Agents
│   └── tool_schemas.py# JSON-Schemas für function-calling
├── visualization/
│   ├── serve.py       # Visualisierungsserver (Port 8766)
│   └── tree.html      # Interaktiver D3.js-Baum
├── templates/
│   └── AGENTS.md      # Nutzungsvorlage für Zielprojekte
├── data/
│   └── spider.db      # SQLite-Datenbank (auto-erstellt)
├── AGENTS.md          # Bauanleitung für Coding-Agents
└── .env.example       # Konfigurationsvorlage
```

---

## API-Endpunkte

| Method | Endpunkt                  | Beschreibung                         |
|--------|---------------------------|--------------------------------------|
| GET    | `/nodes`                  | Alle Nodes (flach)                   |
| GET    | `/nodes/{id}`             | Einzelner Node                       |
| GET    | `/nodes/{id}/children`    | Direktkinder eines Nodes             |
| POST   | `/nodes`                  | Neuen Node erstellen                 |
| PATCH  | `/nodes/{id}`             | Node aktualisieren                   |
| POST   | `/nodes/{id}/reject`      | Node ablehnen                        |
| POST   | `/nodes/{id}/accept`      | Node akzeptieren                     |
| GET    | `/tree`                   | Kompletter Baum (flach)              |
| GET    | `/tree/nested`            | Baum verschachtelt                   |
| GET    | `/tree/stats`             | Fortschrittsstatistiken              |
| GET    | `/actions`                | Alle Audit-Log-Einträge              |
| POST   | `/actions`                | Manuellen Audit-Eintrag erstellen    |

---

## Einbindung in ein neues Projekt

### Schritt 1: Spider einmalig installieren
```bash
# Lokal (Entwicklung), aus dem Spider-Repo – inkl. MCP-Server:
pip install -e ".[mcp]"

# Später, nach GitHub-Publish:
pip install "spider[mcp] @ git+https://github.com/<user>/spider.git"
```
Installiere in das Python, das deine Projekte nutzen (System-Python, oder das venv des Projekts).
`[mcp]` ist optional – nur für den nativen MCP-Server nötig.

### Schritt 2: Projekt initialisieren
Ein Befehl macht ein beliebiges Projekt Spider-fähig:
```bash
spider-init /pfad/zum/projekt        # oder: python -m spider.init /pfad/zum/projekt
```
Das legt im Zielprojekt an:
- `.spider/.env` – zentrale Konfiguration (`SPIDER_DB_PATH`, optional `SPIDER_BASE_URL`),
- `.spider/spider.db` – die projekteigene Datenbank (lazy, isoliert pro Projekt),
- `.spider/work_agent.md` – System-Prompt für read-only Subagents,
- `AGENTS.md` – Agent-Anweisungen (neu) bzw. ein angehängter, markierter Block,
- `spider_tools.py` – Tool-Shim (exportiert `spider` und read-only `spider_ro`),
- `.mcp.json` – MCP-Server-Konfiguration für Claude Code & Co.,
- `.claude/commands/spider-plan.md` + `spider-execute.md` – Slash-Commands,
- `spider-viz.ps1` / `spider-viz.sh` – Start-Helper für die Visualisierung.

### Schritt 3: Tools nutzen

**a) Native MCP-Tools (empfohlen, z.B. Claude Code):** Beim Öffnen des Projekts findet der Client
`.mcp.json` und startet `python -m spider.mcp_server` (Direkt-DB, kein Server). Verfügbare Tools:
`spider_create_node`, `spider_get_tree`, `spider_get_tree_stats`, `spider_accept_node`,
`spider_reject_node`, `spider_update_node`, `spider_add_action`, `spider_get_node`,
`spider_get_children`, `spider_get_actions`. (Projekt-MCP-Server einmalig bestätigen.)

**b) Per Python (kein Server nötig):**
```python
from spider_tools import spider       # voller Zugriff
spider.get_tree_stats()
from spider_tools import spider_ro     # read-only (für Subagents; Schreib-Methoden werfen)
```

**Netzwerk-/Remote-Zugriff** (z.B. Claude Code vom Handy): in `.spider/.env`
`SPIDER_BASE_URL=http://<host>:8765` setzen und `python -m spider.server.main` starten –
Shim/MCP nutzen dann HTTP, gleiche DB darunter, keine Migration.

### Schritt 4: Zwei-Phasen-Workflow (Slash-Commands)
- **`/spider-plan`** – Planungsphase: baut den Entscheidungsbaum auf, bis `root.reifegrad == 1.0`.
- **`/spider-execute`** – Ausführungsphase: Orchestrator mit exklusivem Schreibzugriff startet
  read-only Subagents (siehe `.spider/work_agent.md`), die Ergebnisse zurückmelden; nur der
  Orchestrator schreibt sie nach Spider.

### Schritt 5: Visualisierung öffnen
```bash
./spider-viz.ps1        # Windows   (bzw.  ./spider-viz.sh  unter Linux/macOS)
# wählt automatisch einen freien Port und gibt die URL aus
```

### Bestehendes Projekt upgraden
Nach einem Spider-Update die generierten Dateien im Projekt aktualisieren – Nutzerdaten
(`.spider/.env`, `.spider/spider.db`) bleiben unangetastet:
```bash
spider-init /pfad/zum/projekt --force
```

---

## reifegrad-Logik

| Knotentyp                          | reifegrad |
|------------------------------------|-----------|
| Blattknoten, akzeptiert            | 1.0       |
| Blattknoten, abgelehnt             | 1.0       |
| Blattknoten, offen                 | 0.0       |
| Interner Knoten                    | Ø(Children)|
| Root (Ziel)                        | **1.0**   |

---

## Konfiguration (`.spider/.env`)

Pro Projekt liegt die Konfiguration in `.spider/.env` (von `spider-init` erzeugt, autoritativ
geladen via `spider/config.py`). Ein relativer `SPIDER_DB_PATH` wird relativ zur Projektwurzel
aufgelöst.

```env
SPIDER_DB_PATH=.spider/spider.db
# Optionaler Netzwerk-/Remote-Zugriff (Shim/MCP schalten dann auf HTTP):
# SPIDER_BASE_URL=http://127.0.0.1:8765
# Optionale feste Ports (sonst wählt der Viz-Start einen freien Port):
# SPIDER_HOST=127.0.0.1
# SPIDER_PORT=8765
# SPIDER_VIZ_HOST=127.0.0.1
# SPIDER_VIZ_PORT=8766
```

---

## POC-Status & Nächste Schritte

Dieser POC validiert das Grundkonzept. Bei Erfolg geplant:

- [ ] Rückwirkende Integration für laufende Projekte
- [ ] API-Key-Authentifizierung für Multi-Agent-Setups
- [ ] PostgreSQL-Migration für Produktion
- [ ] PDF/Markdown-Export des Entscheidungsbaums
- [ ] Webhook-Benachrichtigungen bei Reifegrad-Schwellwerten
- [ ] pip-Package-Veröffentlichung

