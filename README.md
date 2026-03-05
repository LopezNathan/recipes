# Recipe API

A simple FastAPI application for creating, reading, updating, and deleting recipes with SQLite persistence.

## Features

- Create recipes with title, description, ingredients, instructions, cooking times, and categories
- Read all recipes or get a specific recipe by ID
- Update recipe details
- Delete recipes
- Search and filter recipes by title, description, ingredients, and category
- **Persistent SQLite database** - suitable for cloud deployment
- Async/await throughout for non-blocking I/O

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`
The database (`recipes.db`) will be created automatically on first run.

### 3. API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### List all recipes (with optional filtering)
```
GET /recipes
```

**Query Parameters:**
- `search` (string, optional): Search in title and description (case-insensitive)
- `ingredient` (string, optional): Filter recipes containing a specific ingredient
- `category` (string, optional): Filter by recipe category
- `skip` (integer, optional): Pagination offset (default: 0)
- `limit` (integer, optional): Pagination limit (default: 100, max: 100)
- `sort_by` (string, optional): Sort field - `created_at`, `title`, `prep_time`, `cook_time` (default: created_at)

**Examples:**
```
GET /recipes?search=pasta
GET /recipes?ingredient=tomato
GET /recipes?search=pasta&skip=0&limit=10
GET /recipes?sort_by=prep_time&limit=5
GET /recipes?ingredient=egg&search=breakfast
```

### Advanced search
```
POST /search
Content-Type: application/json

{
  "query": "pasta",
  "search_fields": ["title", "description"],
  "max_results": 10
}
```

### Get a specific recipe
```
GET /recipes/{recipe_id}
```

### Create a new recipe
```
POST /recipes
Content-Type: application/json

{
  "title": "Spaghetti Carbonara",
  "description": "A classic Italian pasta dish",
  "ingredients": [
    {"name": "pasta", "quantity": "400g"},
    {"name": "eggs", "quantity": "3"},
    {"name": "bacon", "quantity": "200g"},
    {"name": "parmesan", "quantity": "100g"}
  ],
  "instructions": "Cook pasta, fry bacon, mix with eggs and cheese",
  "prep_time": 10,
  "cook_time": 20
}
```

**Note:** You can specify ingredients in two formats:
- **With quantity:** `{"name": "pasta", "quantity": "400g"}`
- **Simple string:** `"pasta"` (quantity is optional)

### Update a recipe
```
PUT /recipes/{recipe_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "prep_time": 15
}
```

### Delete a recipe
```
DELETE /recipes/{recipe_id}
```

## Project Structure

- `main.py` - FastAPI application and route handlers
- `models.py` - Pydantic data models for request/response validation
- `database.py` - SQLAlchemy async engine and database models
- `db.py` - Abstract database interface and SQLite implementation
- `requirements.txt` - Python dependencies
- `recipes.db` - SQLite database (auto-created on first run)
- `index.html` - Frontend UI

## Database

This app uses **SQLite** with **SQLAlchemy ORM** for data persistence:
- Database file: `recipes.db` (auto-created on first run, NOT committed to git)
- Schema: Recipes table with id, title, description, ingredients (JSON), instructions, prep_time, cook_time, category, created_at, updated_at
- **Easy migration path**: The abstraction layer in `db.py` allows swapping to PostgreSQL, DynamoDB, or other databases in the future

## Testing

Run the test suite with:

```bash
pytest tests/ -v
```

**Test Structure:**
- `tests/conftest.py` - Shared pytest fixtures for database setup/teardown
- `tests/test_recipes_crud.py` - 10 tests for Create, Read, Update, Delete operations
- `tests/test_recipes_list.py` - 5 tests for listing and pagination
- `tests/test_recipes_search.py` - 9 tests for search and filtering

**Test features:**
- Uses fresh file-based SQLite database for each test (auto-cleanup)
- **24 total tests** covering all CRUD operations, search, filtering, and error cases
- Async tests with proper fixture setup/teardown
- Each test is independent with isolated database state
- Fast execution (~0.35 seconds for full suite)
- All deprecation warnings fixed (uses `datetime.now(timezone.utc)` instead of deprecated `utcnow()`)
- SQLAlchemy connection cleanup warnings suppressed (benign GC warnings)

**Example output:**
```
tests/test_recipes_crud.py::test_create_recipe PASSED
tests/test_recipes_crud.py::test_update_recipe PASSED
tests/test_recipes_crud.py::test_delete_recipe PASSED
tests/test_recipes_list.py::test_list_recipes_with_data PASSED
tests/test_recipes_list.py::test_list_recipes_pagination PASSED
tests/test_recipes_search.py::test_search_recipes PASSED
tests/test_recipes_search.py::test_list_recipes_filter_by_category PASSED
======================== 24 passed in 0.35s ======================
```
