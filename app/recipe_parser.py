"""Parser for AI-generated recipes in JSON, markdown, and HTML formats."""

import json
import re
from typing import Optional, Union
from bs4 import BeautifulSoup
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
            servings=data.get("servings"),
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
        servings = None
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

        # Look for servings
        serv_match = re.search(r'Servings?:?\s*(\d+)', content, re.IGNORECASE)
        if serv_match:
            servings = int(serv_match.group(1))

        recipe = RecipeCreate(
            title=title,
            description=description,
            ingredients=ingredients,
            instructions=instructions_text,
            prep_time=prep_time,
            cook_time=cook_time,
            servings=servings,
            category=category,
            image_url=image_url,
        )
        
        return recipe
    except Exception as e:
        print(f"Error parsing markdown recipe: {e}")
        return None


def _parse_time_text(text: str) -> Optional[int]:
    """Parse a time string like '10 mins' or '1 hour 30 mins' into minutes."""
    total = 0
    hour_match = re.search(r'(\d+)\s*(?:hour|hr)', text, re.IGNORECASE)
    min_match = re.search(r'(\d+)\s*(?:min)', text, re.IGNORECASE)
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if min_match:
        total += int(min_match.group(1))
    return total if total else None


_UNIT_RE = re.compile(
    r'^(cups?|tablespoons?|teaspoons?|tbsp|tsp|'
    r'ounces?|oz|grams?|g|kilograms?|kg|'
    r'pounds?|lbs?|pinch(?:es)?|dashes?|'
    r'cloves?|cans?|jars?|slices?|bunches?|stalks?|heads?|bulbs?|units?|'
    r'large|medium|small|whole|handfuls?)\s+(.+)$',
    re.IGNORECASE,
)


def _is_section_header(text: str) -> bool:
    """Detect Paprika-style ingredient section headers like 'Sauce' or 'Stir Fry'."""
    # "see note N" pattern is always a header annotation
    if re.search(r'\bsee note\b', text, re.IGNORECASE):
        return True
    # Headers have no commas/parens, and every word starts with a capital
    if re.search(r'[,\(\)]', text):
        return False
    words = text.split()
    if not words or not all(w[0].isupper() for w in words if w):
        return False
    # Single capitalised word with no digits is ambiguous — only treat as header
    # if it's a known category word
    _CATEGORY_WORDS = {
        'sauce', 'marinade', 'dressing', 'topping', 'toppings', 'filling',
        'glaze', 'garnish', 'base', 'batter', 'coating', 'breading',
        'salsa', 'relish', 'rub', 'seasoning',
    }
    if len(words) == 1:
        return words[0].lower() in _CATEGORY_WORDS
    # Multi-word all-title-case with no digits → header
    return not re.search(r'\d', text)


def _parse_html_ingredient(el) -> Optional[Ingredient]:
    """Parse an ingredient <p> element using <strong> as the quantity base.
    Returns None for section headers."""
    strong = el.find('strong')
    if not strong:
        text = el.get_text(separator=' ', strip=True)
        if _is_section_header(text):
            return None
        parsed = parse_ingredient(text)
        return Ingredient(name=parsed['name'], quantity=parsed['quantity'] or None)

    qty_base = strong.get_text(strip=True)

    # Collect text that follows the <strong> tag
    tail_parts = []
    for sibling in strong.next_siblings:
        part = sibling.get_text(separator=' ', strip=True) if hasattr(sibling, 'get_text') else str(sibling).strip()
        if part:
            tail_parts.append(part)
    remaining = ' '.join(tail_parts).strip()

    # If remaining starts with a hyphen it's a compound descriptor like "1-inch piece ginger"
    if remaining.startswith('-') or remaining.startswith('–'):
        return Ingredient(name=qty_base + remaining)

    # Attach a leading unit from the tail to the quantity
    unit_match = _UNIT_RE.match(remaining)
    if unit_match:
        unit = unit_match.group(1)
        quantity = qty_base if re.fullmatch(r'units?', unit, re.IGNORECASE) else f"{qty_base} {unit}"
        name = unit_match.group(2).strip()
    else:
        quantity = qty_base
        name = remaining

    return Ingredient(name=name or qty_base, quantity=quantity or None)


def parse_recipe_html(content: str) -> Optional[RecipeCreate]:
    """Parse a recipe HTML page using schema.org microdata."""
    try:
        soup = BeautifulSoup(content, 'html.parser')

        # Title
        title_el = soup.find(attrs={'itemprop': 'name'}) or soup.find(class_='name')
        title = title_el.get_text(strip=True) if title_el else 'Untitled Recipe'

        # Ingredients
        ingredients = []
        for el in soup.find_all(attrs={'itemprop': 'recipeIngredient'}):
            ing = _parse_html_ingredient(el)
            if ing and ing.name:
                ingredients.append(ing)
        if not ingredients:
            ingredients = [Ingredient(name='See instructions')]

        # Instructions — join each <p> as its own step
        instructions = ''
        inst_el = soup.find(attrs={'itemprop': 'recipeInstructions'})
        if inst_el:
            steps = [p.get_text(strip=True) for p in inst_el.find_all('p') if p.get_text(strip=True)]
            instructions = '\n\n'.join(steps)

        # Times — fall back to totalTime as cook_time when prep/cook aren't separate
        prep_el = soup.find(attrs={'itemprop': 'prepTime'})
        prep_time = _parse_time_text(prep_el.get_text()) if prep_el else None

        cook_el = soup.find(attrs={'itemprop': 'cookTime'})
        cook_time = _parse_time_text(cook_el.get_text()) if cook_el else None

        if not prep_time and not cook_time:
            total_el = soup.find(attrs={'itemprop': 'totalTime'})
            cook_time = _parse_time_text(total_el.get_text()) if total_el else None

        # Source URL from itemprop="url", falling back to a bare URL in the notes
        source_url = None
        source_el = soup.find(attrs={'itemprop': 'url'})
        if source_el:
            source_url = source_el.get('href')
        if not source_url:
            notes_el = soup.find(attrs={'itemprop': 'comment'})
            if notes_el:
                url_match = re.search(r'https?://\S+', notes_el.get_text())
                if url_match:
                    source_url = url_match.group(0).rstrip('*')

        # Image — prefer the external href wrapping the photo, not the local src
        image_url = None
        img_el = soup.find('img', attrs={'itemprop': 'image'})
        if img_el:
            parent_a = img_el.find_parent('a')
            if parent_a and str(parent_a.get('href', '')).startswith('http'):
                image_url = parent_a['href']

        # Description from notes (skip if the notes are just a URL)
        description = ''
        notes_el = soup.find(attrs={'itemprop': 'comment'})
        if notes_el:
            notes_text = notes_el.get_text(strip=True)
            if not re.match(r'^https?://', notes_text):
                description = notes_text

        # Servings from recipeYield — prefer "N serving" pattern, else first integer
        servings = None
        yield_el = soup.find(attrs={'itemprop': 'recipeYield'})
        if yield_el:
            yield_text = yield_el.get_text(strip=True)
            m = re.search(r'(\d+)\s*servings?', yield_text, re.IGNORECASE)
            if m:
                servings = int(m.group(1))
            else:
                m = re.search(r'\b(\d+)\b', yield_text)
                if m and 1 <= int(m.group(1)) <= 100:
                    servings = int(m.group(1))

        return RecipeCreate(
            title=title,
            description=description,
            ingredients=ingredients,
            instructions=instructions,
            prep_time=prep_time,
            cook_time=cook_time,
            servings=servings,
            image_url=image_url,
            source_url=source_url,
        )
    except Exception as e:
        print(f"Error parsing HTML recipe: {e}")
        return None


def parse_recipe_content(content: str) -> Optional[RecipeCreate]:
    """
    Detect format and parse recipe content.

    Tries HTML first, then JSON, then markdown.
    """
    content = content.strip()

    # Detect HTML export
    if content.startswith('<!DOCTYPE') or content.lower().startswith('<html'):
        result = parse_recipe_html(content)
        if result:
            return result

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
