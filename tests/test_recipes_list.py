"""Tests for listing and pagination."""


def test_list_recipes_empty(client):
    """Test GET /recipes returns empty list when no recipes exist."""
    response = client.get("/recipes")
    assert response.status_code == 200
    data = response.json()
    assert data["recipes"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 100


def test_list_recipes_with_data(client):
    """Test GET /recipes returns recipes."""
    recipe_data = {
        "title": "Pasta",
        "description": "Delicious pasta",
        "ingredients": [{"name": "pasta", "quantity": "400g"}],
        "instructions": "Boil and serve",
        "category": "main"
    }
    create_resp = client.post("/recipes", json=recipe_data)
    assert create_resp.status_code == 201
    
    response = client.get("/recipes")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["total"] == 1
    assert data["recipes"][0]["title"] == "Pasta"


def test_list_recipes_pagination(client):
    """Test GET /recipes with pagination."""
    # Create 5 recipes
    for i in range(5):
        recipe_data = {
            "title": f"Recipe {i}",
            "ingredients": ["ingredient"],
            "instructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)
    
    # Get first 2
    response = client.get("/recipes?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["total"] == 5
    assert data["skip"] == 0
    assert data["limit"] == 2
    
    # Get next 2
    response = client.get("/recipes?skip=2&limit=2")
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["skip"] == 2
    
    # Get last 1
    response = client.get("/recipes?skip=4&limit=2")
    data = response.json()
    assert len(data["recipes"]) == 1


def test_list_recipes_default_pagination(client):
    """Test GET /recipes uses correct default pagination."""
    # Create 3 recipes
    for i in range(3):
        recipe_data = {
            "title": f"Recipe {i}",
            "ingredients": ["ing"],
            "instructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)
    
    response = client.get("/recipes")
    data = response.json()
    assert data["skip"] == 0
    assert data["limit"] == 100
    assert data["total"] == 3
    assert len(data["recipes"]) == 3


def test_list_recipes_with_custom_skip_and_limit(client):
    """Test GET /recipes with custom skip and limit."""
    for i in range(10):
        recipe_data = {
            "title": f"Recipe {i:02d}",
            "ingredients": ["ing"],
            "instructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)
    
    response = client.get("/recipes?skip=3&limit=4")
    data = response.json()
    assert len(data["recipes"]) == 4
    assert data["total"] == 10
    assert data["skip"] == 3
    assert data["limit"] == 4
