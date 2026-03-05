"""FastAPI Recipe Application with SQLite."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from models import Recipe, RecipeCreate, RecipeUpdate, SearchRequest
from database import init_db, AsyncSessionLocal
from db import SQLiteRecipeDatabase


# Lifespan event handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, cleanup on shutdown."""
    # Startup
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down")


# Create FastAPI app
app = FastAPI(
    title="Recipe API",
    version="1.0.0",
    description="A simple recipe management API",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database instance
async def get_recipe_db(session: AsyncSession = Depends(lambda: AsyncSessionLocal())) -> SQLiteRecipeDatabase:
    """Get SQLite recipe database."""
    return SQLiteRecipeDatabase(session)



# Routes
@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("index.html", media_type="text/html")


@app.get("/recipes", response_model=dict)
async def list_recipes(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    ingredient: str | None = None,
    category: str | None = None,
    sort_by: str = "created_at",
    db: SQLiteRecipeDatabase = Depends(get_recipe_db),
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


@app.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int, db: SQLiteRecipeDatabase = Depends(get_recipe_db)):
    """Get a specific recipe by ID."""
    recipe = await db.get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@app.post("/recipes", response_model=Recipe, status_code=201)
async def create_recipe(recipe: RecipeCreate, db: SQLiteRecipeDatabase = Depends(get_recipe_db)):
    """Create a new recipe."""
    return await db.create(recipe)


@app.put("/recipes/{recipe_id}", response_model=Recipe)
async def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: SQLiteRecipeDatabase = Depends(get_recipe_db),
):
    """Update a recipe."""
    recipe = await db.update(recipe_id, recipe_update)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@app.delete("/recipes/{recipe_id}", status_code=204)
async def delete_recipe(recipe_id: int, db: SQLiteRecipeDatabase = Depends(get_recipe_db)):
    """Delete a recipe."""
    success = await db.delete(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return None


@app.post("/search", response_model=list[Recipe])
async def search_recipes(
    search_request: SearchRequest,
    db: SQLiteRecipeDatabase = Depends(get_recipe_db),
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