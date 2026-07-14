"""FastAPI Recipe Application - Dual API Setup."""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import close_db, get_pool, init_db
from app.db import PostgresRecipeDatabase
from app.image_utils import validate_image_url
from app.models import (
    Recipe,
    RecipeCreate,
    RecipeImportRequest,
    RecipeListResponse,
    RecipePasteRequest,
    RecipeUpdate,
    SearchRequest,
)
from app.recipe_parser import parse_recipe_content
from app.scraper import scrape_recipe
from app.url_safety import is_public_http_url

BASE_DIR = Path(__file__).resolve().parent


def _compute_static_version() -> str:
    h = hashlib.md5()
    for name in ("static/style.css", "static/app.js"):
        p = BASE_DIR / name
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


STATIC_VERSION = _compute_static_version()

# Grocery-store search URL templates for the /shop redirect. Shop links go
# through our own domain so iOS never treats them as universal links: store
# apps (e.g. FreshDirect) intercept direct store URLs but drop the search
# term, while a same-origin link followed by a server-side redirect always
# stays in the browser, where the search works. Fixed templates keyed by
# store id (rather than a pass-through URL) avoid an open redirect.
SHOP_SEARCH_URLS = {
    "freshdirect": "https://www.freshdirect.com/search?search={q}",
    "heb": "https://www.heb.com/search?q={q}",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


# ============================================================================
# PUBLIC API (Read-only) - Port 8000
# ============================================================================
public_app = FastAPI(
    title="Recipe API - Public (Read-Only)",
    version="1.0.0",
    description="Public read-only recipe API. No authentication required.",
    lifespan=lifespan,
)

# Enable CORS for public API: read-only access from any origin, no credentials
public_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)
public_app.mount(
    "/static", StaticFiles(directory=BASE_DIR / "static"), name="static-public"
)


# ============================================================================
# PRIVATE API (Read/Write) - Port 8001
# ============================================================================
private_app = FastAPI(
    title="Recipe API - Private (Read/Write)",
    version="1.0.0",
    description="Private read/write recipe API. Access via Cloudflare tunnel only.",
    lifespan=lifespan,
)

# No CORS middleware on the private API: its frontend is served same-origin,
# so cross-origin browser access to the write endpoints is deliberately not enabled.
private_app.mount(
    "/static", StaticFiles(directory=BASE_DIR / "static"), name="static-private"
)

# Keep 'app' as alias for backward compatibility with testing
app = private_app


# Dependency to get database instance
async def get_recipe_db() -> PostgresRecipeDatabase:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield PostgresRecipeDatabase(conn)


# ============================================================================
# SHARED READ-ONLY ROUTES (on both public_app and private_app)
# ============================================================================


def setup_read_only_routes(fastapi_app: FastAPI, mode: str = "public"):
    """Register read-only routes on the given FastAPI app."""

    @fastapi_app.get("/app-mode")
    async def app_mode():
        return {"mode": mode}

    @fastapi_app.get("/health")
    async def health():
        """Liveness check: process is up. No dependencies touched."""
        return {"status": "ok"}

    @fastapi_app.get("/health/ready")
    async def health_ready():
        """Readiness check: verifies the database pool is reachable."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return {"status": "ready"}

    @fastapi_app.get("/shop")
    async def shop_redirect(
        store: str, q: str = Query(..., min_length=1, max_length=200)
    ):
        """Redirect to a grocery store's search page for the given term."""
        template = SHOP_SEARCH_URLS.get(store)
        if not template:
            raise HTTPException(status_code=404, detail="Unknown store")
        return RedirectResponse(url=template.format(q=quote(q)), status_code=302)

    @fastapi_app.get("/")
    async def root():
        html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace(
            'href="/static/style.css"', f'href="/static/style.css?v={STATIC_VERSION}"'
        )
        html = html.replace(
            'src="/static/app.js"', f'src="/static/app.js?v={STATIC_VERSION}"'
        )
        return HTMLResponse(content=html)

    @fastapi_app.get("/recipes", response_model=RecipeListResponse)
    async def list_recipes(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        search: str | None = None,
        ingredient: str | None = None,
        category: str | None = None,
        cuisine: str | None = None,
        keyword: str | None = None,
        sort_by: str = "date_published",
        db: PostgresRecipeDatabase = Depends(get_recipe_db),
    ):
        """
        List all recipes with optional filtering and pagination.

        Query parameters:
        - skip: Number of recipes to skip (for pagination)
        - limit: Maximum number of recipes to return
        - search: Search in title and description
        - ingredient: Filter by ingredient
        - category: Filter by category
        - cuisine: Filter by cuisine
        - keyword: Filter by keyword
        - sort_by: Sort field (date_published for newest first, anything else sorts by name)
        """
        recipes, total = await db.list_all(
            skip=skip,
            limit=limit,
            search=search,
            ingredient=ingredient,
            category=category,
            cuisine=cuisine,
            keyword=keyword,
            sort_by=sort_by,
        )

        return {
            "recipes": recipes,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @fastapi_app.get("/categories", response_model=list[str])
    async def list_categories(db: PostgresRecipeDatabase = Depends(get_recipe_db)):
        """Return all distinct recipe categories sorted alphabetically."""
        return await db.get_categories()

    @fastapi_app.get("/cuisines", response_model=list[str])
    async def list_cuisines(db: PostgresRecipeDatabase = Depends(get_recipe_db)):
        """Return all distinct recipe cuisines sorted alphabetically."""
        return await db.get_cuisines()

    @fastapi_app.get("/keywords", response_model=list[str])
    async def list_keywords(db: PostgresRecipeDatabase = Depends(get_recipe_db)):
        """Return all distinct recipe keywords sorted alphabetically."""
        return await db.get_keywords()

    @fastapi_app.get("/recipes/{recipe_id}", response_model=Recipe)
    async def get_recipe(
        recipe_id: int, db: PostgresRecipeDatabase = Depends(get_recipe_db)
    ):
        """Get a specific recipe by ID."""
        recipe = await db.get(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe

    @fastapi_app.post("/search", response_model=list[Recipe])
    async def search_recipes(
        search_request: SearchRequest,
        db: PostgresRecipeDatabase = Depends(get_recipe_db),
    ):
        """
        Advanced search across recipes.

        Body parameters:
        - query: Search query string
        - search_fields: Fields to search in (default: title, description)
        - max_results: Maximum number of results to return
        """
        return await db.search(
            query=search_request.query,
            search_fields=search_request.search_fields,
            max_results=search_request.max_results,
        )


# Register read-only routes on both APIs
setup_read_only_routes(public_app, mode="public")
setup_read_only_routes(private_app, mode="private")


# ============================================================================
# WRITE-ONLY ROUTES (on private_app only)
# ============================================================================


@private_app.post("/recipes", response_model=Recipe, status_code=201)
async def create_recipe(
    recipe: RecipeCreate, db: PostgresRecipeDatabase = Depends(get_recipe_db)
):
    """Create a new recipe."""
    return await db.create(recipe)


@private_app.put("/recipes/{recipe_id}", response_model=Recipe)
async def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: PostgresRecipeDatabase = Depends(get_recipe_db),
):
    """Update a recipe."""
    recipe = await db.update(recipe_id, recipe_update)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@private_app.delete("/recipes/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: int, db: PostgresRecipeDatabase = Depends(get_recipe_db)
):
    """Delete a recipe."""
    success = await db.delete(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return None


@private_app.post("/import", response_model=Recipe, status_code=201)
async def import_recipe(
    import_request: RecipeImportRequest,
    db: PostgresRecipeDatabase = Depends(get_recipe_db),
):
    """
    Import a recipe from a URL.

    Supports 900+ recipe websites including:
    - AllRecipes
    - Food Network
    - BBC Good Food
    - Serious Eats
    - Bon Appétit
    - And many more!

    Body parameters:
    - url: The URL of the recipe to import

    Example:
    ```
    POST /import
    {
      "url": "https://www.allrecipes.com/recipe/..."
    }
    ```
    """
    # is_public_http_url does DNS resolution — keep it off the event loop
    if not await asyncio.to_thread(is_public_http_url, import_request.url):
        raise HTTPException(
            status_code=400, detail="URL must be a public http(s) address."
        )

    # Scrape recipe from URL
    recipe_data = await scrape_recipe(import_request.url)

    if not recipe_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to scrape recipe from URL. Please ensure the URL is a valid recipe page.",
        )

    recipe_data.image = await validate_image_url(recipe_data.image)

    # Create recipe in database
    return await db.create(recipe_data)


@private_app.post("/paste", response_model=Recipe, status_code=201)
async def paste_recipe(
    paste_request: RecipePasteRequest,
    db: PostgresRecipeDatabase = Depends(get_recipe_db),
):
    """
    Paste in an AI-generated recipe in JSON or markdown format.

    Supports two formats:

    1. JSON format (schema.org Recipe):
    ```json
    {
        "name": "Recipe Name",
        "description": "Optional description",
        "recipeIngredient": ["2 cups flour", "1 egg", "salt to taste"],
        "recipeInstructions": "Step 1...\\nStep 2...",
        "prepTime": "PT15M",
        "cookTime": "PT30M",
        "recipeCategory": ["Dessert"]
    }
    ```

    2. Markdown format:
    ```
    # Recipe Title

    Optional description here

    ## Ingredients
    - 2 cups flour
    - 1 egg
    - salt to taste

    ## Instructions
    1. Mix dry ingredients
    2. Add wet ingredients
    3. Bake at 350°F for 30 minutes

    ## Metadata
    Prep Time: 15 minutes
    Cook Time: 30 minutes
    Category: Dessert
    ```
    """
    recipe_data = parse_recipe_content(paste_request.content)

    if not recipe_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse recipe. Please check the format and try again.",
        )

    recipe_data.image = await validate_image_url(recipe_data.image)

    # Create recipe in database
    return await db.create(recipe_data)
