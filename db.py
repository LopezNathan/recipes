"""Database abstraction layer for recipes."""

from abc import ABC, abstractmethod
from models import Recipe, RecipeCreate, RecipeUpdate
from typing import List, Optional, Tuple


class RecipeDatabase(ABC):
    """Abstract base class for recipe database implementations."""
    
    @abstractmethod
    async def create(self, recipe: RecipeCreate) -> Recipe:
        """Create a new recipe and return it with ID."""
        pass
    
    @abstractmethod
    async def get(self, recipe_id: int) -> Optional[Recipe]:
        """Get a recipe by ID."""
        pass
    
    @abstractmethod
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        ingredient: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at"
    ) -> Tuple[List[Recipe], int]:
        """
        List all recipes with filtering.
        Returns tuple of (recipes, total_count).
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Recipe]:
        """Advanced search across specified fields."""
        pass
    
    @abstractmethod
    async def update(self, recipe_id: int, recipe_update: RecipeUpdate) -> Optional[Recipe]:
        """Update a recipe and return updated recipe or None if not found."""
        pass
    
    @abstractmethod
    async def delete(self, recipe_id: int) -> bool:
        """Delete a recipe. Returns True if deleted, False if not found."""
        pass


class SQLiteRecipeDatabase(RecipeDatabase):
    """SQLite implementation using SQLAlchemy."""
    
    def __init__(self, db_session):
        """Initialize with SQLAlchemy session."""
        self.db = db_session
    
    async def create(self, recipe: RecipeCreate) -> Recipe:
        """Create a new recipe."""
        from database import RecipeModel
        from datetime import datetime
        from sqlalchemy import select
        
        # Serialize ingredients - convert Pydantic models to dicts
        ingredients_data = []
        for ing in recipe.ingredients:
            if isinstance(ing, dict):
                ingredients_data.append(ing)
            elif hasattr(ing, 'model_dump'):  # Pydantic model
                ingredients_data.append(ing.model_dump())
            else:
                ingredients_data.append({"name": str(ing)})
        
        # Create model instance
        db_recipe = RecipeModel(
            title=recipe.title,
            description=recipe.description,
            ingredients=ingredients_data,
            instructions=recipe.instructions,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            category=recipe.category,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(db_recipe)
        await self.db.commit()
        await self.db.refresh(db_recipe)
        
        return self._to_recipe(db_recipe)
    
    async def get(self, recipe_id: int) -> Optional[Recipe]:
        """Get a recipe by ID."""
        from database import RecipeModel
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(RecipeModel).where(RecipeModel.id == recipe_id)
        )
        db_recipe = result.scalar_one_or_none()
        
        if db_recipe:
            return self._to_recipe(db_recipe)
        return None
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        ingredient: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at"
    ) -> Tuple[List[Recipe], int]:
        """List all recipes with filtering."""
        from database import RecipeModel
        from sqlalchemy import select, or_, desc, func
        import json
        
        query = select(RecipeModel)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            query = query.where(
                or_(
                    RecipeModel.title.ilike(f"%{search_lower}%"),
                    RecipeModel.description.ilike(f"%{search_lower}%"),
                )
            )
        
        # Apply ingredient filter
        if ingredient:
            ingredient_lower = ingredient.lower()
            # This is a simple filter - in production you might want more sophisticated matching
            query = query.filter(RecipeModel.ingredients.contains(ingredient_lower))
        
        # Apply category filter
        if category:
            query = query.where(RecipeModel.category == category)
        
        # Count total (before pagination)
        count_query = select(func.count()).select_from(RecipeModel)
        
        # Re-apply filters to count query
        if search:
            search_lower = search.lower()
            count_query = count_query.where(
                or_(
                    RecipeModel.title.ilike(f"%{search_lower}%"),
                    RecipeModel.description.ilike(f"%{search_lower}%"),
                )
            )
        if ingredient:
            ingredient_lower = ingredient.lower()
            count_query = count_query.filter(RecipeModel.ingredients.contains(ingredient_lower))
        if category:
            count_query = count_query.where(RecipeModel.category == category)
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Apply sorting
        if sort_by == "created_at":
            query = query.order_by(desc(RecipeModel.created_at))
        elif sort_by == "title":
            query = query.order_by(RecipeModel.title)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        db_recipes = result.scalars().all()
        
        recipes = [self._to_recipe(r) for r in db_recipes]
        return recipes, total_count
    
    async def search(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Recipe]:
        """Advanced search across specified fields."""
        from database import RecipeModel
        from sqlalchemy import select, or_
        
        if not search_fields:
            search_fields = ["title", "description"]
        
        query_lower = query.lower()
        conditions = []
        
        if "title" in search_fields:
            conditions.append(RecipeModel.title.ilike(f"%{query_lower}%"))
        if "description" in search_fields:
            conditions.append(RecipeModel.description.ilike(f"%{query_lower}%"))
        if "ingredients" in search_fields:
            conditions.append(RecipeModel.ingredients.contains(query_lower))
        
        if not conditions:
            return []
        
        result = await self.db.execute(
            select(RecipeModel)
            .where(or_(*conditions))
            .limit(max_results)
        )
        db_recipes = result.scalars().all()
        
        return [self._to_recipe(r) for r in db_recipes]
    
    async def update(self, recipe_id: int, recipe_update: RecipeUpdate) -> Optional[Recipe]:
        """Update a recipe."""
        from database import RecipeModel
        from datetime import datetime
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(RecipeModel).where(RecipeModel.id == recipe_id)
        )
        db_recipe = result.scalar_one_or_none()
        
        if not db_recipe:
            return None
        
        # Update fields that are provided
        update_data = recipe_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "ingredients" and value is not None:
                # Serialize ingredients
                ingredients_data = []
                for ing in value:
                    if isinstance(ing, dict):
                        ingredients_data.append(ing)
                    elif hasattr(ing, 'model_dump'):  # Pydantic model
                        ingredients_data.append(ing.model_dump())
                    else:
                        ingredients_data.append({"name": str(ing)})
                setattr(db_recipe, field, ingredients_data)
            else:
                setattr(db_recipe, field, value)
        
        db_recipe.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_recipe)
        
        return self._to_recipe(db_recipe)
    
    async def delete(self, recipe_id: int) -> bool:
        """Delete a recipe."""
        from database import RecipeModel
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(RecipeModel).where(RecipeModel.id == recipe_id)
        )
        db_recipe = result.scalar_one_or_none()
        
        if not db_recipe:
            return False
        
        await self.db.delete(db_recipe)
        await self.db.commit()
        return True
    
    @staticmethod
    def _to_recipe(db_recipe) -> Recipe:
        """Convert database model to Pydantic recipe."""
        from models import Recipe
        
        return Recipe(
            id=db_recipe.id,
            title=db_recipe.title,
            description=db_recipe.description,
            ingredients=db_recipe.ingredients,
            instructions=db_recipe.instructions,
            prep_time=db_recipe.prep_time,
            cook_time=db_recipe.cook_time,
            category=db_recipe.category,
            created_at=db_recipe.created_at,
            updated_at=db_recipe.updated_at,
        )
