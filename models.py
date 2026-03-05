from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime


class Ingredient(BaseModel):
    """Ingredient with name and optional quantity."""
    name: str
    quantity: Optional[str] = None  # e.g., "2 cups", "500g", "1 tablespoon"


class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None
    ingredients: list[Union[str, Ingredient]]  # Support both strings and Ingredient objects
    instructions: str
    prep_time: Optional[int] = None  # in minutes
    cook_time: Optional[int] = None  # in minutes
    category: Optional[str] = None  # e.g., "dessert", "main", "appetizer"
    image_url: Optional[str] = None  # URL to recipe image


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[list[Union[str, Ingredient]]] = None
    instructions: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None


class Recipe(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    """Request model for advanced search."""
    query: str
    search_fields: Optional[list[str]] = None
    max_results: int = 10


class RecipeImportRequest(BaseModel):
    """Request model for importing recipe from URL."""
    url: str
