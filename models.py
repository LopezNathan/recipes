from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None
    ingredients: list[str]
    instructions: str
    prep_time: Optional[int] = None  # in minutes
    cook_time: Optional[int] = None  # in minutes


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[list[str]] = None
    instructions: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None


class Recipe(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
