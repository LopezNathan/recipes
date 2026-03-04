# Recipe API

A simple FastAPI application for creating, reading, updating, and deleting recipes.

## Features

- Create recipes with title, description, ingredients, instructions, and cooking times
- Read all recipes or get a specific recipe by ID
- Update recipe details
- Delete recipes
- Persistent JSON-based storage

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### 3. API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### List all recipes
```
GET /recipes
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
- `models.py` - Pydantic data models
- `requirements.txt` - Python dependencies
- `recipes.json` - Persistent data storage (created automatically)
