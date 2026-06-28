"""
Spider Framework – zentrale Konfiguration / .env-Laden.

Sorgt dafür, dass alle SPIDER_*-Einstellungen (insbesondere SPIDER_DB_PATH)
**konsistent aus der Projekt-.env** kommen. Jeder Einstiegspunkt (Tool-Shim,
`launch.py`, `server.main`, `db.seed`, `db.database.get_db`) ruft `load_project_env()`
auf, bevor er Konfiguration liest.

Konventionen:
  - Pro Projekt liegt die Konfiguration in `<projekt>/.spider/.env`
    (isoliert von einer evtl. vorhandenen App-eigenen `.env` im Projektwurzelordner).
  - Gesucht wird ab einem Startverzeichnis aufwärts: zuerst `.spider/.env`,
    ersatzweise `.env` im selben Verzeichnis.
  - Die `.env` ist **autoritativ** (`override=True`): ihre Werte gewinnen gegenüber
    bereits gesetzten Prozess-Umgebungsvariablen. Damit kann keine global gesetzte
    SPIDER_DB_PATH-Variable ein Projekt mehr „kapern". Schlüssel, die *nicht* in der
    `.env` stehen (z.B. ein per Shell gesetztes SPIDER_BASE_URL), bleiben unberührt.
  - Ein relativer SPIDER_DB_PATH wird relativ zur **Projektwurzel** (dem Verzeichnis,
    das `.spider/` enthält) zu einem absoluten Pfad aufgelöst.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_loaded = False


def find_project_env(start: Optional[Path] = None) -> Optional[Path]:
    """Sucht ab `start` (default: CWD) aufwärts die nächste Projekt-.env."""
    base = (Path(start) if start else Path.cwd()).resolve()
    for d in [base, *base.parents]:
        candidate = d / ".spider" / ".env"
        if candidate.is_file():
            return candidate
        candidate = d / ".env"
        if candidate.is_file():
            return candidate
    return None


def _parse_env(text: str) -> dict[str, str]:
    """Minimaler .env-Parser (KEY=VALUE, # Kommentare, optionale Quotes)."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            values[key] = val
    return values


def _project_root(env_path: Path) -> Path:
    """Projektwurzel = Verzeichnis, das `.spider/` enthält (bzw. .env-Verzeichnis)."""
    if env_path.parent.name == ".spider":
        return env_path.parent.parent
    return env_path.parent


def load_project_env(start: Optional[Path] = None, override: bool = True, force: bool = False) -> Optional[Path]:
    """
    Lädt die Projekt-.env in os.environ. Idempotent (nur einmal pro Prozess, außer force=True).
    Gibt den geladenen .env-Pfad zurück (oder None, wenn keine gefunden wurde).
    """
    global _loaded
    if _loaded and not force:
        return None
    _loaded = True

    env_path = find_project_env(start)
    if env_path is None:
        return None

    values = _parse_env(env_path.read_text(encoding="utf-8"))
    for key, val in values.items():
        if override or key not in os.environ:
            os.environ[key] = val

    # Relativen SPIDER_DB_PATH relativ zur Projektwurzel absolut machen (portabel).
    db_path = os.environ.get("SPIDER_DB_PATH")
    if db_path and not Path(db_path).is_absolute():
        os.environ["SPIDER_DB_PATH"] = str((_project_root(env_path) / db_path).resolve())

    return env_path
