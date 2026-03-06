"""Parser for AI-generated recipes in JSON and markdown-style formats."""

import json
import re
from typing import Optional, Union
from models import RecipeCreate, Ingredient


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
                # Remove markdown list markers
                line = re.sub(r'^[\-\*\d+\.]\s+', '', line).strip()
                if line:
                    ingredients.append(Ingredient(name=line))
        
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
