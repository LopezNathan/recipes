"""Tests for search and filtering."""


def test_search_recipes(client):
    """Test POST /search finds recipes."""
    recipes = [
        {"title": "Spaghetti", "description": "Pasta dish", "ingredients": ["pasta"]},
        {"title": "Salad", "description": "Fresh greens", "ingredients": ["lettuce"]},
        {"title": "Pasta Carbonara", "description": "Italian", "ingredients": ["pasta"]},
    ]
    
    for recipe in recipes:
        recipe["instructions"] = "Cook"
        client.post("/recipes", json=recipe)
    
    response = client.post("/search", json={"query": "pasta"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_search_empty_results(client):
    """Test search with no results."""
    client.post("/recipes", json={
        "title": "Salad",
        "ingredients": ["lettuce"],
        "instructions": "Mix"
    })
    
    response = client.post("/search", json={"query": "pizza"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_search_with_specific_fields(client):
    """Test search in specific fields."""
    client.post("/recipes", json={
        "title": "Tomato Pasta",
        "description": "No mentions of eggs",
        "ingredients": ["pasta", "tomato"],
        "instructions": "Cook"
    })
    
    client.post("/recipes", json={
        "title": "Salad",
        "description": "With eggs for protein",
        "ingredients": ["lettuce", "eggs"],
        "instructions": "Mix"
    })
    
    response = client.post("/search", json={
        "query": "pasta",
        "search_fields": ["title"]
    })
    data = response.json()
    assert len(data) == 1
    assert "Tomato Pasta" in data[0]["title"]


def test_search_max_results(client):
    """Test search respects max_results."""
    for i in range(5):
        client.post("/recipes", json={
            "title": f"Pasta {i}",
            "description": "A pasta dish",
            "ingredients": ["pasta"],
            "instructions": "Cook"
        })
    
    response = client.post("/search", json={
        "query": "pasta",
        "max_results": 2
    })
    data = response.json()
    assert len(data) <= 2


def test_list_recipes_with_search(client):
    """Test GET /recipes with search parameter."""
    for title in ["Pasta Carbonara", "Pasta Bolognese", "Chicken Soup"]:
        recipe_data = {
            "title": title,
            "description": "A delicious dish",
            "ingredients": ["tomato"],
            "instructions": "Cook it",
        }
        client.post("/recipes", json=recipe_data)
    
    response = client.get("/recipes?search=pasta")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Pasta" in r["title"] for r in data["recipes"])


def test_list_recipes_search_case_insensitive(client):
    """Test search is case-insensitive."""
    client.post("/recipes", json={
        "title": "Pasta Carbonara",
        "ingredients": ["pasta"],
        "instructions": "Cook",
    })
    
    # Search with different cases
    for query in ["pasta", "PASTA", "Pasta", "pAsTa"]:
        response = client.get(f"/recipes?search={query}")
        data = response.json()
        assert data["total"] == 1


def test_list_recipes_filter_by_category(client):
    """Test GET /recipes with category filter."""
    client.post("/recipes", json={
        "title": "Brownies",
        "ingredients": ["chocolate"],
        "instructions": "Bake",
        "category": "dessert"
    })
    
    client.post("/recipes", json={
        "title": "Steak",
        "ingredients": ["beef"],
        "instructions": "Grill",
        "category": "main"
    })
    
    response = client.get("/recipes?category=dessert")
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["category"] == "dessert"


def test_list_recipes_filter_by_ingredient(client):
    """Test GET /recipes with ingredient filter."""
    client.post("/recipes", json={
        "title": "Pasta Carbonara",
        "ingredients": ["pasta", "eggs", "bacon"],
        "instructions": "Cook",
    })
    
    client.post("/recipes", json={
        "title": "Egg Salad",
        "ingredients": ["eggs", "lettuce"],
        "instructions": "Mix",
    })
    
    client.post("/recipes", json={
        "title": "Tomato Soup",
        "ingredients": ["tomato", "cream"],
        "instructions": "Simmer",
    })
    
    response = client.get("/recipes?ingredient=eggs")
    data = response.json()
    assert data["total"] == 2


def test_list_recipes_combined_filters(client):
    """Test GET /recipes with multiple filters."""
    client.post("/recipes", json={
        "title": "Pasta Carbonara",
        "description": "Italian classic",
        "ingredients": ["pasta", "eggs"],
        "instructions": "Cook",
        "category": "main"
    })
    
    client.post("/recipes", json={
        "title": "Egg Fried Rice",
        "description": "Asian dish",
        "ingredients": ["eggs", "rice"],
        "instructions": "Stir fry",
        "category": "main"
    })
    
    client.post("/recipes", json={
        "title": "Egg Soup",
        "ingredients": ["eggs"],
        "instructions": "Simmer",
        "category": "soup"
    })
    
    # Filter by ingredient and category
    response = client.get("/recipes?ingredient=eggs&category=main")
    data = response.json()
    assert data["total"] == 2
    assert all(r["category"] == "main" for r in data["recipes"])
