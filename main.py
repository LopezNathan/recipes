from fastapi import FastAPI, HTTPException
from models import Recipe, RecipeCreate, RecipeUpdate
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
def list_recipes():
    """Get all recipes."""
    recipes = []
    for recipe_id, recipe_data in recipes_db.items():
        recipe_data["id"] = int(recipe_id)
        recipes.append(recipe_data)
    return {"recipes": recipes}


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    """Get a specific recipe by ID."""
    if str(recipe_id) not in recipes_db:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe = recipes_db[str(recipe_id)].copy()
    recipe["id"] = recipe_id
    return recipe


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
