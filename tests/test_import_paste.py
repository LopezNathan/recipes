"""Tests for import and paste endpoints."""

import json


# Paste endpoint tests
def test_paste_recipe_json_format(client):
    recipe_json = {
        "name": "Pasta Primavera",
        "description": "Fresh vegetable pasta",
        "recipeIngredient": ["400g pasta", "2 cups broccoli", "3 cloves garlic"],
        "recipeInstructions": "Cook pasta, steam broccoli, combine",
        "prepTime": "PT15M",
        "cookTime": "PT20M",
        "recipeCategory": ["vegetarian"],
    }

    response = client.post("/paste", json={"content": json.dumps(recipe_json)})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pasta Primavera"
    assert data["description"] == "Fresh vegetable pasta"
    assert len(data["recipeIngredient"]) == 3
    assert data["prepTime"] == "PT15M"
    assert data["cookTime"] == "PT20M"
    assert data["recipeCategory"] == ["vegetarian"]


def test_paste_recipe_markdown_format(client):
    recipe_markdown = """# Chocolate Brownies

Dense and fudgy brownies with dark chocolate flavor.

## Ingredients
- 2 cups flour
- 1 cup sugar
- 3/4 cup cocoa powder
- 2 eggs
- 1 cup butter

## Instructions
1. Preheat oven to 350°F
2. Mix dry ingredients
3. Add eggs and butter
4. Pour into pan
5. Bake for 30 minutes

## Metadata
Prep Time: 15
Cook Time: 30
Category: Dessert
"""

    response = client.post("/paste", json={"content": recipe_markdown})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Chocolate Brownies"
    assert "Dense and fudgy" in data["description"]
    assert len(data["recipeIngredient"]) == 5
    assert "Preheat oven" in data["recipeInstructions"]
    assert data["prepTime"] == "PT15M"
    assert data["cookTime"] == "PT30M"
    assert data["recipeCategory"] == ["Dessert"]


def test_paste_recipe_markdown_description_extraction(client):
    recipe_markdown = """# Tomato Soup

This is a delicious homemade tomato soup recipe.

## Ingredients
- 2 lbs tomatoes
- 1 cup cream

## Instructions
1. Cook tomatoes
2. Blend smooth
3. Add cream
"""

    response = client.post("/paste", json={"content": recipe_markdown})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tomato Soup"
    assert data["description"] == "This is a delicious homemade tomato soup recipe."


def test_paste_recipe_markdown_multiline_description(client):
    recipe_markdown = """# Beef Stew

This hearty beef stew is perfect for cold winter nights.
It's loaded with vegetables and tender beef chunks.

## Ingredients
- 2 lbs beef
- 4 carrots
- 3 potatoes

## Instructions
1. Brown beef
2. Add vegetables
3. Simmer 2 hours
"""

    response = client.post("/paste", json={"content": recipe_markdown})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beef Stew"
    assert "hearty beef stew" in data["description"].lower()
    assert "winter nights" in data["description"].lower()


def test_paste_recipe_json_with_all_fields(client):
    recipe_json = {
        "name": "Risotto Milanese",
        "description": "Creamy Italian rice dish",
        "recipeIngredient": ["300g arborio rice", "saffron", "100g parmesan"],
        "recipeInstructions": "Toast rice, add broth gradually, stir constantly",
        "prepTime": "PT10M",
        "cookTime": "PT25M",
        "recipeCategory": ["italian"],
        "image": "https://example.com/risotto.jpg",
    }

    response = client.post("/paste", json={"content": json.dumps(recipe_json)})

    assert response.status_code == 201
    data = response.json()
    assert data["image"] == "https://example.com/risotto.jpg"
    assert data["recipeCategory"] == ["italian"]


def test_paste_recipe_json_minimal_fields(client):
    recipe_json = {
        "name": "Fried Egg",
        "recipeIngredient": ["1 egg", "1 tbsp oil"],
        "recipeInstructions": "Heat oil, crack egg, cook until done",
    }

    response = client.post("/paste", json={"content": json.dumps(recipe_json)})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Fried Egg"
    assert len(data["recipeIngredient"]) == 2


def test_paste_recipe_auto_detection_json(client):
    recipe_json = {
        "name": "Pancakes",
        "recipeIngredient": ["2 cups flour", "2 eggs"],
        "recipeInstructions": "Mix, cook on griddle",
    }

    response = client.post("/paste", json={"content": json.dumps(recipe_json)})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pancakes"


def test_paste_recipe_auto_detection_markdown(client):
    recipe_markdown = """# Omelette

Quick egg dish.

## Ingredients
- 3 eggs
- 1 tbsp butter

## Instructions
1. Heat butter
2. Pour eggs
3. Cook until set
"""

    response = client.post("/paste", json={"content": recipe_markdown})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Omelette"


def test_paste_recipe_missing_content(client):
    response = client.post("/paste", json={})
    assert response.status_code == 422


def test_paste_recipe_markdown_with_multiple_paragraphs(client):
    recipe_markdown = """# French Toast

This classic breakfast dish is crispy on the outside
and custardy on the inside.

Make it for special weekend breakfasts or brunch with friends.

## Ingredients
- 4 slices bread
- 2 eggs
- 1 cup milk

## Instructions
1. Whisk eggs and milk
2. Dip bread slices
3. Cook on griddle until golden
"""

    response = client.post("/paste", json={"content": recipe_markdown})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "French Toast"
    assert "crispy on the outside" in data["description"]
    assert "## Ingredients" not in data["description"]


def test_paste_recipe_json_legacy_fields(client):
    """Test that legacy field names (title, ingredients, instructions) are accepted."""
    recipe_json = {
        "title": "Simple Pasta",
        "ingredients": ["salt", "400g pasta", "olive oil", "2 cloves garlic"],
        "instructions": "Cook pasta, garlic in oil, season with salt",
    }

    response = client.post("/paste", json={"content": json.dumps(recipe_json)})

    assert response.status_code == 201
    data = response.json()
    assert len(data["recipeIngredient"]) == 4


def test_import_recipe_missing_url(client):
    response = client.post("/import", json={})
    assert response.status_code == 422


def test_import_rejects_internal_urls(client):
    for url in (
        "http://127.0.0.1:8001/recipes",
        "http://localhost/recipe",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
    ):
        response = client.post("/import", json={"url": url})
        assert response.status_code == 400, url
        assert "public" in response.json()["detail"]
