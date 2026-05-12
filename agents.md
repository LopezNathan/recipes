## Agents for the `recipes` project

This document lists recommended automated "agents" (small services or scripts) mapped to the current repository layout and behaviour we discussed. Each agent includes a short responsibility summary, a compact contract (inputs/outputs/error modes), triggers, important files, and quick run/observability notes.

Assumptions
- The backend is a Python web API (there is a `main.py` and frontend expects `http://localhost:8000`). I assume a typical dev run uses `uvicorn` or `python -m` to start the API. If this is not correct, adjust the "how to run" commands below.
- The repository contains the frontend static UI in `index.html` and Python modules for DB and parsing (`db.py`, `database.py`, `recipe_parser.py`, `scraper.py`, `models.py`).

Checklist (requirements from the request)
- Create `agents.md` in repo — Done
- Describe agents based on repository and prior discussion — Done
- Include contracts, triggers, files, run notes, and next steps — Done

------------------------------

### 1) Importer Agent (import-agent)
- Responsibility: Accept an external recipe URL, delegate to the scraper/parser, and create a recipe record.
- Trigger: HTTP POST to `/import` (from UI `importBtn`) or scheduled batch import.
- Inputs: { url: string }
- Outputs: recipe JSON (created) or error object { detail }
- Error modes: network timeouts, unsupported site, parse failure, duplicate recipe
- Files: `scraper.py`, `recipe_parser.py`, `main.py` (import endpoint)
- Contract (happy path): valid URL -> 200 + recipe JSON
- Observability: log URL, start/end timestamps, parse result size, HTTP status
- Quick run notes: backend must be reachable; follow existing import endpoint in `main.py`.

### 2) Paste / Parser Agent (paste-agent)
- Responsibility: Parse pasted JSON or Markdown recipes and validate/normalize before inserting to DB.
- Trigger: HTTP POST to `/paste` (UI `pasteBtn`), or CLI invocation for bulk ingest.
- Inputs: { content: string } (markdown or JSON)
- Outputs: recipe JSON (created) or validation errors
- Error modes: invalid JSON/markdown, missing required fields (title/instructions), ambiguous ingredients
- Files: `recipe_parser.py`, `main.py`
- Contract: return 201 + created recipe or 400 + error detail

### 3) Scraper Agent (scraper-agent)
- Responsibility: Low-level site scraping for many sources. Extract raw recipe content and metadata.
- Trigger: Called by Importer Agent or run as worker for queued jobs.
- Inputs: URL
- Outputs: raw recipe payload (title, ingredients, instructions, prep_time, cook_time, image_url)
- Error modes: site layout changes, rate limits, captchas
- Files: `scraper.py`
- Notes: add retries, per-domain rate limits, caching of last-scrape timestamp.

### 4) Parser / Normalizer Agent (parser-agent)
- Responsibility: Convert raw scraped text into canonical recipe structure and ingredient objects.
- Trigger: Called by Scraper Agent or Paste Agent after obtaining raw text.
- Inputs: raw recipe payload
- Outputs: normalized recipe object ready for DB insertion
- Files: `recipe_parser.py`
- Contract: produce { title, ingredients[], instructions, prep_time?, cook_time?, image_url? }
- Edge: support both list/string ingredients; preserve unknown fields as metadata.

### 5) Database Agent (db-agent)
- Responsibility: CRUD operations against persistent storage (SQLite/DB). Ensure migrations/locking.
- Trigger: Called by API endpoints (create/read/update/delete) or maintenance scripts.
- Inputs: recipe objects or query params
- Outputs: success/failure & records
- Files: `db.py`, `database.py`, `models.py`, `recipes.db`
- Contract: consistent schema — expose create_recipe, list_recipes, get_recipe, update, delete
- Notes: add tests around race conditions and large payloads. Keep DB connections short-lived for CLI/worker use.

### 6) Frontend Agent (ui-agent)
- Responsibility: The static UI (`index.html`) that calls backend endpoints and provides local interactivity (cooking mode, timers).
- Trigger: User interactions (create, import, paste, edit, delete, open cooking mode)
- Inputs/Outputs: HTTP requests to API endpoints, localStorage theme
- Files: `index.html`
- Notes: The UI expects a JSON API at `http://localhost:8000`. If CORS is necessary, backend should allow the static host origin.

### 7) Test Agent (test-agent)
- Responsibility: Run unit/functional tests on changes. Provide a fast feedback loop.
- Trigger: Local dev `pytest` or CI on push/PR
- Inputs: test files under `tests/`
- Outputs: pass/fail, coverage summary
- Files: `tests/`, `pytest.ini`
- Contract: run `pytest -q` and return non-zero exit code on failure

### 8) CI / Lint Agent (ci-agent)
- Responsibility: On push/PR run linting, tests, and optionally package build.
- Trigger: GitHub Actions / other CI on push/pull_request
- Inputs: repo + branch
- Outputs: status checks
- Notes: minimal pipeline: 1) install Python deps from `requirements.txt`, 2) run linter (flake8/ruff) if added, 3) run `pytest`.

------------------------------

Contracts / Tiny API summary (2–4 bullets for each important endpoint)
- POST /recipes
  - Input: JSON recipe (title, ingredients, instructions, optional times/image)
  - Output: 201 + recipe JSON or 400 + validation
- GET /recipes?skip=&limit=&search=&ingredient=
  - Input: query params
  - Output: { total: int, recipes: [...] }
- POST /import
  - Input: { url }
  - Output: created recipe or error
- POST /paste
  - Input: { content }
  - Output: created recipe or error

Edge cases to watch
- Ingredients sometimes strings vs objects — persist both but normalize views to show name and optional quantity.
- Duplicate detection — same title + similar ingredients should be flagged/merged.
- Large instructions or binary images — strip/limit sizes on write and surface a clear error.

Quick run / dev notes
- (Assuming a Python backend) Create a venv, install requirements, start API and open `index.html` in a browser.

Example commands (adjust if your app starts differently):
```bash
# create venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run backend (if FastAPI / uvicorn-based)
# from repo root — may be `main:app` or `app:app` depending on file contents
uvicorn main:app --reload --port 8000
```

Observability & logs
- Log every external import attempt with URL and outcome.
- Scraper and parser should emit structured logs with a request-id to trace an import across components.

Next steps / small improvements (low-risk)
- Add a small `scripts/` folder with CLI helpers to run import/paste locally for debugging.
- Add basic GitHub Actions workflow to run tests on PRs (lint + pytest).
- Add minimal health endpoint `/health` returning 200 to make the UI/CI checks quick.

Contact / Notes
- This file is intentionally prescriptive but conservative — if you want, I can open a small PR that adds a simple `scripts/import_cli.py` and a GH action to run tests.
