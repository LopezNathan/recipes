import pytest
import json
import os
from fastapi.testclient import TestClient
import main

# Create a test client
client = TestClient(main.app)

# Test database file
TEST_DB_FILE = "test_recipes.json"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Clear the in-memory database before each test
    main.recipes_db.clear()
    main.next_id = 1
    
    # Remove test database file if it exists
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    
    yield
    
    # Cleanup after test
    main.recipes_db.clear()
    main.next_id = 1
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_read_root(self):
        """Test GET / returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Welcome to the Recipe API"


class TestListRecipes:
    """Test list recipes endpoint."""
    
    def test_list_recipes_empty(self):
        """Test GET /recipes returns empty list when no recipes exist."""
        response = client.get("/recipes")
        assert response.status_code == 200
        assert response.json()["recipes"] == []
    
    def test_list_recipes_with_data(self):
        """Test GET /recipes returns all recipes."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta", "tomato"],
            "instructions": "Cook and serve"
        }
        client.post("/recipes", json=recipe_data)
        
        # List recipes
        response = client.get("/recipes")
        assert response.status_code == 200
        recipes = response.json()["recipes"]
        assert len(recipes) == 1
        assert recipes[0]["title"] == "Pasta"


class TestCreateRecipe:
    """Test create recipe endpoint."""
    
    def test_create_recipe_minimal(self):
        """Test creating a recipe with minimal required fields."""
        recipe_data = {
            "title": "Simple Pasta",
            "ingredients": ["pasta", "salt", "water"],
            "instructions": "Boil water, add pasta, cook until done"
        }
        response = client.post("/recipes", json=recipe_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Simple Pasta"
        assert data["ingredients"] == ["pasta", "salt", "water"]
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_recipe_full(self):
        """Test creating a recipe with all fields."""
        recipe_data = {
            "title": "Spaghetti Carbonara",
            "description": "A classic Italian pasta dish",
            "ingredients": ["pasta", "eggs", "bacon", "parmesan"],
            "instructions": "Cook pasta, fry bacon, mix with eggs and cheese",
            "prep_time": 10,
            "cook_time": 20
        }
        response = client.post("/recipes", json=recipe_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Spaghetti Carbonara"
        assert data["description"] == "A classic Italian pasta dish"
        assert data["prep_time"] == 10
        assert data["cook_time"] == 20
    
    def test_create_recipe_missing_title(self):
        """Test creating a recipe without title fails."""
        recipe_data = {
            "ingredients": ["pasta"],
            "instructions": "Cook it"
        }
        response = client.post("/recipes", json=recipe_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_create_recipe_missing_ingredients(self):
        """Test creating a recipe without ingredients fails."""
        recipe_data = {
            "title": "Pasta",
            "instructions": "Cook it"
        }
        response = client.post("/recipes", json=recipe_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_create_recipe_missing_instructions(self):
        """Test creating a recipe without instructions fails."""
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta"]
        }
        response = client.post("/recipes", json=recipe_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_create_multiple_recipes(self):
        """Test creating multiple recipes increments IDs."""
        for i in range(3):
            recipe_data = {
                "title": f"Recipe {i+1}",
                "ingredients": ["ingredient1"],
                "instructions": "Instructions"
            }
            response = client.post("/recipes", json=recipe_data)
            assert response.status_code == 201
            assert response.json()["id"] == i + 1


class TestGetRecipe:
    """Test get single recipe endpoint."""
    
    def test_get_recipe_success(self):
        """Test getting an existing recipe."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "description": "Italian dish",
            "ingredients": ["pasta", "tomato"],
            "instructions": "Cook and serve",
            "prep_time": 5,
            "cook_time": 15
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        
        # Get the recipe
        response = client.get(f"/recipes/{recipe_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recipe_id
        assert data["title"] == "Pasta"
        assert data["description"] == "Italian dish"
        assert data["prep_time"] == 5
        assert data["cook_time"] == 15
    
    def test_get_recipe_not_found(self):
        """Test getting a non-existent recipe."""
        response = client.get("/recipes/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateRecipe:
    """Test update recipe endpoint."""
    
    def test_update_recipe_title(self):
        """Test updating just the title."""
        # Create a recipe
        recipe_data = {
            "title": "Original Title",
            "ingredients": ["pasta"],
            "instructions": "Cook"
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        original_created_at = create_response.json()["created_at"]
        
        # Update the recipe
        update_data = {"title": "Updated Title"}
        response = client.put(f"/recipes/{recipe_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recipe_id
        assert data["title"] == "Updated Title"
        assert data["created_at"] == original_created_at
        assert data["updated_at"] > original_created_at
    
    def test_update_recipe_multiple_fields(self):
        """Test updating multiple fields."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta"],
            "instructions": "Cook",
            "prep_time": 5,
            "cook_time": 15
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        
        # Update multiple fields
        update_data = {
            "title": "Updated Pasta",
            "description": "New description",
            "prep_time": 10,
            "cook_time": 20
        }
        response = client.put(f"/recipes/{recipe_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Pasta"
        assert data["description"] == "New description"
        assert data["prep_time"] == 10
        assert data["cook_time"] == 20
        assert data["ingredients"] == ["pasta"]  # Unchanged
    
    def test_update_recipe_ingredients(self):
        """Test updating ingredients."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta", "salt"],
            "instructions": "Cook"
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        
        # Update ingredients
        update_data = {
            "ingredients": ["pasta", "salt", "olive oil", "garlic"]
        }
        response = client.put(f"/recipes/{recipe_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ingredients"] == ["pasta", "salt", "olive oil", "garlic"]
    
    def test_update_recipe_not_found(self):
        """Test updating a non-existent recipe."""
        update_data = {"title": "New Title"}
        response = client.put("/recipes/999", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_recipe_empty_update(self):
        """Test updating a recipe with no fields."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta"],
            "instructions": "Cook"
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        original_data = create_response.json()
        
        # Update with empty object
        response = client.put(f"/recipes/{recipe_id}", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == original_data["title"]
        assert data["ingredients"] == original_data["ingredients"]


class TestDeleteRecipe:
    """Test delete recipe endpoint."""
    
    def test_delete_recipe_success(self):
        """Test deleting an existing recipe."""
        # Create a recipe
        recipe_data = {
            "title": "Pasta",
            "ingredients": ["pasta"],
            "instructions": "Cook"
        }
        create_response = client.post("/recipes", json=recipe_data)
        recipe_id = create_response.json()["id"]
        
        # Delete the recipe
        response = client.delete(f"/recipes/{recipe_id}")
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/recipes/{recipe_id}")
        assert get_response.status_code == 404
    
    def test_delete_recipe_not_found(self):
        """Test deleting a non-existent recipe."""
        response = client.delete("/recipes/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_recipe_then_create_new(self):
        """Test that creating after delete uses next ID correctly."""
        # Create first recipe
        recipe_data = {
            "title": "Pasta 1",
            "ingredients": ["pasta"],
            "instructions": "Cook"
        }
        response1 = client.post("/recipes", json=recipe_data)
        id1 = response1.json()["id"]
        
        # Create second recipe
        recipe_data["title"] = "Pasta 2"
        response2 = client.post("/recipes", json=recipe_data)
        id2 = response2.json()["id"]
        
        # Delete first recipe
        client.delete(f"/recipes/{id1}")
        
        # Create third recipe - should get next ID (not reuse deleted ID)
        recipe_data["title"] = "Pasta 3"
        response3 = client.post("/recipes", json=recipe_data)
        id3 = response3.json()["id"]
        
        assert id1 == 1
        assert id2 == 2
        assert id3 == 3


class TestIntegration:
    """Integration tests for full workflows."""
    
    def test_full_crud_workflow(self):
        """Test a complete CRUD workflow."""
        # Create
        recipe_data = {
            "title": "Spaghetti Carbonara",
            "description": "Classic Italian pasta",
            "ingredients": ["pasta", "eggs", "bacon", "parmesan"],
            "instructions": "Cook pasta, mix with bacon and eggs",
            "prep_time": 10,
            "cook_time": 20
        }
        create_response = client.post("/recipes", json=recipe_data)
        assert create_response.status_code == 201
        recipe = create_response.json()
        recipe_id = recipe["id"]
        
        # Read
        get_response = client.get(f"/recipes/{recipe_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Spaghetti Carbonara"
        
        # Update
        update_data = {
            "description": "A delicious Italian pasta dish",
            "cook_time": 25
        }
        update_response = client.put(f"/recipes/{recipe_id}", json=update_data)
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["description"] == "A delicious Italian pasta dish"
        assert updated["cook_time"] == 25
        
        # List
        list_response = client.get("/recipes")
        assert list_response.status_code == 200
        recipes = list_response.json()["recipes"]
        assert len(recipes) == 1
        
        # Delete
        delete_response = client.delete(f"/recipes/{recipe_id}")
        assert delete_response.status_code == 204
        
        # Verify deleted
        get_response = client.get(f"/recipes/{recipe_id}")
        assert get_response.status_code == 404
    
    def test_multiple_recipes_workflow(self):
        """Test managing multiple recipes."""
        recipes_to_create = [
            {
                "title": "Pasta Carbonara",
                "ingredients": ["pasta", "eggs", "bacon"],
                "instructions": "Mix all together"
            },
            {
                "title": "Risotto",
                "ingredients": ["rice", "broth", "parmesan"],
                "instructions": "Stir and cook slowly"
            },
            {
                "title": "Tiramisu",
                "ingredients": ["mascarpone", "eggs", "cocoa"],
                "instructions": "Layer and chill"
            }
        ]
        
        created_ids = []
        for recipe_data in recipes_to_create:
            response = client.post("/recipes", json=recipe_data)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # Verify all were created
        list_response = client.get("/recipes")
        recipes = list_response.json()["recipes"]
        assert len(recipes) == 3
        
        # Update one
        client.put(f"/recipes/{created_ids[0]}", json={"cook_time": 30})
        
        # Delete one
        client.delete(f"/recipes/{created_ids[1]}")
        
        # Verify counts
        list_response = client.get("/recipes")
        recipes = list_response.json()["recipes"]
        assert len(recipes) == 2
