# Changelog

Alle nennenswerten Änderungen an Spider. Format lose angelehnt an *Keep a Changelog*.

## [0.1.0] – 2026-06-28

Erste pip-installierbare Version mit Projekt-Onboarding (`spider-init`).

### Hinzugefügt
- **pip-Paketierung** (`pyproject.toml`): Repo-Root ist das `spider`-Package
  (`package-dir = {spider = "."}`). Dist-Name `spider` (== Import-Name). Optionales
  `mcp`-Extra: `pip install -e ".[mcp]"`. Console-Script `spider-init`.
- **`spider-init <projekt>`** (`init.py`): macht ein beliebiges Projekt Spider-fähig.
  Erzeugt `.spider/.env`, `AGENTS.md` (idempotenter Marker-Block), `spider_tools.py`-Shim
  (`spider` + read-only `spider_ro`), `.mcp.json`, `.claude/commands/spider-{plan,execute}.md`,
  `.spider/work_agent.md`, `spider-viz.ps1/.sh`.
  - `--force` / `--upgrade`: aktualisiert generierte Dateien in bestehenden Projekten,
    ohne Nutzerdaten (`.spider/.env`, `.spider/spider.db`) anzutasten.
- **Zentrale Konfiguration** (`config.py`): `load_project_env` lädt `.spider/.env`
  (aufwärts ab CWD), autoritativ (`override=True`), relativer `SPIDER_DB_PATH` wird relativ
  zur Projektwurzel aufgelöst. Alle Einstiegspunkte funneln hindurch → keine Hijacks durch
  globale Variablen mehr.
- **Direkt-DB-Tools** (`tools/local_tools.py`): `LocalSpiderTools` ruft die Logik aus
  `server/api.py` in-process auf (kein HTTP, schnell, tokenarm). `ReadOnlySpiderTools`
  (Schreib-Methoden werfen `ReadOnlyViolation`) für read-only Subagents.
- **MCP-Server** (`mcp_server.py`): stdio-Server (FastMCP), exposed `spider_*`-Tools auf
  Direkt-DB-Basis. `.mcp.json` startet ihn automatisch in MCP-Clients (z.B. Claude Code).
- **Visualisierungs-Start** (`launch.py`): wählt einen freien Port zur Laufzeit, gibt die URL
  aus; mehrere Projekte laufen kollisionsfrei parallel.
- **Zwei-Phasen-Workflow** (Slash-Commands): `/spider-plan` (Planungs-Agent, baut den Baum bis
  `root.reifegrad == 1.0`) und `/spider-execute` (Orchestrator mit exklusivem Schreibzugriff,
  startet read-only Subagents via `.spider/work_agent.md`).
- **Netzwerk-Switch**: `SPIDER_BASE_URL` setzen → Shim/MCP nutzen den HTTP-`SpiderTools`-Client
  gegen `server.main`; dieselbe DB darunter, keine Migration.

### Geändert
- `tools/agent_tools.py`-Konstruktor bleibt parametrisierbar (`base_url`); HTTP-Pfad unverändert.
- Standard-DB-Pfad pro Projekt: `.spider/spider.db`.
- Doku (`README.md`, `templates/AGENTS.md`, `CLAUDE.md`) auf Direkt-DB, `.env`, MCP und die
  Slash-Commands aktualisiert.

### Behoben
- `db/seed.py`: absolute Imports (`spider.db.*` statt `db.*`) → `python -m spider.db.seed` läuft.
- `init.py`: frisch geschriebene `AGENTS.md` wird in Marker gewrappt → erneute Läufe sind
  idempotent (kein doppelter Block).
