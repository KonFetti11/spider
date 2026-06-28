"""
Spider Framework – Start-Helper für die Visualisierung (`python -m spider.launch`).

Wird von den projekteigenen Skripten `spider-viz.ps1` / `spider-viz.sh` aufgerufen.
Ablauf:
  1. Bindet die Projekt-DB (`<cwd>/.spider/spider.db`) über SPIDER_DB_PATH.
  2. Sucht einen freien TCP-Port am laufenden System (kollidiert nie mit anderen
     parallel laufenden Spider-Projekten – jedes bekommt seinen eigenen Port).
  3. Gibt die URL aus und startet den Visualisierungsserver.

Die Isolation mehrerer Projekte ergibt sich aus Port → Prozess → SPIDER_DB_PATH:
Die zentrale tree.html fetcht relativ `/api/tree` und trifft damit immer den Server,
der sie ausgeliefert hat – also dessen Projekt-Datenbank. Es wird nichts ins Projekt kopiert.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path


def find_free_port() -> int:
    """Vom Betriebssystem einen freien Port zuteilen lassen."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    project_dir = Path.cwd()
    db_path = project_dir / ".spider" / "spider.db"

    # Projekt-DB + Viz-Port für die Server-Prozessumgebung setzen.
    os.environ["SPIDER_DB_PATH"] = str(db_path)
    host = os.environ.get("SPIDER_VIZ_HOST", "127.0.0.1")
    port = int(os.environ.get("SPIDER_VIZ_PORT") or find_free_port())
    os.environ["SPIDER_VIZ_PORT"] = str(port)

    import uvicorn

    url = f"http://{host}:{port}"
    print(f"Spider-Visualisierung für {project_dir}", flush=True)
    print(f"  Datenbank: {db_path}", flush=True)
    print(f"  Öffne:     {url}", flush=True)
    uvicorn.run("spider.visualization.serve:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
