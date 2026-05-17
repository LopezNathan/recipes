# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (required before running anything)
source venv/bin/activate

# Run the full test suite
pytest tests/ -v

# Run a single test file
pytest tests/test_recipes_crud.py -v

# Run a single test by name
pytest tests/test_recipes_crud.py::test_create_recipe -v

# Start local dev server (full read/write on port 8000)
uvicorn main:app --reload

# Start public (read-only) API on port 8000
uvicorn main:public_app --port 8000 --reload

# Start private (read/write) API on port 8001
uvicorn main:private_app --port 8001 --reload
```

## Architecture

### Dual-API design
`main.py` exposes two FastAPI app instances — `public_app` (read-only, port 8000) and `private_app` (read/write, port 8001). Both share the same read routes, registered via `setup_read_only_routes()`. Write routes (`POST /recipes`, `PUT`, `DELETE`, `POST /import`, `POST /paste`) are registered only on `private_app`. `app` is an alias for `private_app` used by the test suite.

A `GET /app-mode` endpoint returns `{"mode": "public"}` or `{"mode": "private"}` so the frontend can show/hide write UI without port-sniffing. The frontend uses a relative `API_URL = ''` so it always hits whichever app served it.

### Database
- `app/database.py` — asyncpg connection pool setup. Handles Neon SSL by stripping `sslmode` from the DSN and passing an `ssl.create_default_context()` explicitly. Runs `CREATE TABLE IF NOT EXISTS` on startup (no migrations tool).
- `app/db.py` — `RecipeDatabase` ABC and `PostgresRecipeDatabase` concrete implementation. Route handlers receive a connection via FastAPI dependency injection (`get_recipe_db`), never touching the pool directly.
- `app/models.py` — Pydantic models for API request/response. `Ingredient` has optional `quantity`. `ingredients` fields accept `Union[str, Ingredient]` lists everywhere.

### Import / paste pipeline
`POST /import` → `app/scraper.py:scrape_recipe()` (uses `recipe-scrapers` library, 900+ sites) → `RecipeCreate` → `db.create()`

`POST /paste` → `app/recipe_parser.py:parse_recipe_content()` (auto-detects JSON vs markdown) → `RecipeCreate` → `db.create()`

`recipe_parser.py:parse_ingredient()` handles quantity extraction from raw strings, including unicode fractions (½ ¼ ⅓) and bullet-point formats (`name • qty`).

### Frontend
`index.html` is a self-contained single-file SPA (no build step). It talks to whichever API the page is served from. Key modes: recipe list view, recipe detail view, and Cooking Mode (step-by-step with multi-timer support). Write tabs (Create, Import, Paste) are hidden on the public app via the `/app-mode` response.

### Tests
Tests in `tests/` use `conftest.py` fixtures that connect to a real PostgreSQL test database (`TEST_DATABASE_URL` from `.env`). Each test drops and recreates the `recipes` table for isolation. All tests are async (`asyncio_mode = auto` in `pytest.ini`). The local Postgres container (`make up`) must be running before running tests.
