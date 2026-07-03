# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Before committing

Always update `README.md` to reflect any new features, changed behavior, or removed functionality before creating a commit.

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
- `app/models.py` — Pydantic models for API request/response, using schema.org Recipe field names (`recipeIngredient`, `prepTime`, `recipeYield`, …). Ingredients are plain strings (`list[str]`, e.g. `"2 cups flour"`) — there is no structured `Ingredient` model.

### Import / paste pipeline
`POST /import` → `app/scraper.py:scrape_recipe()` (uses `recipe-scrapers` library, 900+ sites) → `RecipeCreate` → `db.create()`

`POST /paste` → `app/recipe_parser.py:parse_recipe_content()` (auto-detects HTML with schema.org microdata, then JSON, then markdown) → `RecipeCreate` → `db.create()`

`recipe_parser.py:_parse_html_ingredient()` extracts flat ingredient strings from HTML exports (e.g. Paprika), handling quantity/unit splitting and skipping section headers (`_is_section_header()`).

`scrape_recipe()` runs the synchronous `recipe-scrapers` fetch via `asyncio.to_thread()` — keep it off the event loop if you touch it.

### Frontend
`index.html` is a self-contained single-file SPA (no build step). It talks to whichever API the page is served from. Key modes: recipe list view, recipe detail view, and Cooking Mode (step-by-step with multi-timer support). Write tabs (Create, Import, Paste) are hidden on the public app via the `/app-mode` response.

Recipe data is untrusted (scraped from third-party sites / pasted): any value interpolated into an `innerHTML` template in `app.js` must go through `escapeHtml()` (defined at the top of the file). Plain-text nodes should use `textContent` instead.

Key frontend components:
- **Filters panel** — `#filterToggleBtn` / `#filterPanel` (collapsible); `toggleFilterPanel()` in `app.js`. Filters: ingredient text input + category/cuisine/keyword selects. Selects are hidden until recipes with those fields exist.
- **Recipe tags** — `.recipe-tags` / `.recipe-tag` rendered in Cooking Mode and detail views. Tag variants: `.recipe-tag--category`, `.recipe-tag--cuisine`.
- **Grocery list** — `.grocery-toolbar` contains `#groceryCustomInput`, `.btn-primary` (Add), and `.grocery-clear-btns` wrapper div holding the two clear buttons. The wrapper exists so mobile CSS can give the input more space (via `1fr auto` grid) while keeping clear buttons equal-width (via `flex: 1` inside the wrapper).

### CSS architecture note
`static/style.css` has a **file-order dependency**: the grocery-list mobile overrides (`@media (max-width: 768px)`) live at the **very end** of the file, after the base `.grocery-toolbar` styles (~line 1560). If you add grocery mobile styles to the earlier 768px block (line ~1248), the base `display: flex` rule — which comes later — will win over `display: grid` due to cascade order. Always add new grocery mobile overrides at the bottom.

### Tests
Tests in `tests/` use `conftest.py` fixtures that connect to a real PostgreSQL test database (`TEST_DATABASE_URL` from `.env`). Each test drops and recreates the `recipes` table for isolation. All tests are async (`asyncio_mode = auto` in `pytest.ini`). The local Postgres container (`make up`) must be running before running tests.
