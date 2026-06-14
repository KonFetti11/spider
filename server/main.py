"""
Spider Framework – Einstiegspunkt für den HTTP-Server.

Startet den FastAPI-Server mit Uvicorn.
Port und Host können per .env oder Umgebungsvariablen konfiguriert werden.

Verwendung:
    python -m spider.server.main
    # oder:
    uvicorn spider.server.api:app --reload --port 8765
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Projektwurzel im Suchpfad
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optional

import uvicorn
from spider.server.api import app  # noqa: F401 – App wird exportiert

HOST = os.environ.get("SPIDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("SPIDER_PORT", "8765"))
RELOAD = os.environ.get("SPIDER_RELOAD", "false").lower() == "true"
LOG_LEVEL = os.environ.get("SPIDER_LOG_LEVEL", "info")


def main():
    print(f"Spider API Server startet auf http://{HOST}:{PORT}")
    print(f"Dokumentation: http://{HOST}:{PORT}/docs")
    p = os.environ.get('SPIDER_DB_PATH', 'data/spider.db')
    print(f"Datenbank: {p}")
    uvicorn.run(
        "spider.server.api:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL,
    )


if __name__ == "__main__":
    main()

