"""Database abstraction layer for recipes."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from models import Recipe, RecipeCreate, RecipeUpdate


class RecipeDatabase(ABC):

    @abstractmethod
    async def create(self, recipe: RecipeCreate) -> Recipe:
        pass

    @abstractmethod
    async def get(self, recipe_id: int) -> Optional[Recipe]:
        pass

    @abstractmethod
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        ingredient: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at",
    ) -> Tuple[List[Recipe], int]:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> List[Recipe]:
        pass

    @abstractmethod
    async def update(self, recipe_id: int, recipe_update: RecipeUpdate) -> Optional[Recipe]:
        pass

    @abstractmethod
    async def delete(self, recipe_id: int) -> bool:
        pass


def _serialize_ingredients(ingredients) -> list:
    result = []
    for ing in ingredients:
        if isinstance(ing, dict):
            result.append(ing)
        elif hasattr(ing, "model_dump"):
            result.append(ing.model_dump())
        else:
            result.append({"name": str(ing)})
    return result


def _to_recipe(row) -> Recipe:
    ingredients = row["ingredients"]
    if isinstance(ingredients, str):
        ingredients = json.loads(ingredients)
    return Recipe(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        ingredients=ingredients,
        instructions=row["instructions"],
        prep_time=row["prep_time"],
        cook_time=row["cook_time"],
        category=row["category"],
        image_url=row["image_url"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresRecipeDatabase(RecipeDatabase):

    def __init__(self, conn):
        self.conn = conn

    async def create(self, recipe: RecipeCreate) -> Recipe:
        row = await self.conn.fetchrow(
            """
            INSERT INTO recipes
                (title, description, ingredients, instructions,
                 prep_time, cook_time, category, image_url)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            recipe.title,
            recipe.description,
            json.dumps(_serialize_ingredients(recipe.ingredients)),
            recipe.instructions,
            recipe.prep_time,
            recipe.cook_time,
            recipe.category,
            recipe.image_url,
        )
        return _to_recipe(row)

    async def get(self, recipe_id: int) -> Optional[Recipe]:
        row = await self.conn.fetchrow("SELECT * FROM recipes WHERE id = $1", recipe_id)
        return _to_recipe(row) if row else None

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        ingredient: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at",
    ) -> Tuple[List[Recipe], int]:
        conditions: list[str] = []
        params: list = []

        if search:
            params.append(f"%{search}%")
            conditions.append(f"(title ILIKE ${len(params)} OR description ILIKE ${len(params)})")

        if ingredient:
            params.append(f"%{ingredient}%")
            conditions.append(f"ingredients::text ILIKE ${len(params)}")

        if category:
            params.append(category)
            conditions.append(f"category = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = await self.conn.fetchval(f"SELECT COUNT(*) FROM recipes {where}", *params)

        order = "ORDER BY created_at DESC" if sort_by == "created_at" else "ORDER BY title ASC"
        params.append(limit)
        params.append(skip)
        rows = await self.conn.fetch(
            f"SELECT * FROM recipes {where} {order} LIMIT ${len(params) - 1} OFFSET ${len(params)}",
            *params,
        )

        return [_to_recipe(r) for r in rows], total

    async def search(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> List[Recipe]:
        if not search_fields:
            search_fields = ["title", "description"]

        conditions = []
        if "title" in search_fields:
            conditions.append("title ILIKE $1")
        if "description" in search_fields:
            conditions.append("description ILIKE $1")
        if "ingredients" in search_fields:
            conditions.append("ingredients::text ILIKE $1")

        if not conditions:
            return []

        rows = await self.conn.fetch(
            f"SELECT * FROM recipes WHERE {' OR '.join(conditions)} LIMIT $2",
            f"%{query}%",
            max_results,
        )
        return [_to_recipe(r) for r in rows]

    async def update(self, recipe_id: int, recipe_update: RecipeUpdate) -> Optional[Recipe]:
        update_data = recipe_update.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get(recipe_id)

        set_parts: list[str] = []
        params: list = []

        for key, value in update_data.items():
            if key == "ingredients":
                params.append(json.dumps(_serialize_ingredients(value or [])))
                set_parts.append(f"{key} = ${len(params)}::jsonb")
            else:
                params.append(value)
                set_parts.append(f"{key} = ${len(params)}")

        params.append(datetime.now(timezone.utc))
        set_parts.append(f"updated_at = ${len(params)}")

        params.append(recipe_id)
        row = await self.conn.fetchrow(
            f"UPDATE recipes SET {', '.join(set_parts)} WHERE id = ${len(params)} RETURNING *",
            *params,
        )
        return _to_recipe(row) if row else None

    async def delete(self, recipe_id: int) -> bool:
        result = await self.conn.execute("DELETE FROM recipes WHERE id = $1", recipe_id)
        return result != "DELETE 0"
