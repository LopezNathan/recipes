"""Tests for listing and pagination."""


def test_list_recipes_empty(client):
    response = client.get("/recipes")
    assert response.status_code == 200
    data = response.json()
    assert data["recipes"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 100


def test_list_recipes_with_data(client):
    recipe_data = {
        "name": "Pasta",
        "description": "Delicious pasta",
        "recipeIngredient": ["400g pasta"],
        "recipeInstructions": "Boil and serve",
        "recipeCategory": ["main"],
    }
    create_resp = client.post("/recipes", json=recipe_data)
    assert create_resp.status_code == 201

    response = client.get("/recipes")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["total"] == 1
    assert data["recipes"][0]["name"] == "Pasta"


def test_list_recipes_pagination(client):
    for i in range(5):
        recipe_data = {
            "name": f"Recipe {i}",
            "recipeIngredient": ["ingredient"],
            "recipeInstructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)

    response = client.get("/recipes?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["total"] == 5
    assert data["skip"] == 0
    assert data["limit"] == 2

    response = client.get("/recipes?skip=2&limit=2")
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["skip"] == 2

    response = client.get("/recipes?skip=4&limit=2")
    data = response.json()
    assert len(data["recipes"]) == 1


def test_list_recipes_default_pagination(client):
    for i in range(3):
        recipe_data = {
            "name": f"Recipe {i}",
            "recipeIngredient": ["ing"],
            "recipeInstructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)

    response = client.get("/recipes")
    data = response.json()
    assert data["skip"] == 0
    assert data["limit"] == 100
    assert data["total"] == 3
    assert len(data["recipes"]) == 3


def test_list_recipes_with_custom_skip_and_limit(client):
    for i in range(10):
        recipe_data = {
            "name": f"Recipe {i:02d}",
            "recipeIngredient": ["ing"],
            "recipeInstructions": "Cook",
        }
        client.post("/recipes", json=recipe_data)

    response = client.get("/recipes?skip=3&limit=4")
    data = response.json()
    assert len(data["recipes"]) == 4
    assert data["total"] == 10
    assert data["skip"] == 3
    assert data["limit"] == 4
