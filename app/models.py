from datetime import datetime

from pydantic import BaseModel, Field


class RecipeBase(BaseModel):
    name: str
    description: str | None = None
    recipeIngredient: list[str]
    recipeInstructions: str
    prepTime: str | None = None  # ISO 8601, e.g. "PT30M"
    cookTime: str | None = None  # ISO 8601, e.g. "PT1H"
    recipeYield: str | None = None  # e.g. "4 servings"
    recipeCategory: list[str] | None = None
    recipeCuisine: list[str] | None = None
    keywords: list[str] | None = None
    image: str | None = None
    url: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)  # personal 1-5 star rating


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    recipeIngredient: list[str] | None = None
    recipeInstructions: str | None = None
    prepTime: str | None = None
    cookTime: str | None = None
    recipeYield: str | None = None
    recipeCategory: list[str] | None = None
    recipeCuisine: list[str] | None = None
    keywords: list[str] | None = None
    image: str | None = None
    url: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


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
    search_fields: list[str] | None = None
    max_results: int = Field(default=10, ge=1, le=100)


class RecipeImportRequest(BaseModel):
    url: str
