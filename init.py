"""
Spider Framework – Projekt-Initialisierung (`spider-init`).

Macht ein beliebiges Projekt in einem Schritt Spider-fähig:

    spider-init <projektpfad>        # oder:  python -m spider.init <projektpfad>

Erzeugt im Zielprojekt:
  - .spider/                  Verzeichnis für die projekteigene SQLite-DB (lazy angelegt)
  - AGENTS.md                 Agent-Anweisungen (neu) bzw. markierter Block (angehängt)
  - spider_tools.py           Tool-Shim mit Auto-Detect (Direkt-DB lokal / HTTP via SPIDER_BASE_URL)
  - spider-viz.ps1 / .sh      Start-Helper für den Visualisierungsserver (dynamischer Port)

Der Spider-Code selbst bleibt zentral (pip-Installation) – im Projekt landet nur Konfiguration.
"""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

# Marker, mit denen der angehängte Spider-Block in einer bestehenden AGENTS.md
# eindeutig erkannt wird (Idempotenz).
SPIDER_BLOCK_START = "<!-- spider:start -->"
SPIDER_BLOCK_END = "<!-- spider:end -->"


# ---------------------------------------------------------------------------
# Generierte Dateiinhalte
# ---------------------------------------------------------------------------

SHIM_CONTENT = '''"""
Spider-Tool-Zugang für dieses Projekt – automatisch erzeugt von `spider-init`.

Verwendung (im Agent / in Skripten):
    from spider_tools import spider
    spider.get_tree_stats()
    spider.create_node(name="...", reasoning="...", summary="...", issuer="...")

Konfiguration kommt aus `.spider/.env` (SPIDER_DB_PATH, optional SPIDER_BASE_URL).
Zugriffsmodus (Auto-Detect):
  - Standard: Direkt-DB (schnell, tokenarm, kein Server nötig). Schreibt/liest die
    in `.spider/.env` konfigurierte Projekt-DB (Standard: `.spider/spider.db`).
  - Netzwerk: Ist SPIDER_BASE_URL gesetzt (in `.spider/.env` oder als Umgebungs-
    variable), wird der laufende Spider-HTTP-Server genutzt. Dieselbe DB darunter.

Zwei Handles:
  - `spider`     – voller Zugriff (Lesen + Schreiben). Für den Orchestrator / die Planung.
  - `spider_ro`  – read-only (Schreib-Methoden werfen). Für Subagents (`/spider-execute`).
"""

import os
import pathlib

# Projekt-.env laden (.spider/.env), verankert am Ort dieser Datei – unabhängig vom CWD.
# Die .env ist autoritativ und setzt SPIDER_DB_PATH; eine globale Variable kann das
# Projekt damit nicht mehr kapern.
from spider.config import load_project_env
load_project_env(pathlib.Path(__file__).resolve().parent)

_base_url = os.environ.get("SPIDER_BASE_URL")
if _base_url:
    from spider.tools.agent_tools import SpiderTools
    spider = SpiderTools(base_url=_base_url)
else:
    from spider.tools.local_tools import LocalSpiderTools
    spider = LocalSpiderTools()

# Read-only Sicht für Subagents (Schreib-Methoden werfen ReadOnlyViolation).
from spider.tools.local_tools import ReadOnlySpiderTools
spider_ro = ReadOnlySpiderTools(spider)
'''

MCP_JSON_CONTENT = """{
  "mcpServers": {
    "spider": {
      "command": "python",
      "args": ["-m", "spider.mcp_server"]
    }
  }
}
"""

ENV_CONTENT = """# Spider-Konfiguration – erzeugt von spider-init.
# Diese Datei ist die zentrale Konfigurationsquelle für dieses Projekt.

# Pfad zur Projekt-Datenbank (relativ zur Projektwurzel, dem Verzeichnis mit .spider/).
SPIDER_DB_PATH=.spider/spider.db

# Optionaler Netzwerkzugriff statt Direkt-DB (Shim schaltet automatisch um):
# SPIDER_BASE_URL=http://127.0.0.1:8765

# Optionale feste Viz-Ports (sonst wird beim Start ein freier Port gewählt):
# SPIDER_VIZ_HOST=127.0.0.1
# SPIDER_VIZ_PORT=8766
"""

VIZ_PS1_CONTENT = """# Spider-Visualisierung starten – automatisch erzeugt von spider-init.
# Waehlt einen freien Port und gibt die URL aus.
Set-Location -Path $PSScriptRoot
python -m spider.launch
"""

VIZ_SH_CONTENT = """#!/usr/bin/env bash
# Spider-Visualisierung starten – automatisch erzeugt von spider-init.
# Waehlt einen freien Port und gibt die URL aus.
cd "$(dirname "$0")" || exit 1
exec python -m spider.launch
"""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _read_template(relpath: str) -> str:
    """Liest eine Datei aus dem templates/-Verzeichnis des installierten Spider-Packages."""
    return resources.files("spider").joinpath(f"templates/{relpath}").read_text(encoding="utf-8")


def _emit(path: Path, content: str, force: bool = False) -> str:
    """Schreibt content. Existierende Dateien werden nur mit force=True überschrieben.
    Gibt 'erstellt' | 'aktualisiert' | 'unverändert' zurück."""
    existed = path.exists()
    if existed and not force:
        return "unverändert"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "aktualisiert" if existed else "erstellt"


def copy_agents(project_dir: Path) -> str:
    """
    Sorgt dafür, dass die Spider-Agent-Anweisungen im Projekt aktiv sind.

    - Keine AGENTS.md vorhanden  → Template als neue AGENTS.md schreiben.
    - AGENTS.md vorhanden        → markierten Spider-Block anhängen (idempotent).
    Gibt eine kurze Statusmeldung zurück.
    """
    template = _read_template("AGENTS.md")
    agents_path = project_dir / "AGENTS.md"
    block = f"{SPIDER_BLOCK_START}\n{template}\n{SPIDER_BLOCK_END}\n"

    if not agents_path.exists():
        # Auch frisch mit Markern schreiben → erneute Läufe erkennen den Block (idempotent).
        agents_path.write_text(block, encoding="utf-8")
        return "AGENTS.md erstellt."

    existing = agents_path.read_text(encoding="utf-8")
    if SPIDER_BLOCK_START in existing:
        return "AGENTS.md bereits Spider-fähig (Block vorhanden) – unverändert."

    agents_path.write_text(existing + "\n\n" + block, encoding="utf-8")
    return "AGENTS.md vorhanden – Spider-Block angehängt."


def write_env(project_dir: Path) -> str:
    # .env wird NIE überschrieben (enthält evtl. nutzerspezifische Konfiguration).
    return f".spider/.env {_emit(project_dir / '.spider' / '.env', ENV_CONTENT)} (zentrale Konfiguration)."


def write_shim(project_dir: Path, force: bool = False) -> str:
    return f"spider_tools.py {_emit(project_dir / 'spider_tools.py', SHIM_CONTENT, force)}."


def write_mcp_config(project_dir: Path, force: bool = False) -> str:
    return f".mcp.json {_emit(project_dir / '.mcp.json', MCP_JSON_CONTENT, force)} (MCP-Server)."


def write_commands(project_dir: Path, force: bool = False) -> str:
    cmd_dir = project_dir / ".claude" / "commands"
    parts = []
    for name in ("spider-plan.md", "spider-execute.md"):
        status = _emit(cmd_dir / name, _read_template(f"commands/{name}"), force)
        parts.append(f"/{name[:-3]} {status}")
    return "Slash-Commands: " + ", ".join(parts) + "."


def write_work_agent(project_dir: Path, force: bool = False) -> str:
    status = _emit(project_dir / ".spider" / "work_agent.md", _read_template("work_agent.md"), force)
    return f".spider/work_agent.md {status} (Subagent-Prompt)."


def write_viz_scripts(project_dir: Path, force: bool = False) -> str:
    ps1 = _emit(project_dir / "spider-viz.ps1", VIZ_PS1_CONTENT, force)
    sh_path = project_dir / "spider-viz.sh"
    sh = _emit(sh_path, VIZ_SH_CONTENT, force)
    if sh != "unverändert":
        try:
            sh_path.chmod(0o755)
        except OSError:
            pass
    return f"Viz-Start-Helper: spider-viz.ps1 {ps1}, spider-viz.sh {sh}."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="spider-init",
        description="Initialisiert ein Projekt für das Spider-Traceability-Framework.",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Zielprojekt-Verzeichnis (Standard: aktuelles Verzeichnis).",
    )
    parser.add_argument(
        "-f", "--force", "--upgrade",
        action="store_true",
        dest="force",
        help="Bestehendes Projekt upgraden: generierte Dateien (Shim, Commands, "
             "work_agent.md, .mcp.json, Viz-Skripte) überschreiben. "
             "Nutzerdaten (.spider/.env, .spider/spider.db) bleiben unangetastet.",
    )
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
        print(f"Projektverzeichnis erstellt: {project_dir}")
    elif not project_dir.is_dir():
        print(f"Fehler: {project_dir} ist kein Verzeichnis.", file=sys.stderr)
        return 1

    (project_dir / ".spider").mkdir(exist_ok=True)

    results = [
        write_env(project_dir),
        copy_agents(project_dir),
        write_shim(project_dir, args.force),
        write_mcp_config(project_dir, args.force),
        write_commands(project_dir, args.force),
        write_work_agent(project_dir, args.force),
        write_viz_scripts(project_dir, args.force),
    ]

    verb = "aktualisiert (--force)" if args.force else "initialisiert"
    print(f"\nSpider in Projekt {verb}: {project_dir}")
    print("  .spider/                  (eigene Datenbank, wird beim ersten Schreibzugriff angelegt)")
    for r in results:
        print(f"  {r}")

    print("\nNächste Schritte:")
    print("  1) Native MCP-Tools (Claude Code u.a.): MCP-SDK installieren")
    print('       pip install "spider[mcp]"   (bzw. im Repo:  pip install -e ".[mcp]")')
    print("     .mcp.json ist erzeugt; Claude Code beim Projektöffnen den Server bestätigen.")
    print("  2) Alternativ ohne MCP – Tool per Python (kein Server nötig):")
    print("       from spider_tools import spider")
    print("       spider.get_tree_stats()")
    print("  3) Slash-Commands in Claude Code:")
    print("       /spider-plan     – Entscheidungsbaum aufbauen (Planungsphase)")
    print("       /spider-execute  – Umsetzen via read-only Subagents (Ausführungsphase)")
    print("  4) Visualisierung öffnen:")
    print("       ./spider-viz.ps1   (Windows)   bzw.   ./spider-viz.sh   (Linux/macOS)")
    print("  5) Konfiguration: .spider/.env (SPIDER_DB_PATH; optional SPIDER_BASE_URL")
    print("     für Netzwerkzugriff via `python -m spider.server.main`).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
