# Recipe API

A simple FastAPI application for creating, reading, updating, and deleting recipes with SQLite persistence.

## Features

- Create recipes with title, description, ingredients, instructions, cooking times, and categories
- Read all recipes or get a specific recipe by ID
- Update recipe details
- Delete recipes
- Search and filter recipes by title, description, ingredients, and category
- **Recipe Image Support** - Store and display recipe images with image URLs
- **Web Recipe Import** - Import recipes from 900+ websites (AllRecipes, Food Network, Budget Bytes, Serious Eats, etc.)
- **AI Recipe Paste** - Paste AI-generated recipes in JSON or markdown format
- **Intelligent Ingredient Parsing** - Automatically separates quantity from ingredient name
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

The application provides two separate APIs:

**Public API (Read-only) - Port 8000**
```bash
uvicorn main:public_app --port 8000 --reload
```
Available at `http://localhost:8000` - anyone can read recipes, but cannot create/edit/delete

**Private API (Read/Write) - Port 8001**
```bash
uvicorn main:private_app --port 8001 --reload
```
Available at `http://localhost:8001` - intended for authenticated access via Cloudflare tunnel, supports all operations

**For local development** (single API with all features):
```bash
uvicorn main:app --reload
```
This runs the private app on port 8000 with full read/write access.

The database (`recipes.db`) will be created automatically on first run.

### 4. API Documentation

When running an API instance, documentation is available at:
- **Swagger UI**: `http://localhost:{port}/docs`
- **ReDoc**: `http://localhost:{port}/redoc`

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

### Import recipe from URL
```
POST /import
Content-Type: application/json

{
  "url": "https://www.budgetbytes.com/recipe/baked-sweet-potato-fries/"
}
```

Supports 900+ recipe websites including:
- AllRecipes
- Food Network
- Serious Eats
- Budget Bytes
- And many more!

**Response:** Returns the created recipe with extracted metadata (title, ingredients, instructions, image_url, prep_time, cook_time, etc.)

### Paste AI-generated recipe
```
POST /paste
Content-Type: application/json

{
  "content": "{\"title\": \"My Recipe\", \"ingredients\": [{\"name\": \"flour\", \"quantity\": \"2 cups\"}], \"instructions\": \"Mix and bake\"}"
}
```

Supports two formats:

**JSON Format:**
```json
{
  "title": "Recipe Name",
  "description": "Optional description",
  "ingredients": [
    {"name": "flour", "quantity": "2 cups"},
    "salt to taste"
  ],
  "instructions": "Step 1...\nStep 2...",
  "prep_time": 15,
  "cook_time": 30,
  "category": "dessert",
  "image_url": "https://..."
}
```

**Markdown Format:**
```
# Recipe Name

Optional description here

## Ingredients
- 2 cups flour
- 1 egg
- salt to taste

## Instructions
1. Mix dry ingredients
2. Add wet ingredients
3. Bake at 350°F for 30 minutes

## Metadata
Prep Time: 15
Cook Time: 30
Category: Dessert
```

Auto-detects format and parses accordingly. Metadata extraction is optional.

## Project Structure

- `main.py` - FastAPI application and route handlers
- `models.py` - Pydantic data models for request/response validation
- `database.py` - SQLAlchemy async engine and database models
- `db.py` - Abstract database interface and SQLite implementation
- `scraper.py` - Web recipe scraper using recipe-scrapers library
- `recipe_parser.py` - JSON and markdown recipe format parser
- `requirements.txt` - Python dependencies
- `recipes.db` - SQLite database (auto-created on first run)
- `index.html` - Frontend UI with import and paste features

## Deployment with Cloudflare

### Architecture

This API is designed to run behind Cloudflare Tunnel with two separate endpoints:

1. **Public API (Port 8000)** - Read-only access
   - Anyone can view recipes without authentication
   - Only supports GET requests and `/search` (POST)
   - Perfect for sharing your recipe collection publicly
   - Example: `https://recipes.example.com/recipes`

2. **Private API (Port 8001)** - Read/Write access via Cloudflare Access
   - Protected by Cloudflare Access (email/password or SSO)
   - Supports all operations (create, edit, delete, import, paste)
   - Only accessible through the Cloudflare Tunnel
   - Example: `https://private-recipes.example.com/recipes`

### Setup with Cloudflare Tunnel

```bash
# Terminal 1: Run public API
uvicorn main:public_app --port 8000

# Terminal 2: Run private API
uvicorn main:private_app --port 8001

# Terminal 3: Create Cloudflare Tunnel
cloudflared tunnel run my-recipes-tunnel
```

### Cloudflare Configuration

In `~/.cloudflared/config.yml`:

```yaml
tunnel: my-recipes-tunnel
credentials-file: /Users/yourusername/.cloudflared/my-recipes-tunnel.json

ingress:
  # Public read-only API
  - hostname: recipes.example.com
    service: http://localhost:8000
  
  # Private read/write API (with Cloudflare Access policy)
  - hostname: private-recipes.example.com
    service: http://localhost:8001
  
  # Fallback
  - service: http_status:404
```

Then set Cloudflare Access policy on `private-recipes.example.com` to require authentication.

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
- `tests/test_import_paste.py` - 12 tests for import and paste endpoints

**Test features:**
- Uses fresh file-based SQLite database for each test (auto-cleanup)
- **36 total tests** covering all CRUD operations, search, filtering, import/paste, and error cases
- Async tests with proper fixture setup/teardown
- Each test is independent with isolated database state
- Fast execution (~0.5 seconds for full suite)
- All deprecation warnings fixed (uses `datetime.now(timezone.utc)` instead of deprecated `utcnow()`)

**Note about warnings:**
The test suite may display benign SQLAlchemy GC warnings about unchecked-in connections. These are harmless warnings from aiosqlite's garbage collection and don't affect test reliability. To suppress them, run:
```bash
pytest tests/ -v -W ignore::sqlalchemy.exc.SAWarning
```

**Example output:**
```
tests/test_recipes_crud.py::test_create_recipe PASSED
tests/test_recipes_crud.py::test_update_recipe PASSED
tests/test_recipes_crud.py::test_delete_recipe PASSED
tests/test_recipes_list.py::test_list_recipes_with_data PASSED
tests/test_recipes_list.py::test_list_recipes_pagination PASSED
tests/test_recipes_search.py::test_search_recipes PASSED
tests/test_recipes_search.py::test_list_recipes_filter_by_category PASSED
tests/test_import_paste.py::test_paste_recipe_json_format PASSED
tests/test_import_paste.py::test_paste_recipe_markdown_format PASSED
======================== 36 passed in 0.50s ======================
```
