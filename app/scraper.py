"""Recipe scraper utility for importing recipes from URLs."""

import asyncio

from recipe_scrapers import scrape_me
from app.models import RecipeCreate
from typing import Optional


def _minutes_to_duration(minutes) -> Optional[str]:
    if minutes is None:
        return None
    minutes = int(minutes)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"PT{hours}H{mins}M"
    if hours:
        return f"PT{hours}H"
    return f"PT{mins}M"


async def scrape_recipe(url: str) -> Optional[RecipeCreate]:
    # scrape_me does synchronous network I/O — run it in a thread so the
    # event loop (and every other request) isn't blocked during the fetch.
    return await asyncio.to_thread(_scrape_recipe_sync, url)


def _scrape_recipe_sync(url: str) -> Optional[RecipeCreate]:
    try:
        scraper = scrape_me(url)

        title = scraper.title()
        description = scraper.summary() if hasattr(scraper, 'summary') else None
        ingredients = scraper.ingredients() or []
        instructions = scraper.instructions()
        image = scraper.image() if hasattr(scraper, 'image') else None

        prepTime = _minutes_to_duration(scraper.prep_time())
        cookTime = _minutes_to_duration(scraper.cook_time())

        recipeYield = None
        try:
            recipeYield = scraper.yields() or None
        except Exception:
            pass

        recipe = RecipeCreate(
            name=title,
            description=description or "",
            recipeIngredient=ingredients if ingredients else ["See instructions"],
            recipeInstructions=instructions if isinstance(instructions, str) else "\n".join(instructions) if instructions else "",
            prepTime=prepTime,
            cookTime=cookTime,
            recipeYield=recipeYield,
            image=image,
            url=url,
        )

        return recipe

    except Exception as e:
        print(f"Error scraping recipe from {url}: {str(e)}")
        return None
