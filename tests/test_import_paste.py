"""Tests for import and paste endpoints."""
import json


# Paste endpoint tests
def test_paste_recipe_json_format(client):
    """Test pasting a recipe in JSON format."""
    recipe_json = {
        "title": "Pasta Primavera",
        "description": "Fresh vegetable pasta",
        "ingredients": [
            {"name": "pasta", "quantity": "400g"},
            {"name": "broccoli", "quantity": "2 cups"},
            {"name": "garlic", "quantity": "3 cloves"},
        ],
        "instructions": "Cook pasta, steam broccoli, combine",
        "prep_time": 15,
        "cook_time": 20,
        "category": "vegetarian",
    }

    response = client.post(
        "/paste",
        json={"content": json.dumps(recipe_json)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Pasta Primavera"
    assert data["description"] == "Fresh vegetable pasta"
    assert len(data["ingredients"]) == 3
    assert data["prep_time"] == 15
    assert data["cook_time"] == 20
    assert data["category"] == "vegetarian"


def test_paste_recipe_markdown_format(client):
    """Test pasting a recipe in markdown format."""
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

    response = client.post(
        "/paste",
        json={"content": recipe_markdown},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Chocolate Brownies"
    assert "Dense and fudgy" in data["description"]
    assert len(data["ingredients"]) == 5
    assert "Preheat oven" in data["instructions"]
    assert data["prep_time"] == 15
    assert data["cook_time"] == 30
    assert data["category"] == "Dessert"


def test_paste_recipe_markdown_description_extraction(client):
    """Test that markdown description is extracted correctly from first paragraph."""
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

    response = client.post(
        "/paste",
        json={"content": recipe_markdown},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Tomato Soup"
    assert data["description"] == "This is a delicious homemade tomato soup recipe."


def test_paste_recipe_markdown_multiline_description(client):
    """Test markdown with multiline description."""
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

    response = client.post(
        "/paste",
        json={"content": recipe_markdown},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Beef Stew"
    assert "hearty beef stew" in data["description"].lower()
    assert "winter nights" in data["description"].lower()


def test_paste_recipe_json_with_all_fields(client):
    """Test JSON format with all optional fields."""
    recipe_json = {
        "title": "Risotto Milanese",
        "description": "Creamy Italian rice dish",
        "ingredients": [
            {"name": "arborio rice", "quantity": "300g"},
            "saffron",
            {"name": "parmesan", "quantity": "100g"},
        ],
        "instructions": "Toast rice, add broth gradually, stir constantly",
        "prep_time": 10,
        "cook_time": 25,
        "category": "italian",
        "image_url": "https://example.com/risotto.jpg",
    }

    response = client.post(
        "/paste",
        json={"content": json.dumps(recipe_json)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image_url"] == "https://example.com/risotto.jpg"
    assert data["category"] == "italian"


def test_paste_recipe_json_minimal_fields(client):
    """Test JSON format with only required fields."""
    recipe_json = {
        "title": "Fried Egg",
        "ingredients": [
            {"name": "egg", "quantity": "1"},
            {"name": "oil", "quantity": "1 tbsp"},
        ],
        "instructions": "Heat oil, crack egg, cook until done",
    }

    response = client.post(
        "/paste",
        json={"content": json.dumps(recipe_json)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Fried Egg"
    assert len(data["ingredients"]) == 2


def test_paste_recipe_auto_detection_json(client):
    """Test that JSON format is auto-detected."""
    recipe_json = {
        "title": "Pancakes",
        "ingredients": [
            {"name": "flour", "quantity": "2 cups"},
            {"name": "eggs", "quantity": "2"},
        ],
        "instructions": "Mix, cook on griddle",
    }

    response = client.post(
        "/paste",
        json={"content": json.dumps(recipe_json)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Pancakes"


def test_paste_recipe_auto_detection_markdown(client):
    """Test that markdown format is auto-detected."""
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

    response = client.post(
        "/paste",
        json={"content": recipe_markdown},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Omelette"


def test_paste_recipe_missing_content(client):
    """Test paste request without content field."""
    response = client.post("/paste", json={})
    assert response.status_code == 422


def test_paste_recipe_markdown_with_multiple_paragraphs(client):
    """Test markdown with multiline description before ingredients."""
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

    response = client.post(
        "/paste",
        json={"content": recipe_markdown},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "French Toast"
    assert "crispy on the outside" in data["description"]
    assert "## Ingredients" not in data["description"]


def test_paste_recipe_json_with_string_ingredients(client):
    """Test JSON format with mixed ingredient formats (string and dict)."""
    recipe_json = {
        "title": "Simple Pasta",
        "ingredients": [
            "salt",
            {"name": "pasta", "quantity": "400g"},
            "olive oil",
            {"name": "garlic", "quantity": "2 cloves"},
        ],
        "instructions": "Cook pasta, garlic in oil, season with salt",
    }

    response = client.post(
        "/paste",
        json={"content": json.dumps(recipe_json)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["ingredients"]) == 4


def test_import_recipe_missing_url(client):
    """Test import request without URL."""
    response = client.post("/import", json={})
    assert response.status_code == 422
