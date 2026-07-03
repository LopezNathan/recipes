"""Tests for app.scraper.scrape_recipe with a mocked recipe-scrapers backend.

These avoid any network I/O by patching scrape_me, so they exercise the
mapping from a scraper object to RecipeCreate (and the failure path).
"""

import app.scraper as scraper_module
from app.scraper import scrape_recipe


class _FakeScraper:
    def title(self):
        return "Test Recipe"

    def summary(self):
        return "A short description"

    def ingredients(self):
        return ["2 cups flour", "1 egg"]

    def instructions(self):
        return "Mix.\nBake."

    def image(self):
        return "https://example.com/img.jpg"

    def prep_time(self):
        return 10

    def cook_time(self):
        return 20

    def yields(self):
        return "4 servings"


async def test_scrape_recipe_maps_fields(monkeypatch):
    monkeypatch.setattr(scraper_module, "scrape_me", lambda url: _FakeScraper())

    recipe = await scrape_recipe("https://example.com/recipe")

    assert recipe is not None
    assert recipe.name == "Test Recipe"
    assert recipe.description == "A short description"
    assert recipe.recipeIngredient == ["2 cups flour", "1 egg"]
    assert recipe.recipeInstructions == "Mix.\nBake."
    assert recipe.prepTime == "PT10M"
    assert recipe.cookTime == "PT20M"
    assert recipe.recipeYield == "4 servings"
    assert recipe.image == "https://example.com/img.jpg"
    assert recipe.url == "https://example.com/recipe"


async def test_scrape_recipe_joins_list_instructions(monkeypatch):
    class ListInstructions(_FakeScraper):
        def instructions(self):
            return ["Step one", "Step two"]

    monkeypatch.setattr(scraper_module, "scrape_me", lambda url: ListInstructions())

    recipe = await scrape_recipe("https://example.com/recipe")
    assert recipe.recipeInstructions == "Step one\nStep two"


async def test_scrape_recipe_defaults_empty_ingredients(monkeypatch):
    class NoIngredients(_FakeScraper):
        def ingredients(self):
            return []

    monkeypatch.setattr(scraper_module, "scrape_me", lambda url: NoIngredients())

    recipe = await scrape_recipe("https://example.com/recipe")
    assert recipe.recipeIngredient == ["See instructions"]


async def test_scrape_recipe_returns_none_on_error(monkeypatch):
    def boom(url):
        raise ValueError("no recipe found")

    monkeypatch.setattr(scraper_module, "scrape_me", boom)

    assert await scrape_recipe("https://example.com/recipe") is None
