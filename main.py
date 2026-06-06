"""FastAPI Recipe Application - Dual API Setup."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.models import Recipe, RecipeCreate, RecipeUpdate, SearchRequest, RecipeImportRequest, RecipePasteRequest
from app.database import init_db, close_db, get_pool
from app.db import PostgresRecipeDatabase
from app.scraper import scrape_recipe
from app.recipe_parser import parse_recipe_content
from app.image_utils import validate_image_url


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
    lifespan=lifespan
)

# Enable CORS for public API (only allow GET)
public_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)
public_app.mount("/static", StaticFiles(directory="static"), name="static-public")


# ============================================================================
# PRIVATE API (Read/Write) - Port 8001
# ============================================================================
private_app = FastAPI(
    title="Recipe API - Private (Read/Write)",
    version="1.0.0",
    description="Private read/write recipe API. Access via Cloudflare tunnel only.",
    lifespan=lifespan
)

# Enable CORS for private API (allow all methods)
private_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
private_app.mount("/static", StaticFiles(directory="static"), name="static-private")

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

    @fastapi_app.get("/")
    async def root():
        """Serve the main HTML page."""
        return FileResponse("index.html", media_type="text/html")

    @fastapi_app.get("/recipes", response_model=dict)
    async def list_recipes(
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        ingredient: str | None = None,
        category: str | None = None,
        sort_by: str = "created_at",
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
        - sort_by: Sort field (created_at or title)
        """
        recipes, total = await db.list_all(
            skip=skip,
            limit=limit,
            search=search,
            ingredient=ingredient,
            category=category,
            sort_by=sort_by,
        )
        
        return {
            "recipes": recipes,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @fastapi_app.get("/recipes/{recipe_id}", response_model=Recipe)
    async def get_recipe(recipe_id: int, db: PostgresRecipeDatabase = Depends(get_recipe_db)):
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
async def create_recipe(recipe: RecipeCreate, db: PostgresRecipeDatabase = Depends(get_recipe_db)):
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
async def delete_recipe(recipe_id: int, db: PostgresRecipeDatabase = Depends(get_recipe_db)):
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
    # Scrape recipe from URL
    recipe_data = await scrape_recipe(import_request.url)

    if not recipe_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to scrape recipe from URL. Please ensure the URL is a valid recipe page."
        )

    recipe_data.image = await validate_image_url(recipe_data.image)

    # Create recipe in database
    return await db.create(recipe_data)


@private_app.post("/paste", response_model=Recipe)
async def paste_recipe(paste_request: RecipePasteRequest, db: PostgresRecipeDatabase = Depends(get_recipe_db)):
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
            detail="Failed to parse recipe. Please check the format and try again."
        )

    recipe_data.image = await validate_image_url(recipe_data.image)

    # Create recipe in database
    return await db.create(recipe_data)
