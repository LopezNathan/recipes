"""PostgreSQL database setup with asyncpg."""

import os
import ssl

import asyncpg
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)  # local overrides for dev

_raw_url = os.getenv("DATABASE_URL", "postgresql://localhost/recipes")

# asyncpg doesn't parse sslmode from the DSN — strip it and pass ssl explicitly
_use_ssl = "sslmode=" in _raw_url
DATABASE_URL = _raw_url.split("?")[0] if "?" in _raw_url else _raw_url

_pool: asyncpg.Pool | None = None

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS recipes (
        id                  SERIAL PRIMARY KEY,
        name                VARCHAR(255) NOT NULL,
        description         TEXT,
        recipe_ingredient   JSONB NOT NULL,
        recipe_instructions TEXT NOT NULL,
        prep_time           VARCHAR(20),
        cook_time           VARCHAR(20),
        recipe_yield        VARCHAR(50),
        recipe_category     JSONB,
        recipe_cuisine      JSONB,
        keywords            JSONB,
        image               VARCHAR(500),
        url                 VARCHAR(500),
        date_published      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_modified       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- The category/cuisine/keyword filters use jsonb_array_elements_text + lower(),
    -- which a default gin(recipe_category) index can't serve, so it was pure
    -- write-time overhead. Drop it (idempotent no-op once removed from prod).
    DROP INDEX IF EXISTS idx_recipes_recipe_category;

    CREATE INDEX IF NOT EXISTS idx_recipes_name           ON recipes (name);
    CREATE INDEX IF NOT EXISTS idx_recipes_date_published  ON recipes (date_published DESC);
"""


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        ssl_ctx = ssl.create_default_context() if _use_ssl else None
        _pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_ctx)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
