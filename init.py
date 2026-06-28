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

Zugriffsmodus (Auto-Detect):
  - Standard: Direkt-DB (schnell, tokenarm, kein Server nötig). Schreibt/liest
    `<dieses Projekt>/.spider/spider.db`.
  - Netzwerk: Ist die Umgebungsvariable SPIDER_BASE_URL gesetzt (z.B.
    http://host:8765), wird stattdessen der laufende Spider-HTTP-Server genutzt.
    Dieselbe Datenbank darunter – keine Migration nötig.
"""

import os
import pathlib

# Projekt-DB verbindlich festlegen, BEVOR das Spider-Package initialisiert wird.
# Bewusst harte Zuweisung (kein setdefault): so nutzt dieses Projekt immer seine
# eigene DB, selbst wenn global eine SPIDER_DB_PATH-Variable gesetzt ist.
# (Im Netzwerkmodus via SPIDER_BASE_URL ist dieser Pfad ohnehin unbenutzt.)
os.environ["SPIDER_DB_PATH"] = str(
    pathlib.Path(__file__).resolve().parent / ".spider" / "spider.db"
)

_base_url = os.environ.get("SPIDER_BASE_URL")
if _base_url:
    from spider.tools.agent_tools import SpiderTools
    spider = SpiderTools(base_url=_base_url)
else:
    from spider.tools.local_tools import LocalSpiderTools
    spider = LocalSpiderTools()
'''

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

def _read_template_agents() -> str:
    """Liest templates/AGENTS.md aus dem installierten Spider-Package."""
    return resources.files("spider").joinpath("templates/AGENTS.md").read_text(encoding="utf-8")


def _write_if_absent(path: Path, content: str) -> bool:
    """Schreibt content nur, wenn die Datei noch nicht existiert. Gibt True bei Schreibvorgang."""
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def copy_agents(project_dir: Path) -> str:
    """
    Sorgt dafür, dass die Spider-Agent-Anweisungen im Projekt aktiv sind.

    - Keine AGENTS.md vorhanden  → Template als neue AGENTS.md schreiben.
    - AGENTS.md vorhanden        → markierten Spider-Block anhängen (idempotent).
    Gibt eine kurze Statusmeldung zurück.
    """
    template = _read_template_agents()
    agents_path = project_dir / "AGENTS.md"

    if not agents_path.exists():
        agents_path.write_text(template, encoding="utf-8")
        return "AGENTS.md erstellt."

    existing = agents_path.read_text(encoding="utf-8")
    if SPIDER_BLOCK_START in existing:
        return "AGENTS.md bereits Spider-fähig (Block vorhanden) – unverändert."

    block = f"\n\n{SPIDER_BLOCK_START}\n{template}\n{SPIDER_BLOCK_END}\n"
    agents_path.write_text(existing + block, encoding="utf-8")
    return "AGENTS.md vorhanden – Spider-Block angehängt."


def write_shim(project_dir: Path) -> str:
    if _write_if_absent(project_dir / "spider_tools.py", SHIM_CONTENT):
        return "spider_tools.py erstellt."
    return "spider_tools.py existiert bereits – unverändert."


def write_viz_scripts(project_dir: Path) -> str:
    msgs = []
    if _write_if_absent(project_dir / "spider-viz.ps1", VIZ_PS1_CONTENT):
        msgs.append("spider-viz.ps1")
    sh_path = project_dir / "spider-viz.sh"
    if _write_if_absent(sh_path, VIZ_SH_CONTENT):
        try:
            sh_path.chmod(0o755)
        except OSError:
            pass
        msgs.append("spider-viz.sh")
    if msgs:
        return f"Viz-Start-Helper erstellt: {', '.join(msgs)}."
    return "Viz-Start-Helper existieren bereits – unverändert."


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
        copy_agents(project_dir),
        write_shim(project_dir),
        write_viz_scripts(project_dir),
    ]

    print(f"\nSpider in Projekt initialisiert: {project_dir}")
    print("  .spider/                  (eigene Datenbank, wird beim ersten Schreibzugriff angelegt)")
    for r in results:
        print(f"  {r}")

    print("\nNächste Schritte:")
    print("  1) Spider als Tool nutzen (kein Server nötig):")
    print("       from spider_tools import spider")
    print("       spider.get_tree_stats()")
    print("  2) Visualisierung öffnen:")
    print("       ./spider-viz.ps1   (Windows)   bzw.   ./spider-viz.sh   (Linux/macOS)")
    print("  3) Optional Netzwerkzugriff: Umgebungsvariable SPIDER_BASE_URL setzen")
    print("     (z.B. http://127.0.0.1:8765) und `python -m spider.server.main` starten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
