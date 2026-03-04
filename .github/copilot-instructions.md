# Copilot Instructions for Recipe API

## Project Overview
Recipe API is a lightweight FastAPI application for CRUD operations on recipes with search/filtering capabilities. It uses in-memory storage with JSON file persistence, Pydantic for validation, and pytest for testing.

**Key Files:**
- `main.py` - FastAPI routes and business logic
- `models.py` - Pydantic models (Ingredient, Recipe, SearchRequest)
- `test_main.py` - Comprehensive test suite (34 tests)
- `recipes.json` - Persistent storage file

## Architecture & Data Flow

### Storage Pattern
The codebase uses a **global in-memory dictionary with JSON file persistence**:
```python
recipes_db: dict[int, dict] = {}  # String keys, dict values
next_id = 1  # Global counter for IDs
```

**Critical pattern:** Dictionary keys are **strings** (not ints), but IDs are **integers**. When accessing: `recipes_db[str(recipe_id)]`

### Ingredient Format Support
Ingredients support **Union types** - both strings and objects:
```python
ingredients: list[Union[str, Ingredient]]
```
This dual support is intentional and tested extensively. When filtering/processing ingredients:
1. Handle dict format: `ing.get("name", ing)` for name extraction
2. Handle string format: convert to string with `str(ing)`
3. Always use `.lower()` for case-insensitive matching

### Search & Filtering
Located in `list_recipes()` endpoint:
- **Title/Description search:** Case-insensitive substring match in two fields
- **Ingredient filter:** Loops through ingredients, handles both formats
- **Category filter:** Prepared but not fully integrated (stub exists)
- **Sorting:** Only validates against allowed fields (created_at, title, prep_time, cook_time)
- **Pagination:** `limit` capped at 100 to prevent abuse

## Testing Patterns

### Test Structure
Tests are organized by endpoint in class-based structure (e.g., `TestCreateRecipe`, `TestListRecipes`). Each test class has:
- **Setup/Teardown:** Fixture clears `recipes_db` and `next_id` to ensure test isolation
- **Naming:** `test_<feature>_<case>` (e.g., `test_create_recipe_with_ingredient_quantities`)

### Critical Testing Convention
The fixture **modifies global state**:
```python
@pytest.fixture(autouse=True)
def setup_teardown():
    main.recipes_db.clear()
    main.next_id = 1
    yield
    main.recipes_db.clear()
    main.next_id = 1
```

When adding new tests:
1. Don't create shared recipes across test methods (each test is independent)
2. Always test ID incrementing behavior explicitly (see `TestCreateRecipe::test_create_multiple_recipes`)
3. Case-insensitive matching is thoroughly tested - replicate pattern for new fields

### Test Coverage Areas
- **Validation:** Missing required fields (title, ingredients, instructions)
- **Edge cases:** Empty searches, out-of-range pagination, case sensitivity
- **State management:** ID increments correctly, deletions don't break sequence
- **Integration:** Full CRUD workflows, multiple recipe workflows

## Model Design

### Pydantic Pattern
- `RecipeBase` - Shared fields for Create/Read
- `RecipeCreate` - No ID or timestamps (set server-side)
- `RecipeUpdate` - All fields optional (partial updates supported)
- `Recipe` - Full record with ID and timestamps
- `SearchRequest` - Separate model for POST body validation

### Ingredient Model
```python
class Ingredient(BaseModel):
    name: str
    quantity: Optional[str] = None  # Free-form: "400g", "2 cups", "1 tablespoon"
```

Quantity is **never validated** - accepts any string. This is intentional for flexibility.

## Endpoint Design Patterns

### Error Handling
- `404 Not Found` - When recipe doesn't exist (consistent across GET, PUT, DELETE)
- `400 Bad Request` - Only for empty search queries in `/search` endpoint
- `422 Validation Error` - Pydantic validation failures (auto-handled by FastAPI)
- `201 Created` - POST /recipes returns success code

### Response Structure
GET /recipes returns paginated wrapper:
```python
{
    "recipes": [...],
    "total": int,
    "skip": int,
    "limit": int
}
```

POST /search returns:
```python
{
    "query": str,
    "results": [...],
    "count": int
}
```

### Parameter Validation Pattern
- `search` parameter: Minimal validation (substring match only)
- `ingredient` parameter: Case-insensitive, handles both string/object formats
- `sort_by`: **Whitelist validation** - only allow specific fields, default to "created_at"
- `limit`: **Capped at 100** with `min(limit, 100)`

## Common Developer Tasks

### Adding a New Field to Recipe
1. Update `Ingredient` or `RecipeBase` in `models.py`
2. Update `main.py` functions handling that field
3. Update `test_main.py` with tests for create/update
4. Fields in RecipeUpdate should be Optional if supporting partial updates

### Adding a New Filter
1. Add parameter to `list_recipes()` function signature
2. Implement filter logic **after** search and **before** sorting
3. Add 2-3 test cases in `TestListRecipes` class
4. Test both with and without other filters

### Running Tests Locally
```bash
source venv/bin/activate
pytest test_main.py -v                    # All tests
pytest test_main.py::TestListRecipes -v   # Specific class
pytest test_main.py -k "search" -v        # Pattern matching
```

## Known Limitations & Future Patterns

### Current Gaps
- **No persistent DB** - Using JSON file, not suitable for concurrent writes
- **No authentication** - All endpoints public
- **No category field** - Code prepared but not used (see stub in list_recipes)
- **Ingredient filtering only by name** - Doesn't match by quantity

### Migration Path (if needed)
If migrating to SQLAlchemy/PostgreSQL:
1. Replace `recipes_db` dict with ORM queries
2. Keep Pydantic models for request/response validation
3. Test fixture will need to use database transaction rollback instead of clearing dict
4. String key pattern won't apply (use ORM primary keys)

## Code Style Observations

- **Type hints:** Always used (PEP 484)
- **Docstrings:** Present for endpoints and major functions
- **Error messages:** Lower-case, simple ("Recipe not found", "Query cannot be empty")
- **None handling:** Explicit checks like `(r.get("description") or "").lower()`
- **Global state:** Used sparingly (recipes_db, next_id at module level)
