from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    recipeIngredient: list[str]
    recipeInstructions: str
    prepTime: Optional[str] = None   # ISO 8601, e.g. "PT30M"
    cookTime: Optional[str] = None   # ISO 8601, e.g. "PT1H"
    recipeYield: Optional[str] = None  # e.g. "4 servings"
    recipeCategory: Optional[list[str]] = None
    recipeCuisine: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    image: Optional[str] = None
    url: Optional[str] = None


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    recipeIngredient: Optional[list[str]] = None
    recipeInstructions: Optional[str] = None
    prepTime: Optional[str] = None
    cookTime: Optional[str] = None
    recipeYield: Optional[str] = None
    recipeCategory: Optional[list[str]] = None
    recipeCuisine: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    image: Optional[str] = None
    url: Optional[str] = None


class Recipe(RecipeBase):
    id: int
    datePublished: datetime
    dateModified: datetime


class RecipeListResponse(BaseModel):
    recipes: list[Recipe]
    total: int
    skip: int
    limit: int


class RecipePasteRequest(BaseModel):
    content: str

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    search_fields: Optional[list[str]] = None
    max_results: int = Field(default=10, ge=1, le=100)


class RecipeImportRequest(BaseModel):
    url: str
