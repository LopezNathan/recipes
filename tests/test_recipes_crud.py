"""Tests for CRUD operations on recipes."""


def test_create_recipe(client):
    """Test POST /recipes creates a recipe."""
    recipe_data = {
        "title": "Spaghetti Carbonara",
        "description": "Classic Italian pasta",
        "ingredients": [
            {"name": "pasta", "quantity": "400g"},
            {"name": "eggs", "quantity": "3"},
        ],
        "instructions": "Cook pasta, fry bacon, mix with eggs",
        "prep_time": 10,
        "cook_time": 20,
        "category": "main"
    }
    
    response = client.post("/recipes", json=recipe_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Spaghetti Carbonara"
    assert data["description"] == "Classic Italian pasta"
    assert len(data["ingredients"]) == 2
    assert data["prep_time"] == 10
    assert data["cook_time"] == 20
    assert data["category"] == "main"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_recipe_with_string_ingredients(client):
    """Test creating recipe with string ingredients."""
    recipe_data = {
        "title": "Simple Salad",
        "ingredients": ["lettuce", "tomato", "olive oil"],
        "instructions": "Mix and serve",
    }
    
    response = client.post("/recipes", json=recipe_data)
    assert response.status_code == 201
    data = response.json()
    assert len(data["ingredients"]) == 3


def test_create_recipe_minimal(client):
    """Test creating recipe with minimal fields."""
    recipe_data = {
        "title": "Minimal Recipe",
        "ingredients": ["ingredient"],
        "instructions": "Just do it",
    }
    
    response = client.post("/recipes", json=recipe_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal Recipe"
    assert data["description"] is None
    assert data["category"] is None
    assert data["prep_time"] is None
    assert data["cook_time"] is None


def test_get_recipe(client):
    """Test GET /recipes/{id} returns specific recipe."""
    recipe_data = {
        "title": "Test Recipe",
        "ingredients": ["test"],
        "instructions": "Test",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]
    
    response = client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == recipe_id
    assert data["title"] == "Test Recipe"


def test_get_nonexistent_recipe(client):
    """Test GET /recipes/{id} returns 404 for nonexistent recipe."""
    response = client.get("/recipes/999")
    assert response.status_code == 404


def test_update_recipe(client):
    """Test PUT /recipes/{id} updates a recipe."""
    recipe_data = {
        "title": "Original Title",
        "ingredients": ["original"],
        "instructions": "Original instructions",
        "prep_time": 10,
        "cook_time": 20,
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]
    
    update_data = {
        "title": "Updated Title",
        "prep_time": 15,
    }
    response = client.put(f"/recipes/{recipe_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == recipe_id
    assert data["title"] == "Updated Title"
    assert data["prep_time"] == 15
    assert data["cook_time"] == 20  # Unchanged
    assert data["instructions"] == "Original instructions"  # Unchanged


def test_partial_update(client):
    """Test partial update of recipe."""
    recipe_data = {
        "title": "Original",
        "description": "Original desc",
        "ingredients": ["ing"],
        "instructions": "Cook",
        "prep_time": 10,
        "cook_time": 20,
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]
    
    response = client.put(f"/recipes/{recipe_id}", json={"cook_time": 30})
    assert response.status_code == 200
    
    data = response.json()
    assert data["cook_time"] == 30
    assert data["prep_time"] == 10
    assert data["description"] == "Original desc"


def test_update_nonexistent_recipe(client):
    """Test PUT /recipes/{id} returns 404 for nonexistent recipe."""
    response = client.put("/recipes/999", json={"title": "Updated"})
    assert response.status_code == 404


def test_delete_recipe(client):
    """Test DELETE /recipes/{id} deletes a recipe."""
    recipe_data = {
        "title": "To Delete",
        "ingredients": ["ingredient"],
        "instructions": "Delete me",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]
    
    response = client.delete(f"/recipes/{recipe_id}")
    assert response.status_code == 204
    
    response = client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 404


def test_delete_nonexistent_recipe(client):
    """Test DELETE /recipes/{id} returns 404 for nonexistent recipe."""
    response = client.delete("/recipes/999")
    assert response.status_code == 404
