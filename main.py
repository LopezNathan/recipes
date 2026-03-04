from fastapi import FastAPI, HTTPException
from models import Recipe, RecipeCreate, RecipeUpdate, SearchRequest
from datetime import datetime
import json
import os

app = FastAPI(title="Recipe API", version="1.0.0")

# In-memory storage for recipes
recipes_db: dict[int, dict] = {}
next_id = 1

# File for persistent storage
DB_FILE = "recipes.json"


def load_recipes():
    """Load recipes from JSON file if it exists."""
    global recipes_db, next_id
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                recipes_db = data.get("recipes", {})
                next_id = data.get("next_id", 1)
        except Exception as e:
            print(f"Error loading recipes: {e}")


def save_recipes():
    """Save recipes to JSON file."""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(
                {"recipes": recipes_db, "next_id": next_id},
                f,
                indent=2,
                default=str,
            )
    except Exception as e:
        print(f"Error saving recipes: {e}")


# Load recipes on startup
load_recipes()


@app.get("/")
def read_root():
    """Welcome endpoint."""
    return {"message": "Welcome to the Recipe API"}


@app.get("/recipes")
def list_recipes(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    ingredient: str | None = None,
    category: str | None = None,
    sort_by: str = "created_at"
):
    """
    Get all recipes with optional filtering and search.
    
    Query parameters:
    - search: Search in title and description (case-insensitive)
    - ingredient: Filter recipes containing a specific ingredient
    - category: Filter by recipe category
    - skip: Pagination offset (default: 0)
    - limit: Pagination limit (default: 100, max: 100)
    - sort_by: Sort field (created_at, title, prep_time, cook_time)
    """
    # Limit the max limit to 100
    limit = min(limit, 100)
    
    recipes = []
    for recipe_id, recipe_data in recipes_db.items():
        recipe_data["id"] = int(recipe_id)
        recipes.append(recipe_data)
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        recipes = [
            r for r in recipes
            if search_lower in r.get("title", "").lower()
            or search_lower in (r.get("description") or "").lower()
        ]
    
    # Apply ingredient filter
    if ingredient:
        ingredient_lower = ingredient.lower()
        filtered_recipes = []
        for r in recipes:
            ingredients = r.get("ingredients", [])
            for ing in ingredients:
                # Handle both string and object formats
                ing_name = ing.get("name", ing).lower() if isinstance(ing, dict) else str(ing).lower()
                if ingredient_lower in ing_name:
                    filtered_recipes.append(r)
                    break
        recipes = filtered_recipes
    
    # Apply category filter if category field exists
    if category:
        recipes = [r for r in recipes if r.get("category", "").lower() == category.lower()]
    
    # Sort recipes
    sort_field = sort_by if sort_by in ["created_at", "title", "prep_time", "cook_time"] else "created_at"
    reverse = sort_field == "created_at"
    
    try:
        recipes.sort(
            key=lambda x: x.get(sort_field, ""),
            reverse=reverse
        )
    except TypeError:
        # If sorting fails, return unsorted
        pass
    
    # Apply pagination
    total = len(recipes)
    recipes = recipes[skip : skip + limit]
    
    return {
        "recipes": recipes,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    """Get a specific recipe by ID."""
    if str(recipe_id) not in recipes_db:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe = recipes_db[str(recipe_id)].copy()
    recipe["id"] = recipe_id
    return recipe


@app.post("/search")
def search_recipes(search_request: SearchRequest):
    """
    Advanced search endpoint.
    
    Parameters:
    - query: Search query string
    - search_fields: Fields to search in (default: ["title", "description"])
    - max_results: Maximum results to return (default: 10)
    """
    if not search_request.query or len(search_request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    search_fields = search_request.search_fields
    if search_fields is None:
        search_fields = ["title", "description"]
    
    query_lower = search_request.query.lower()
    results = []
    
    for recipe_id, recipe_data in recipes_db.items():
        recipe = recipe_data.copy()
        recipe["id"] = int(recipe_id)
        
        # Search in specified fields
        match_found = False
        for field in search_fields:
            if field in recipe and isinstance(recipe[field], str):
                if query_lower in recipe[field].lower():
                    match_found = True
                    break
        
        if match_found:
            results.append(recipe)
        
        if len(results) >= search_request.max_results:
            break
    
    return {
        "query": search_request.query,
        "results": results,
        "count": len(results)
    }


@app.post("/recipes", status_code=201)
def create_recipe(recipe: RecipeCreate):
    """Create a new recipe."""
    global next_id
    
    recipe_data = recipe.model_dump()
    recipe_data["created_at"] = datetime.now().isoformat()
    recipe_data["updated_at"] = datetime.now().isoformat()
    
    recipes_db[str(next_id)] = recipe_data
    save_recipes()
    
    response = recipe_data.copy()
    response["id"] = next_id
    next_id += 1
    
    return response


@app.put("/recipes/{recipe_id}")
def update_recipe(recipe_id: int, recipe: RecipeUpdate):
    """Update an existing recipe."""
    if str(recipe_id) not in recipes_db:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    existing_recipe = recipes_db[str(recipe_id)]
    update_data = recipe.model_dump(exclude_unset=True)
    
    updated_recipe = {**existing_recipe, **update_data}
    updated_recipe["updated_at"] = datetime.now().isoformat()
    
    recipes_db[str(recipe_id)] = updated_recipe
    save_recipes()
    
    response = updated_recipe.copy()
    response["id"] = recipe_id
    
    return response


@app.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int):
    """Delete a recipe."""
    if str(recipe_id) not in recipes_db:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    del recipes_db[str(recipe_id)]
    save_recipes()
    
    return None
