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
# 1. Abhängigkeiten
pip install -r spider/requirements.txt

# 2. Testdaten
python -m spider.db.seed

# 3. API-Server starten (Port 8765)
python -m spider.server.main

# 4. Visualisierung starten (Port 8766)
python -m spider.visualization.serve

# 5. Browser öffnen
#    Visualisierung: http://localhost:8766
#    API-Docs:       http://localhost:8765/docs
```

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

### Schritt 1: Spider bereitstellen
```bash
# Option A: Direkt im Projekt-Repository (Submodule oder Kopie)
cp -r spider/ /mein-projekt/spider/

# Option B: Als Python-Package (nach Setup-Erstellung)
pip install spider-traceability
```

### Schritt 2: AGENTS.md ins Zielprojekt kopieren
```bash
cp spider/templates/AGENTS.md /mein-projekt/AGENTS.md
# oder für Claude:
cp spider/templates/AGENTS.md /mein-projekt/CLAUDE.md
```

### Schritt 3: Spider-Server starten
```bash
# Einmalig zu Beginn des Projekts
python -m spider.server.main &
python -m spider.visualization.serve &
```

### Schritt 4: Tools in Agent-System einbinden
```python
# Für OpenAI function-calling:
from spider.tools.tool_schemas import get_openai_tools
tools = get_openai_tools()

# Für Anthropic/Claude:
from spider.tools.tool_schemas import get_anthropic_tools
tools = get_anthropic_tools()

# Direkter Aufruf (ohne function-calling):
from spider.tools.agent_tools import SpiderTools
spider = SpiderTools()
stats = spider.get_planning_progress()
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

## Konfiguration (`.env`)

```env
SPIDER_DB_PATH=data/spider.db
SPIDER_HOST=127.0.0.1
SPIDER_PORT=8765
SPIDER_VIZ_HOST=127.0.0.1
SPIDER_VIZ_PORT=8766
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

