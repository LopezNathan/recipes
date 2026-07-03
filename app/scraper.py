"""Recipe scraper utility for importing recipes from URLs."""

import asyncio
import logging

from recipe_scrapers import scrape_me
from app.models import RecipeCreate
from app.duration import minutes_to_duration
from typing import Optional

logger = logging.getLogger(__name__)


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

        prepTime = minutes_to_duration(scraper.prep_time())
        cookTime = minutes_to_duration(scraper.cook_time())

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
        logger.warning("Error scraping recipe from %s: %s", url, e)
        return None
