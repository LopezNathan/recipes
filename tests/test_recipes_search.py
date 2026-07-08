"""Tests for search and filtering."""


def test_search_recipes(client):
    recipes = [
        {
            "name": "Spaghetti",
            "description": "Pasta dish",
            "recipeIngredient": ["pasta"],
        },
        {
            "name": "Salad",
            "description": "Fresh greens",
            "recipeIngredient": ["lettuce"],
        },
        {
            "name": "Pasta Carbonara",
            "description": "Italian",
            "recipeIngredient": ["pasta"],
        },
    ]

    for recipe in recipes:
        recipe["recipeInstructions"] = "Cook"
        client.post("/recipes", json=recipe)

    response = client.post("/search", json={"query": "pasta"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_search_empty_results(client):
    client.post(
        "/recipes",
        json={
            "name": "Salad",
            "recipeIngredient": ["lettuce"],
            "recipeInstructions": "Mix",
        },
    )

    response = client.post("/search", json={"query": "pizza"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_search_with_specific_fields(client):
    client.post(
        "/recipes",
        json={
            "name": "Tomato Pasta",
            "description": "No mentions of eggs",
            "recipeIngredient": ["pasta", "tomato"],
            "recipeInstructions": "Cook",
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Salad",
            "description": "With eggs for protein",
            "recipeIngredient": ["lettuce", "eggs"],
            "recipeInstructions": "Mix",
        },
    )

    response = client.post(
        "/search", json={"query": "pasta", "search_fields": ["name"]}
    )
    data = response.json()
    assert len(data) == 1
    assert "Tomato Pasta" in data[0]["name"]


def test_search_max_results(client):
    for i in range(5):
        client.post(
            "/recipes",
            json={
                "name": f"Pasta {i}",
                "description": "A pasta dish",
                "recipeIngredient": ["pasta"],
                "recipeInstructions": "Cook",
            },
        )

    response = client.post("/search", json={"query": "pasta", "max_results": 2})
    data = response.json()
    assert len(data) <= 2


def test_list_recipes_with_search(client):
    for title in ["Pasta Carbonara", "Pasta Bolognese", "Chicken Soup"]:
        recipe_data = {
            "name": title,
            "description": "A delicious dish",
            "recipeIngredient": ["tomato"],
            "recipeInstructions": "Cook it",
        }
        client.post("/recipes", json=recipe_data)

    response = client.get("/recipes?search=pasta")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Pasta" in r["name"] for r in data["recipes"])


def test_list_recipes_search_case_insensitive(client):
    client.post(
        "/recipes",
        json={
            "name": "Pasta Carbonara",
            "recipeIngredient": ["pasta"],
            "recipeInstructions": "Cook",
        },
    )

    for query in ["pasta", "PASTA", "Pasta", "pAsTa"]:
        response = client.get(f"/recipes?search={query}")
        data = response.json()
        assert data["total"] == 1


def test_list_recipes_filter_by_category(client):
    client.post(
        "/recipes",
        json={
            "name": "Brownies",
            "recipeIngredient": ["chocolate"],
            "recipeInstructions": "Bake",
            "recipeCategory": ["dessert"],
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Steak",
            "recipeIngredient": ["beef"],
            "recipeInstructions": "Grill",
            "recipeCategory": ["main"],
        },
    )

    response = client.get("/recipes?category=dessert")
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["recipeCategory"] == ["dessert"]


def test_list_recipes_filter_by_ingredient(client):
    client.post(
        "/recipes",
        json={
            "name": "Pasta Carbonara",
            "recipeIngredient": ["pasta", "eggs", "bacon"],
            "recipeInstructions": "Cook",
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Egg Salad",
            "recipeIngredient": ["eggs", "lettuce"],
            "recipeInstructions": "Mix",
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Tomato Soup",
            "recipeIngredient": ["tomato", "cream"],
            "recipeInstructions": "Simmer",
        },
    )

    response = client.get("/recipes?ingredient=eggs")
    data = response.json()
    assert data["total"] == 2


def test_list_recipes_combined_filters(client):
    client.post(
        "/recipes",
        json={
            "name": "Pasta Carbonara",
            "description": "Italian classic",
            "recipeIngredient": ["pasta", "eggs"],
            "recipeInstructions": "Cook",
            "recipeCategory": ["main"],
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Egg Fried Rice",
            "description": "Asian dish",
            "recipeIngredient": ["eggs", "rice"],
            "recipeInstructions": "Stir fry",
            "recipeCategory": ["main"],
        },
    )

    client.post(
        "/recipes",
        json={
            "name": "Egg Soup",
            "recipeIngredient": ["eggs"],
            "recipeInstructions": "Simmer",
            "recipeCategory": ["soup"],
        },
    )

    response = client.get("/recipes?ingredient=eggs&category=main")
    data = response.json()
    assert data["total"] == 2
    assert all(r["recipeCategory"] == ["main"] for r in data["recipes"])
