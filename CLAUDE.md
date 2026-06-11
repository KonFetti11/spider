# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Primary reference

`AGENTS.md` is the authoritative build spec for this project (data model, implementation
order, API conventions, reifegrad semantics, visualization requirements). Read it before
making structural changes. `templates/AGENTS.md` is a *different* file — it ships to target
projects as agent usage instructions, not guidance for this repo.

Most prose in this repo is German; keep new docstrings/comments consistent with surrounding code.

## What this is

Spider is a POC framework for AI-agent decision traceability. An agent builds a persistent
**planning tree** where every decision/alternative/rejection is a `Node` with reasoning.
`reifegrad` (maturity, 0.0–1.0) propagates up the tree; `root.reifegrad == 1.0` means all
decisions are made. Every write produces an immutable `Action` audit-log entry.

## Commands

Run all module commands from the **parent directory** of this repo (e.g. `PycharmProjects/`),
because all imports are absolute (`from spider.db...`) and the repo is the `spider` package itself.

```bash
pip install -r spider/requirements.txt   # fastapi, uvicorn, pydantic, python-dotenv
python -m spider.db.seed                  # load demo data into data/spider.db
python -m spider.server.main              # API server, port 8765 (docs at /docs)
python -m spider.visualization.serve      # viz server, port 8766
```

Tests: `test_poc.py` is a standalone end-to-end script (urllib, not pytest). It requires
**both servers running and seed data loaded** — it hits the live HTTP API. Run with
`python spider/test_poc.py`. There is no configured linter or unit-test suite; the 7 checks
in `test_poc.py` are the acceptance criteria.

## Architecture invariants

These constraints span multiple files and are easy to violate:

- **`confidence` and `reifegrad` are computed, never written via API or `update_node`.**
  `update_node` drops them from any update dict (`protected` set in `db/database.py`). They
  are derived in `calculate_reifegrad` / `calculate_confidence` and persisted only by the
  recalculation logic.
- **Every write triggers `_recalculate_ancestors`**, which walks `parentId` to the root and
  recomputes each ancestor. An internal node's reifegrad = average of its children; a leaf =
  `1.0` if accepted (`acceptionDate` set) OR rejected (`active=False`), else `0.0`.
- **`accept` and `reject` are thin wrappers over `update_node`** (`db/database.py`), so they
  inherit audit-logging and recalculation automatically. Add new state transitions the same
  way rather than writing rows directly.
- **`Action.date` must equal the `Node.lastChange` of the same operation** (both `now_ms()`).
  This timestamp identity is what makes the audit trail temporally reconstructable.
- **All timestamps are Unix milliseconds (int).**
- **DB access goes through the `get_db()` singleton** (`db/database.py`), which honors
  `SPIDER_DB_PATH`. Don't instantiate `Database` directly in server/tool code.

## Layout

`db/` data layer (models, SQLite + calc logic, seed) → `server/` FastAPI REST API →
`tools/` agent-facing HTTP wrappers (`SpiderTools` + function-calling JSON schemas;
**stdlib `urllib` only**, no external HTTP deps) → `visualization/` D3.js tree viewer.
The dependency direction is db ← server ← tools/viz (over HTTP).
