"""Recipe scraper utility for importing recipes from URLs."""

from recipe_scrapers import scrape_me
from app.models import RecipeCreate, Ingredient
from typing import Optional
import re


def parse_ingredient(ingredient_str: str) -> Ingredient:
    if not ingredient_str or not ingredient_str.strip():
        return Ingredient(name="")

    ingredient_str = ingredient_str.strip()

    # Remove cost info and parenthetical weight notes
    ingredient_str = re.sub(r'\s*\(\$[\d.]+\)', '', ingredient_str)
    ingredient_str = re.sub(r'\s*\([^)]*(?:about|lb|oz|kg|ml|cup|tbsp|tsp)[^)]*\)', '', ingredient_str)
    ingredient_str = ingredient_str.strip()

    match = re.match(
        r'^([\d\s/.\-–½⅓¼⅔¾⅛⅜⅝⅞]+\s*'
        r'(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|'
        r'ounces?|oz|grams?|g|mg|kilograms?|kg|'
        r'liters?|milliliters?|ml|l|'
        r'pounds?|lbs?|'
        r'pinch(?:es)?|dashes?|splashes?|drops?|'
        r'cloves?|cans?|jars?|loaves?|slices?|sheets?|'
        r'bunches?|stalks?|heads?|bulbs?|units?|'
        r'large|medium|small|whole|handfuls?|'
        r'to\s+taste)?'
        r')\s+(.+)$',
        ingredient_str,
        re.IGNORECASE
    )

    if match:
        quantity = match.group(1).strip()
        name = match.group(2).strip()
        if quantity and re.search(r'[\d½⅓¼⅔¾⅛⅜⅝⅞]', quantity) and name:
            return Ingredient(name=name, quantity=quantity)

    return Ingredient(name=ingredient_str)


async def scrape_recipe(url: str) -> Optional[RecipeCreate]:
    """
    Scrape a recipe from a URL and return a RecipeCreate model.
    
    Supports 900+ recipe websites including AllRecipes, Food Network, 
    BBC Good Food, Serious Eats, etc.
    
    Args:
        url: The URL of the recipe to scrape
        
    Returns:
        RecipeCreate object with scraped recipe data, or None if scraping fails
    """
    try:
        # Scrape the recipe - recipe_scrapers handles different website formats
        scraper = scrape_me(url)
        
        # Extract recipe data
        title = scraper.title()
        description = scraper.summary() if hasattr(scraper, 'summary') else None  # Some sites have this
        ingredients_list = scraper.ingredients()
        instructions = scraper.instructions()
        image_url = scraper.image() if hasattr(scraper, 'image') else None
        
        # Parse cook/prep times (returns minutes as int or None)
        cook_time = scraper.cook_time()
        prep_time = scraper.prep_time()
        
        # Convert ingredients to Ingredient objects
        ingredients = []
        if ingredients_list:
            for ing_str in ingredients_list:
                # Parse quantity and name from ingredient string
                ingredients.append(parse_ingredient(ing_str))
        
        # Create RecipeCreate model
        recipe = RecipeCreate(
            title=title,
            description=description or "",
            ingredients=ingredients if ingredients else [Ingredient(name="See instructions")],
            instructions=instructions if isinstance(instructions, str) else "\n".join(instructions) if instructions else "",
            prep_time=prep_time,
            cook_time=cook_time,
            image_url=image_url,
        )
        
        return recipe
        
    except Exception as e:
        print(f"Error scraping recipe from {url}: {str(e)}")
        return None

