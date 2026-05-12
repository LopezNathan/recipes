"""Recipe scraper utility for importing recipes from URLs."""

from recipe_scrapers import scrape_me
from app.models import RecipeCreate, Ingredient
from typing import Optional
import re


def parse_ingredient(ingredient_str: str) -> Ingredient:
    """
    Parse an ingredient string into name and quantity.
    
    Attempts to extract quantity (e.g., "2 cups", "1 tsp", "3 cloves") from the 
    beginning of the ingredient string. Removes cost information in parentheses.
    Falls back to using the entire string as name if no quantity pattern is found.
    
    Args:
        ingredient_str: Full ingredient string like "2 cups flour ($1.50)" or "salt"
        
    Returns:
        Ingredient object with parsed name and quantity
    """
    if not ingredient_str or not ingredient_str.strip():
        return Ingredient(name="")
    
    ingredient_str = ingredient_str.strip()
    
    # Remove cost information in parentheses (e.g., "($1.50)")
    ingredient_str = re.sub(r'\s*\(\$[\d.]+\)', '', ingredient_str)
    
    # Remove size/weight info in parentheses (e.g., "(about 1 lb.)", "(4 oz.)")
    # Only match if parentheses contain measurement units
    ingredient_str = re.sub(r'\s*\([^)]*(?:about|lb|oz|kg|ml|cup|tbsp|tsp)[^)]*\)', '', ingredient_str)
    
    ingredient_str = ingredient_str.strip()
    
    # Pattern to match quantity formats:
    # 1. Number + unit (e.g., "2 cups", "1/2 tsp")
    # 2. Number + descriptor (e.g., "1 large", "3 small")
    # 3. Plain number + word (e.g., "1 lime", "3 cloves")
    # Match: number/fraction followed by space and either a known unit, descriptor, or just continue
    quantity_pattern = r'^([\d\s/.\-]+\s*(?:tsp|tbsp|cup|cups|oz|g|mg|ml|l|lb|pinch|dash|splash|drop|clove|cloves|can|jar|loaf|slice|sheet|bunch|stalk|head|bulb|large|medium|small|whole|handful|to\s+taste)(?:\s|$)|[\d]+(?:\s+(?:large|medium|small|whole|handful|tablespoon|teaspoon|clove|cloves))?(?:\s))'
    
    match = re.match(quantity_pattern, ingredient_str, re.IGNORECASE)
    
    if match:
        quantity = match.group(0).strip()
        # Only treat it as quantity if it contains a number
        if re.search(r'\d', quantity):
            # Remove the quantity from the ingredient string to get the name
            name = ingredient_str[len(quantity):].strip()
            if name:  # Only if there's text left after the quantity
                return Ingredient(name=name, quantity=quantity)
    
    # No quantity found, use entire string as name
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

