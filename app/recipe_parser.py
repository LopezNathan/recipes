"""Parser for AI-generated recipes in JSON, markdown, and HTML formats."""

import json
import logging
import re

from bs4 import BeautifulSoup

from app.duration import minutes_to_duration
from app.models import RecipeCreate

logger = logging.getLogger(__name__)


def _parse_time_text(text: str) -> int | None:
    """Parse a time string like '10 mins' or '1 hour 30 mins' into minutes."""
    total = 0
    hour_match = re.search(r"(\d+)\s*(?:hour|hr)", text, re.IGNORECASE)
    min_match = re.search(r"(\d+)\s*(?:min)", text, re.IGNORECASE)
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if min_match:
        total += int(min_match.group(1))
    return total if total else None


def _ingredient_to_str(ing) -> str:
    """Convert various ingredient formats to a flat string."""
    if isinstance(ing, str):
        return ing.strip()
    if isinstance(ing, dict):
        name = (ing.get("name") or "").strip()
        qty = (ing.get("quantity") or "").strip()
        return f"{qty} {name}".strip() if qty else name
    return str(ing).strip()


def _is_section_header(text: str) -> bool:
    """Detect Paprika-style ingredient section headers like 'Sauce' or 'Stir Fry'."""
    if re.search(r"\bsee note\b", text, re.IGNORECASE):
        return True
    if re.search(r"[,\(\)]", text):
        return False
    words = text.split()
    if not words or not all(w[0].isupper() for w in words if w):
        return False
    _CATEGORY_WORDS = {
        "sauce",
        "marinade",
        "dressing",
        "topping",
        "toppings",
        "filling",
        "glaze",
        "garnish",
        "base",
        "batter",
        "coating",
        "breading",
        "salsa",
        "relish",
        "rub",
        "seasoning",
    }
    if len(words) == 1:
        return words[0].lower() in _CATEGORY_WORDS
    return not re.search(r"\d", text)


_UNIT_RE = re.compile(
    r"^(cups?|tablespoons?|teaspoons?|tbsp|tsp|"
    r"ounces?|oz|grams?|g|kilograms?|kg|"
    r"pounds?|lbs?|pinch(?:es)?|dashes?|"
    r"cloves?|cans?|jars?|slices?|bunches?|stalks?|heads?|bulbs?|units?|"
    r"large|medium|small|whole|handfuls?)\s+(.+)$",
    re.IGNORECASE,
)


def _parse_html_ingredient(el) -> str | None:
    """Parse an ingredient <p> element to a flat string. Returns None for section headers."""
    strong = el.find("strong")
    if not strong:
        text = el.get_text(separator=" ", strip=True)
        if _is_section_header(text):
            return None
        return text if text else None

    qty_base = strong.get_text(strip=True)

    tail_parts = []
    for sibling in strong.next_siblings:
        part = (
            sibling.get_text(separator=" ", strip=True)
            if hasattr(sibling, "get_text")
            else str(sibling).strip()
        )
        if part:
            tail_parts.append(part)
    remaining = " ".join(tail_parts).strip()

    if remaining.startswith("-") or remaining.startswith("–"):
        return qty_base + remaining

    unit_match = _UNIT_RE.match(remaining)
    if unit_match:
        unit = unit_match.group(1)
        quantity = (
            qty_base
            if re.fullmatch(r"units?", unit, re.IGNORECASE)
            else f"{qty_base} {unit}"
        )
        name = unit_match.group(2).strip()
    else:
        quantity = qty_base
        name = remaining

    if not name:
        return qty_base
    return f"{quantity} {name}".strip()


def parse_recipe_json(content: str) -> RecipeCreate | None:
    try:
        data = json.loads(content)

        raw_ingredients = data.get("ingredients") or data.get("recipeIngredient") or []
        ingredients = [_ingredient_to_str(i) for i in raw_ingredients if i]
        if not ingredients:
            ingredients = ["See instructions"]

        def _get_time(data, *keys):
            for k in keys:
                v = data.get(k)
                if v is not None:
                    if isinstance(v, str) and v.startswith("PT"):
                        return v
                    try:
                        return minutes_to_duration(int(v))
                    except (ValueError, TypeError):
                        pass
            return None

        recipe_yield = data.get("recipeYield") or data.get("servings")
        if isinstance(recipe_yield, int):
            recipe_yield = f"{recipe_yield} servings"

        recipe_category = data.get("recipeCategory") or data.get("category")
        if isinstance(recipe_category, str):
            recipe_category = [recipe_category] if recipe_category else None
        elif isinstance(recipe_category, list):
            recipe_category = recipe_category or None

        return RecipeCreate(
            name=data.get("name") or data.get("title") or "Untitled Recipe",
            description=data.get("description", ""),
            recipeIngredient=ingredients,
            recipeInstructions=data.get("recipeInstructions")
            or data.get("instructions")
            or "",
            prepTime=_get_time(data, "prepTime", "prep_time"),
            cookTime=_get_time(data, "cookTime", "cook_time"),
            recipeYield=str(recipe_yield) if recipe_yield else None,
            recipeCategory=recipe_category,
            recipeCuisine=data.get("recipeCuisine") or None,
            keywords=data.get("keywords") or None,
            image=data.get("image") or data.get("image_url"),
            url=data.get("url") or data.get("source_url"),
        )
    except json.JSONDecodeError as e:
        logger.warning("JSON parsing error: %s", e)
        return None
    except Exception as e:
        logger.warning("Error parsing recipe: %s", e)
        return None


def parse_recipe_markdown(content: str) -> RecipeCreate | None:
    try:
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        name = title_match.group(1).strip() if title_match else "Untitled Recipe"

        title_end = content.find("\n")
        if title_end != -1:
            desc_start = title_end + 1
            desc_end = content.find("\n##", desc_start)
            description = (
                content[desc_start:desc_end].strip()
                if desc_end != -1
                else content[desc_start:].strip()
            )
        else:
            description = ""

        ingredients = []
        ing_match = re.search(
            r"##\s*Ingredients\s*\n(.*?)(?=\n##|\Z)", content, re.IGNORECASE | re.DOTALL
        )
        if ing_match:
            for line in ing_match.group(1).split("\n"):
                line = re.sub(r"^[-\*]\s+|^\d+\.\s+", "", line.strip()).strip()
                if line:
                    ingredients.append(line)

        if not ingredients:
            ingredients = ["See instructions"]

        instructions_text = ""
        inst_match = re.search(
            r"##\s*Instructions\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if inst_match:
            instructions_text = re.sub(
                r"^\d+\.\s+", "", inst_match.group(1), flags=re.MULTILINE
            ).strip()

        prep_time = None
        cook_time = None
        servings = None
        category = None
        image = None

        prep_match = re.search(r"Prep\s*Time:?\s*(\d+)", content, re.IGNORECASE)
        if prep_match:
            prep_time = minutes_to_duration(int(prep_match.group(1)))

        cook_match = re.search(r"Cook\s*Time:?\s*(\d+)", content, re.IGNORECASE)
        if cook_match:
            cook_time = minutes_to_duration(int(cook_match.group(1)))

        cat_match = re.search(r"Category:?\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        if cat_match:
            category = [cat_match.group(1).strip()]

        img_match = re.search(
            r"Image(?:\s*URL)?:?\s*(https?://\S+)", content, re.IGNORECASE
        )
        if img_match:
            image = img_match.group(1)

        serv_match = re.search(r"Servings?:?\s*(\d+)", content, re.IGNORECASE)
        if serv_match:
            servings = f"{serv_match.group(1)} servings"

        return RecipeCreate(
            name=name,
            description=description,
            recipeIngredient=ingredients,
            recipeInstructions=instructions_text,
            prepTime=prep_time,
            cookTime=cook_time,
            recipeYield=servings,
            recipeCategory=category,
            image=image,
        )
    except Exception as e:
        logger.warning("Error parsing markdown recipe: %s", e)
        return None


def parse_recipe_html(content: str) -> RecipeCreate | None:
    """Parse a recipe HTML page using schema.org microdata."""
    try:
        soup = BeautifulSoup(content, "html.parser")

        title_el = soup.find(attrs={"itemprop": "name"}) or soup.find(class_="name")
        name = title_el.get_text(strip=True) if title_el else "Untitled Recipe"

        ingredients = []
        for el in soup.find_all(attrs={"itemprop": "recipeIngredient"}):
            ing = _parse_html_ingredient(el)
            if ing:
                ingredients.append(ing)
        if not ingredients:
            ingredients = ["See instructions"]

        instructions = ""
        inst_el = soup.find(attrs={"itemprop": "recipeInstructions"})
        if inst_el:
            steps = [
                p.get_text(strip=True)
                for p in inst_el.find_all("p")
                if p.get_text(strip=True)
            ]
            instructions = "\n\n".join(steps)

        prep_el = soup.find(attrs={"itemprop": "prepTime"})
        prep_time = (
            minutes_to_duration(_parse_time_text(prep_el.get_text()))
            if prep_el
            else None
        )

        cook_el = soup.find(attrs={"itemprop": "cookTime"})
        cook_time = (
            minutes_to_duration(_parse_time_text(cook_el.get_text()))
            if cook_el
            else None
        )

        if not prep_time and not cook_time:
            total_el = soup.find(attrs={"itemprop": "totalTime"})
            cook_time = (
                minutes_to_duration(_parse_time_text(total_el.get_text()))
                if total_el
                else None
            )

        url = None
        source_el = soup.find(attrs={"itemprop": "url"})
        if source_el:
            url = source_el.get("href")
        if not url:
            notes_el = soup.find(attrs={"itemprop": "comment"})
            if notes_el:
                url_match = re.search(r"https?://\S+", notes_el.get_text())
                if url_match:
                    url = url_match.group(0).rstrip("*")

        image = None
        img_el = soup.find("img", attrs={"itemprop": "image"})
        if img_el:
            parent_a = img_el.find_parent("a")
            if parent_a and str(parent_a.get("href", "")).startswith("http"):
                image = parent_a["href"]

        description = ""
        notes_el = soup.find(attrs={"itemprop": "comment"})
        if notes_el:
            notes_text = notes_el.get_text(strip=True)
            if not re.match(r"^https?://", notes_text):
                description = notes_text

        recipe_yield = None
        yield_el = soup.find(attrs={"itemprop": "recipeYield"})
        if yield_el:
            recipe_yield = yield_el.get_text(strip=True) or None

        recipe_category = None
        cat_el = soup.find(attrs={"itemprop": "recipeCategory"})
        if cat_el:
            recipe_category = [cat_el.get_text(strip=True)]

        return RecipeCreate(
            name=name,
            description=description,
            recipeIngredient=ingredients,
            recipeInstructions=instructions,
            prepTime=prep_time,
            cookTime=cook_time,
            recipeYield=recipe_yield,
            recipeCategory=recipe_category,
            image=image,
            url=url,
        )
    except Exception as e:
        logger.warning("Error parsing HTML recipe: %s", e)
        return None


def parse_recipe_content(content: str) -> RecipeCreate | None:
    """Detect format and parse recipe content. Tries HTML first, then JSON, then markdown."""
    content = content.strip()

    if content.startswith("<!DOCTYPE") or content.lower().startswith("<html"):
        result = parse_recipe_html(content)
        if result:
            return result

    if content.startswith("{"):
        result = parse_recipe_json(content)
        if result:
            return result

    if "#" in content or "ingredients" in content.lower():
        result = parse_recipe_markdown(content)
        if result:
            return result

    if content.startswith("{"):
        return None

    return parse_recipe_markdown(content)
