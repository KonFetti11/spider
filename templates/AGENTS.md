# AGENTS.md – Spider Traceability Framework (Nutzungsanleitung)

> Kopiere diese Datei als `AGENTS.md` (oder `CLAUDE.md`) in das Wurzelverzeichnis
> jedes Projekts, das von AI-Agents begleitet wird und Spider nutzen soll.

---

## Deine Aufgabe als AI-Agent in diesem Projekt

Du arbeitest mit dem **Spider Traceability Framework**. Das bedeutet:

**Du musst JEDEN Entscheidungsschritt und JEDE Alternative in der Spider-Datenbank
dokumentieren – bevor du mit der Implementierung beginnst.**

Spider-Tools stehen als **native MCP-Tools** zur Verfügung (via `.mcp.json`, Direkt-DB,
kein Server nötig) oder per Python (`from spider_tools import spider`). Du hast Zugriff
auf die folgenden Tools:

- `spider_create_node` – Neuen Entscheidungsknoten anlegen
- `spider_get_node` – Einzelnen Knoten abrufen
- `spider_get_tree` – Kompletten Baum abrufen
- `spider_get_tree_stats` – Fortschrittsstatistiken
- `spider_update_node` – Knotenfelder aktualisieren
- `spider_reject_node` – Option ablehnen (mit Begründung)
- `spider_accept_node` – Entscheidung final treffen
- `spider_add_action` – Manuellen Audit-Log-Eintrag hinzufügen
- `spider_get_children` – Direktkinder eines Knotens abrufen

---

## Pflichtverhalten – Wann du Spider verwenden MUSST

### 1. Zu Beginn JEDER Session
```
spider_get_tree_stats()   → Fortschritt prüfen
spider_get_tree()         → Aktuellen Stand überblicken
```
Lies den Baum und orientiere dich: Was ist bereits entschieden? Was ist noch offen?

### 2. Vor JEDER Entscheidung: Alternativen anlegen
Bevor du eine Entscheidung triffst, lege ALLE sinnvollen Alternativen als
Geschwisterknoten (gleicher `parent_id`) an:

```python
# Beispiel: Datenbankauswahl
postgres = spider_create_node(
    name="PostgreSQL",
    reasoning="Relationale DB mit starker Typisierung und ACID-Eigenschaften",
    summary="PostgreSQL als primäre Datenbank",
    issuer="agent-001",
    parent_id="db-entscheidung-001"
)
sqlite = spider_create_node(
    name="SQLite",
    reasoning="Eingebettete DB, kein separater Server, ideal für POC",
    summary="SQLite für lokale Entwicklung",
    issuer="agent-001",
    parent_id="db-entscheidung-001"
)
```

### 3. Nach der Bewertung: Ablehnen + Akzeptieren
Lehne alle nicht gewählten Alternativen AB, bevor du die gewählte akzeptierst:

```python
# Falsche Alternative ablehnen
spider_reject_node(
    node_id=postgres["id"],
    issuer="agent-001",
    reason="PostgreSQL zu komplex für POC; kein separater Server erwünscht. SQLite ausreichend."
)

# Gewählte Option akzeptieren
spider_accept_node(
    node_id=sqlite["id"],
    issuer="agent-001",
    reason="SQLite erfüllt alle Anforderungen: zero-config, built-in Python, ausreichend für POC"
)
```

### 4. Bei wichtigen Zwischenschritten: Action hinzufügen
```python
spider_add_action(
    knoten_id=sqlite["id"],
    issuer="agent-001",
    reason="Recherche durchgeführt",
    action_description="Benchmark-Vergleich SQLite vs PostgreSQL abgeschlossen",
    change={"performance": {"old": "unbekannt", "new": "SQLite: ~10k writes/sec"}}
)
```

### 5. Am Ende JEDER Session
```python
stats = spider_get_tree_stats()
# Berichte: "Spider Planungsfortschritt: X%"
```

---

## Baumstruktur-Prinzipien

### Root-Knoten
Es gibt genau **einen Root-Knoten** pro Projekt (kein `parentId`).
Er repräsentiert das Gesamtprojekt und sein `reifegrad` zeigt den
Planungsfortschritt des gesamten Projekts (Ziel: `1.0`).

### Entscheidungsbereiche (interne Knoten)
Gruppiere verwandte Entscheidungen unter einem gemeinsamen Elternknoten:
```
Root
├── Architektur & Tech-Stack
│   ├── ✓ Python (akzeptiert)
│   ├── ✗ Java (abgelehnt)
│   └── ✓ FastAPI (akzeptiert)
├── UI/UX
│   └── ...
└── Deployment
    └── ...
```

### Blattknoten (finale Entscheidungen)
Blattknoten mit `status = accepted` ODER `active = False` (rejected) zählen
als vollständig (`reifegrad = 1.0`). Erst wenn alle Blattknoten eines Zweigs
vollständig sind, steigt der `reifegrad` des Elternknotens.

---

## reifegrad verstehen

| reifegrad | Bedeutung |
|-----------|-----------|
| `0.0`     | Keine Entscheidungen getroffen |
| `0.0–0.5` | Planungsphase hat begonnen |
| `0.5–0.9` | Planungsphase weitgehend abgeschlossen |
| `1.0`     | Alle Entscheidungen getroffen – Planungsphase abgeschlossen |

**Ziel**: `root.reifegrad == 1.0` vor Beginn der Implementierungsphase.

---

## Pflichtfelder beim Erstellen eines Knotens

| Feld       | Pflicht | Beschreibung |
|------------|---------|--------------|
| `name`     | ✓       | Kurzer, präziser Name (max. 60 Zeichen) |
| `reasoning`| ✓       | WARUM existiert dieser Knoten? Welche Frage steht dahinter? |
| `summary`  | ✓       | Was beschreibt dieser Knoten in 1–2 Sätzen? |
| `issuer`   | ✓       | Deine Agent-ID (z.B. `claude-agent-1`) |
| `parent_id`| ✓*      | Referenz auf Elternknoten (*außer Root) |

---

## Verbotene Aktionen

❌ **Nie direkt `confidence` oder `reifegrad` setzen** – diese werden automatisch berechnet  
❌ **Nie einen Knoten akzeptieren ohne Alternativen bewertet zu haben**  
❌ **Nie mit der Implementierung beginnen bevor die Planungsphase abgeschlossen ist** (reifegrad < 1.0 am Root)  
❌ **Nie Entscheidungen ohne Begründung (`reason`) treffen**  

---

## Zugriff & Visualisierung

Für die Tools ist **kein Server nötig** (Direkt-DB via MCP oder `spider_tools.py`).

```bash
# Visualisierung des Baums (wählt freien Port, gibt URL aus):
./spider-viz.ps1          # Windows   (bzw.  ./spider-viz.sh)

# Nur für Netzwerk-/Remote-Zugriff: SPIDER_BASE_URL in .spider/.env setzen und
python -m spider.server.main
```

---

## Zwei-Phasen-Workflow

- `/spider-plan` – Planungsphase: Entscheidungsbaum aufbauen, bis `root.reifegrad == 1.0`.
- `/spider-execute` – Ausführungsphase: Orchestrator mit exklusivem Schreibzugriff startet
  read-only Subagents (`.spider/work_agent.md`), die zurückmelden; nur der Orchestrator schreibt.

---

## Beispiel: Vollständiger Planungsdurchlauf

```python
# 1. Session starten
stats = spider_get_tree_stats()
# → {"completion_percentage": 0.0, ...}

# 2. Root-Knoten erstellen (einmalig)
root = spider_create_node(
    name="E-Commerce Platform v2",
    reasoning="Neues Projekt: Wir bauen eine E-Commerce-Plattform",
    summary="Root-Knoten für E-Commerce Platform v2",
    issuer="claude-agent-1"
)

# 3. Planungsbereiche aufspannen
tech = spider_create_node(
    name="Tech-Stack Entscheidung",
    reasoning="Wir müssen die grundlegenden Technologien festlegen",
    summary="Auswahl Backend-Framework, Datenbank, Frontend",
    issuer="claude-agent-1",
    parent_id=root["id"],
    status="in_progress"
)

# 4. Alternativen anlegen
django  = spider_create_node(name="Django",  reasoning="...", summary="...", issuer="claude-agent-1", parent_id=tech["id"])
fastapi = spider_create_node(name="FastAPI", reasoning="...", summary="...", issuer="claude-agent-1", parent_id=tech["id"])

# 5. Bewerten und entscheiden
spider_reject_node(node_id=django["id"],  issuer="claude-agent-1", reason="Zu monolithisch für Microservice-Architektur")
spider_accept_node(node_id=fastapi["id"], issuer="claude-agent-1", reason="Beste Performance, async-native, OpenAPI built-in")

# 6. Fortschritt prüfen
stats = spider_get_tree_stats()
# → {"completion_percentage": 33.3, ...}

# 7. Weitere Bereiche bearbeiten bis reifegrad = 1.0 ...
```

---

## Support & Dokumentation

- Konfiguration: `.spider/.env` (`SPIDER_DB_PATH`, optional `SPIDER_BASE_URL`)
- Visualisierung: `./spider-viz.ps1` / `./spider-viz.sh` (Port wird beim Start ausgegeben)
- MCP-Server: `.mcp.json` → `python -m spider.mcp_server`
- Read-only Zugriff für Subagents: `from spider_tools import spider_ro`
- Framework als Package installiert (`spider`); API-Docs nur bei laufendem
  `python -m spider.server.main` unter `/docs`

