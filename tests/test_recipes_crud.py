"""Tests for CRUD operations on recipes."""


def test_create_recipe(client):
    recipe_data = {
        "name": "Spaghetti Carbonara",
        "description": "Classic Italian pasta",
        "recipeIngredient": ["400g pasta", "3 eggs", "200g bacon"],
        "recipeInstructions": "Cook pasta, fry bacon, mix with eggs",
        "prepTime": "PT10M",
        "cookTime": "PT20M",
        "recipeCategory": ["main"]
    }

    response = client.post("/recipes", json=recipe_data)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Spaghetti Carbonara"
    assert data["description"] == "Classic Italian pasta"
    assert len(data["recipeIngredient"]) == 3
    assert data["prepTime"] == "PT10M"
    assert data["cookTime"] == "PT20M"
    assert data["recipeCategory"] == ["main"]
    assert "datePublished" in data
    assert "dateModified" in data


def test_create_recipe_minimal(client):
    recipe_data = {
        "name": "Minimal Recipe",
        "recipeIngredient": ["ingredient"],
        "recipeInstructions": "Just do it",
    }

    response = client.post("/recipes", json=recipe_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Recipe"
    assert data["description"] is None
    assert data["recipeCategory"] is None
    assert data["prepTime"] is None
    assert data["cookTime"] is None


def test_get_recipe(client):
    recipe_data = {
        "name": "Test Recipe",
        "recipeIngredient": ["test"],
        "recipeInstructions": "Test",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]

    response = client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == recipe_id
    assert data["name"] == "Test Recipe"


def test_get_nonexistent_recipe(client):
    response = client.get("/recipes/999")
    assert response.status_code == 404


def test_update_recipe(client):
    recipe_data = {
        "name": "Original Title",
        "recipeIngredient": ["original"],
        "recipeInstructions": "Original instructions",
        "prepTime": "PT10M",
        "cookTime": "PT20M",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]

    update_data = {
        "name": "Updated Title",
        "prepTime": "PT15M",
    }
    response = client.put(f"/recipes/{recipe_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == recipe_id
    assert data["name"] == "Updated Title"
    assert data["prepTime"] == "PT15M"
    assert data["cookTime"] == "PT20M"
    assert data["recipeInstructions"] == "Original instructions"


def test_partial_update(client):
    recipe_data = {
        "name": "Original",
        "description": "Original desc",
        "recipeIngredient": ["ing"],
        "recipeInstructions": "Cook",
        "prepTime": "PT10M",
        "cookTime": "PT20M",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]

    response = client.put(f"/recipes/{recipe_id}", json={"cookTime": "PT30M"})
    assert response.status_code == 200

    data = response.json()
    assert data["cookTime"] == "PT30M"
    assert data["prepTime"] == "PT10M"
    assert data["description"] == "Original desc"


def test_update_nonexistent_recipe(client):
    response = client.put("/recipes/999", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_recipe(client):
    recipe_data = {
        "name": "To Delete",
        "recipeIngredient": ["ingredient"],
        "recipeInstructions": "Delete me",
    }
    create_resp = client.post("/recipes", json=recipe_data)
    recipe_id = create_resp.json()["id"]

    response = client.delete(f"/recipes/{recipe_id}")
    assert response.status_code == 204

    response = client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 404


def test_delete_nonexistent_recipe(client):
    response = client.delete("/recipes/999")
    assert response.status_code == 404
