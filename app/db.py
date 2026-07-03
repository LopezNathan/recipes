"""Database abstraction layer for recipes."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.models import Recipe, RecipeCreate, RecipeUpdate


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
        cuisine: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by: str = "date_published",
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

    @abstractmethod
    async def get_categories(self) -> List[str]:
        pass

    @abstractmethod
    async def get_cuisines(self) -> List[str]:
        pass

    @abstractmethod
    async def get_keywords(self) -> List[str]:
        pass


def _to_recipe(row) -> Recipe:
    def _load_json(val):
        return json.loads(val) if isinstance(val, str) else val

    return Recipe(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        recipeIngredient=_load_json(row["recipe_ingredient"]) or [],
        recipeInstructions=row["recipe_instructions"],
        prepTime=row["prep_time"],
        cookTime=row["cook_time"],
        recipeYield=row["recipe_yield"],
        recipeCategory=_load_json(row["recipe_category"]) if row["recipe_category"] else None,
        recipeCuisine=_load_json(row["recipe_cuisine"]) if row["recipe_cuisine"] else None,
        keywords=_load_json(row["keywords"]) if row["keywords"] else None,
        image=row["image"],
        url=row["url"],
        datePublished=row["date_published"],
        dateModified=row["date_modified"],
    )


class PostgresRecipeDatabase(RecipeDatabase):

    def __init__(self, conn):
        self.conn = conn

    async def create(self, recipe: RecipeCreate) -> Recipe:
        row = await self.conn.fetchrow(
            """
            INSERT INTO recipes
                (name, description, recipe_ingredient, recipe_instructions,
                 prep_time, cook_time, recipe_yield, recipe_category,
                 recipe_cuisine, keywords, image, url)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10::jsonb, $11, $12)
            RETURNING *
            """,
            recipe.name,
            recipe.description,
            json.dumps(recipe.recipeIngredient),
            recipe.recipeInstructions,
            recipe.prepTime,
            recipe.cookTime,
            recipe.recipeYield,
            json.dumps(recipe.recipeCategory) if recipe.recipeCategory is not None else None,
            json.dumps(recipe.recipeCuisine) if recipe.recipeCuisine is not None else None,
            json.dumps(recipe.keywords) if recipe.keywords is not None else None,
            recipe.image,
            recipe.url,
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
        cuisine: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by: str = "date_published",
    ) -> Tuple[List[Recipe], int]:
        conditions: list[str] = []
        params: list = []

        if search:
            params.append(f"%{search}%")
            conditions.append(f"(name ILIKE ${len(params)} OR description ILIKE ${len(params)})")

        if ingredient:
            params.append(f"%{ingredient}%")
            conditions.append(f"recipe_ingredient::text ILIKE ${len(params)}")

        if category:
            params.append(category)
            conditions.append(
                f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(recipe_category) AS c WHERE lower(c) = lower(${len(params)}))"
            )

        if cuisine:
            params.append(cuisine)
            conditions.append(
                f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(recipe_cuisine) AS c WHERE lower(c) = lower(${len(params)}))"
            )

        if keyword:
            params.append(keyword)
            conditions.append(
                f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(keywords) AS k WHERE lower(k) = lower(${len(params)}))"
            )

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = await self.conn.fetchval(f"SELECT COUNT(*) FROM recipes {where}", *params)

        order = "ORDER BY date_published DESC" if sort_by == "date_published" else "ORDER BY name ASC"
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
            search_fields = ["name", "description"]

        # Map schema.org field names to DB column names
        col_map = {"name": "name", "title": "name", "description": "description", "recipeIngredient": "recipe_ingredient"}

        conditions = []
        for field in search_fields:
            col = col_map.get(field, field)
            if col in ("name", "description"):
                conditions.append(f"{col} ILIKE $1")
            elif col == "recipe_ingredient":
                conditions.append("recipe_ingredient::text ILIKE $1")

        if not conditions:
            return []

        rows = await self.conn.fetch(
            f"SELECT * FROM recipes WHERE {' OR '.join(conditions)} "
            "ORDER BY date_published DESC, id DESC LIMIT $2",
            f"%{query}%",
            max_results,
        )
        return [_to_recipe(r) for r in rows]

    async def update(self, recipe_id: int, recipe_update: RecipeUpdate) -> Optional[Recipe]:
        update_data = recipe_update.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get(recipe_id)

        # Map model field names to DB column names
        col_map = {
            "name": "name",
            "description": "description",
            "recipeIngredient": "recipe_ingredient",
            "recipeInstructions": "recipe_instructions",
            "prepTime": "prep_time",
            "cookTime": "cook_time",
            "recipeYield": "recipe_yield",
            "recipeCategory": "recipe_category",
            "recipeCuisine": "recipe_cuisine",
            "keywords": "keywords",
            "image": "image",
            "url": "url",
        }
        jsonb_cols = {"recipe_ingredient", "recipe_category", "recipe_cuisine", "keywords"}

        set_parts: list[str] = []
        params: list = []

        for field, value in update_data.items():
            col = col_map.get(field, field)
            if col in jsonb_cols:
                params.append(json.dumps(value) if value is not None else None)
                set_parts.append(f"{col} = ${len(params)}::jsonb")
            else:
                params.append(value)
                set_parts.append(f"{col} = ${len(params)}")

        params.append(datetime.now(timezone.utc))
        set_parts.append(f"date_modified = ${len(params)}")

        params.append(recipe_id)
        row = await self.conn.fetchrow(
            f"UPDATE recipes SET {', '.join(set_parts)} WHERE id = ${len(params)} RETURNING *",
            *params,
        )
        return _to_recipe(row) if row else None

    async def delete(self, recipe_id: int) -> bool:
        result = await self.conn.execute("DELETE FROM recipes WHERE id = $1", recipe_id)
        return result != "DELETE 0"

    async def get_categories(self) -> List[str]:
        rows = await self.conn.fetch(
            """
            SELECT DISTINCT jsonb_array_elements_text(recipe_category) AS category
            FROM recipes
            WHERE recipe_category IS NOT NULL
            ORDER BY category
            """
        )
        return [row["category"] for row in rows]

    async def get_cuisines(self) -> List[str]:
        rows = await self.conn.fetch(
            """
            SELECT DISTINCT jsonb_array_elements_text(recipe_cuisine) AS cuisine
            FROM recipes
            WHERE recipe_cuisine IS NOT NULL
            ORDER BY cuisine
            """
        )
        return [row["cuisine"] for row in rows]

    async def get_keywords(self) -> List[str]:
        rows = await self.conn.fetch(
            """
            SELECT DISTINCT jsonb_array_elements_text(keywords) AS keyword
            FROM recipes
            WHERE keywords IS NOT NULL
            ORDER BY keyword
            """
        )
        return [row["keyword"] for row in rows]
