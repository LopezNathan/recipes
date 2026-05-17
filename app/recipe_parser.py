"""Parser for AI-generated recipes in JSON and markdown-style formats."""

import json
import re
from typing import Optional, Union
from app.models import RecipeCreate, Ingredient


def parse_ingredient(ingredient_str: str) -> dict:
    """
    Parse ingredient string to extract quantity and name.
    
    Handles multiple formats:
    - "2 cups flour" -> {"quantity": "2 cups", "name": "flour"}
    - "salt to taste" -> {"quantity": "", "name": "salt to taste"}
    - "dried pasta • 10 oz" -> {"quantity": "10 oz", "name": "dried pasta"}
    - "pound ground beef • 1" -> {"quantity": "1 pound", "name": "ground beef"}
    - "cloves garlic • 3" -> {"quantity": "3 cloves", "name": "garlic"}
    - "½ teaspoon salt" -> {"quantity": "½ teaspoon", "name": "salt"}
    - "2–3 cups tomato sauce" -> {"quantity": "2–3 cups", "name": "tomato sauce"}
    """
    ingredient_str = ingredient_str.strip()
    
    # Common unit words that appear in ingredient names
    unit_words = {
        'pound': 'pound', 'pounds': 'pound', 'lb': 'lb', 'lbs': 'lbs',
        'clove': 'clove', 'cloves': 'cloves',
        'cup': 'cup', 'cups': 'cups',
        'tablespoon': 'tablespoon', 'tablespoons': 'tablespoons', 'tbsp': 'tbsp',
        'teaspoon': 'teaspoon', 'teaspoons': 'teaspoons', 'tsp': 'tsp',
        'ounce': 'ounce', 'ounces': 'ounces', 'oz': 'oz',
        'gram': 'gram', 'grams': 'grams', 'g': 'g',
        'kilogram': 'kilogram', 'kilograms': 'kilograms', 'kg': 'kg',
        'milliliter': 'milliliter', 'milliliters': 'milliliters', 'ml': 'ml',
        'liter': 'liter', 'liters': 'liters', 'l': 'l',
        'pint': 'pint', 'pints': 'pints',
        'gallon': 'gallon', 'gallons': 'gallons',
        'pinch': 'pinch', 'pinches': 'pinches',
        'stick': 'stick', 'sticks': 'sticks',
        'slice': 'slice', 'slices': 'slices',
        'piece': 'piece', 'pieces': 'pieces',
        'head': 'head', 'heads': 'heads',
        'bulb': 'bulb', 'bulbs': 'bulbs',
        'stalk': 'stalk', 'stalks': 'stalks',
        'bunch': 'bunch', 'bunches': 'bunches',
        'small': 'small', 'medium': 'medium', 'large': 'large',
    }
    
    # If there's a bullet point, split on it and try to parse quantity from second part
    if '•' in ingredient_str:
        parts = ingredient_str.split('•')
        name_part = parts[0].strip()
        qty_part = parts[1].strip() if len(parts) > 1 else ""
        
        # Check if qty_part looks like a quantity (starts with number or fraction)
        if qty_part and re.match(r'^[\d½⅓¼⅔¾⅛⅜⅝⅞]', qty_part):
            # Check if name_part contains a unit word at the start
            name_words = name_part.lower().split()
            if name_words and name_words[0] in unit_words:
                # Move the unit word from name to quantity
                unit = name_words[0]
                remaining_name = ' '.join(name_words[1:])
                full_qty = f"{qty_part} {unit}"  # Use the original unit, not the mapped value
                return {"quantity": full_qty, "name": remaining_name}
            else:
                # Just use the qty_part as is
                return {"quantity": qty_part, "name": name_part}
    
    # Try to match quantity at the start
    # Supports: numbers, fractions (½, ¼, etc.), ranges (2-3, 2–3)
    # Units: cups, tbsp, tsp, oz, g, kg, ml, l, lbs, grams, cc, pints, gallons, teaspoons, tablespoons, pinch, pound, cloves, etc.
    match = re.match(
        r'^([\d\s\-–\/\.½⅓¼⅔¾⅛⅜⅝⅞]+\s*'
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
        
        # Make sure we actually captured a quantity
        if re.search(r'[\d½⅓¼⅔¾⅛⅜⅝⅞]', quantity):
            return {"quantity": quantity, "name": name}
    
    # No quantity found, entire string is the name
    return {"quantity": "", "name": ingredient_str}


def parse_recipe_json(content: str) -> Optional[RecipeCreate]:
    """
    Parse a recipe from JSON format.
    
    Expected format:
    {
        "title": "Recipe Title",
        "description": "Optional description",
        "ingredients": [
            {"name": "flour", "quantity": "2 cups"},
            "salt to taste"
        ],
        "instructions": "Step 1...\nStep 2...",
        "prep_time": 15,
        "cook_time": 30,
        "category": "dessert",
        "image_url": "https://..."
    }
    """
    try:
        data = json.loads(content)
        
        # Parse ingredients - support both strings and dicts
        ingredients = []
        if "ingredients" in data and data["ingredients"]:
            for ing in data["ingredients"]:
                if isinstance(ing, dict):
                    ingredients.append(Ingredient(**ing))
                elif isinstance(ing, str):
                    ingredients.append(Ingredient(name=ing))
        
        # Create recipe
        recipe = RecipeCreate(
            title=data.get("title", "Untitled Recipe"),
            description=data.get("description", ""),
            ingredients=ingredients if ingredients else [Ingredient(name="See instructions")],
            instructions=data.get("instructions", ""),
            prep_time=data.get("prep_time"),
            cook_time=data.get("cook_time"),
            category=data.get("category"),
            image_url=data.get("image_url"),
        )
        
        return recipe
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"Error parsing recipe: {e}")
        return None


def parse_recipe_markdown(content: str) -> Optional[RecipeCreate]:
    """
    Parse a recipe from markdown-style format.
    
    Expected format:
    # Recipe Title
    
    Description line (optional)
    
    ## Ingredients
    - 2 cups flour
    - 1 egg
    - salt to taste
    
    ## Instructions
    1. Mix dry ingredients
    2. Add wet ingredients
    3. Bake at 350°F for 30 minutes
    
    ## Metadata
    Prep Time: 15 minutes
    Cook Time: 30 minutes
    Category: Dessert
    """
    try:
        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Untitled Recipe"
        
        # Extract description (text after title, before first ## heading)
        # First find where the title ends
        title_end = content.find('\n')
        if title_end != -1:
            # Find the first ## section after the title
            desc_start = title_end + 1
            desc_end = content.find('\n##', desc_start)
            if desc_end == -1:
                # No ## sections, take everything after title
                description = content[desc_start:].strip()
            else:
                # Take text between title and first ## section
                description = content[desc_start:desc_end].strip()
        else:
            description = ""
        
        # Extract ingredients (between ## Ingredients and next ##)
        ingredients = []
        ing_match = re.search(
            r'##\s*Ingredients\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if ing_match:
            ing_text = ing_match.group(1)
            # Find all list items (- or * or numbers)
            for line in ing_text.split('\n'):
                line = line.strip()
                # Remove markdown list markers (-, *, or 1., 2., etc.)
                line = re.sub(r'^[-\*]\s+|^\d+\.\s+', '', line).strip()
                if line:
                    # Parse quantity and name (same as scraper.py)
                    parsed = parse_ingredient(line)
                    ingredients.append(Ingredient(name=parsed['name'], quantity=parsed['quantity']))
        
        if not ingredients:
            ingredients = [Ingredient(name="See instructions")]
        
        # Extract instructions (between ## Instructions and next ##)
        instructions_text = ""
        inst_match = re.search(
            r'##\s*Instructions\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if inst_match:
            inst_text = inst_match.group(1)
            # Remove markdown list markers but preserve line breaks
            instructions_text = re.sub(r'^\d+\.\s+', '', inst_text, flags=re.MULTILINE).strip()
        
        # Extract metadata
        prep_time = None
        cook_time = None
        category = None
        image_url = None
        
        # Look for prep time
        prep_match = re.search(
            r'Prep\s*Time:?\s*(\d+)',
            content,
            re.IGNORECASE
        )
        if prep_match:
            prep_time = int(prep_match.group(1))
        
        # Look for cook time
        cook_match = re.search(
            r'Cook\s*Time:?\s*(\d+)',
            content,
            re.IGNORECASE
        )
        if cook_match:
            cook_time = int(cook_match.group(1))
        
        # Look for category
        cat_match = re.search(
            r'Category:?\s*(.+?)(?:\n|$)',
            content,
            re.IGNORECASE
        )
        if cat_match:
            category = cat_match.group(1).strip()
        
        # Look for image URL
        img_match = re.search(
            r'Image(?:\s*URL)?:?\s*(https?://\S+)',
            content,
            re.IGNORECASE
        )
        if img_match:
            image_url = img_match.group(1)
        
        recipe = RecipeCreate(
            title=title,
            description=description,
            ingredients=ingredients,
            instructions=instructions_text,
            prep_time=prep_time,
            cook_time=cook_time,
            category=category,
            image_url=image_url,
        )
        
        return recipe
    except Exception as e:
        print(f"Error parsing markdown recipe: {e}")
        return None


def parse_recipe_content(content: str) -> Optional[RecipeCreate]:
    """
    Detect format and parse recipe content.
    
    Tries JSON first, then falls back to markdown format.
    """
    content = content.strip()
    
    # Try JSON first
    if content.startswith('{'):
        result = parse_recipe_json(content)
        if result:
            return result
    
    # Try markdown format
    if '#' in content or 'ingredients' in content.lower():
        result = parse_recipe_markdown(content)
        if result:
            return result
    
    # If content looks like JSON but failed to parse, return error
    if content.startswith('{'):
        return None
    
    # As last resort, try markdown again
    return parse_recipe_markdown(content)
