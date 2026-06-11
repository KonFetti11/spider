"""
Spider Framework – Visualisierungs-Server.

Liefert die interaktive D3.js-Baumvisualisierung aus und stellt
die Baumdaten als JSON-API bereit.

Routen:
    GET /          → Interaktive D3.js-Baumansicht (HTML)
    GET /api/tree  → Baumdaten als JSON (von D3.js konsumiert)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from spider.db.database import get_db

app = FastAPI(title="Spider Visualizer", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# HTML wird direkt aus der Datei gelesen
_HTML_PATH = Path(__file__).parent / "tree.html"


@app.get("/", response_class=HTMLResponse)
def serve_visualizer():
    """Liefert die interaktive Baumvisualisierung."""
    if _HTML_PATH.exists():
        return HTMLResponse(content=_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>tree.html nicht gefunden</h1>", status_code=404)


@app.get("/api/tree")
def get_tree_data():
    """
    Gibt alle Nodes als flache Liste zurück.
    Wird von D3.js zur Visualisierung konsumiert.
    """
    db = get_db()
    return JSONResponse(content=db.get_tree())


@app.get("/api/tree/nested")
def get_tree_nested():
    """Verschachtelter Baum für D3.js hierarchy-Layout."""
    db = get_db()
    nested = db.get_tree_nested()
    # D3.js erwartet einen einzelnen Root-Knoten
    if len(nested) == 1:
        return JSONResponse(content=nested[0])
    # Mehrere Roots: synthetischer Root
    return JSONResponse(content={
        "id": "__synthetic_root__",
        "name": "Spider",
        "active": True,
        "status": "in_progress",
        "confidence": 0.0,
        "reifegrad": sum(n.get("reifegrad", 0) for n in nested) / len(nested) if nested else 0,
        "children": nested,
    })


if __name__ == "__main__":
    import os
    import uvicorn
    host = os.environ.get("SPIDER_VIZ_HOST", "127.0.0.1")
    port = int(os.environ.get("SPIDER_VIZ_PORT", "8766"))
    print(f"Spider Visualizer: http://{host}:{port}")
    uvicorn.run("spider.visualization.serve:app", host=host, port=port, reload=False)

