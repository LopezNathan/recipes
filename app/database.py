"""PostgreSQL database setup with asyncpg."""

import asyncpg
import os
import ssl
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)  # local overrides for dev

_raw_url = os.getenv("DATABASE_URL", "postgresql://localhost/recipes")

# asyncpg doesn't parse sslmode from the DSN — strip it and pass ssl explicitly
_use_ssl = "sslmode=" in _raw_url
DATABASE_URL = _raw_url.split("?")[0] if "?" in _raw_url else _raw_url

_pool: Optional[asyncpg.Pool] = None

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

    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='title') THEN
            ALTER TABLE recipes RENAME COLUMN title TO name;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='ingredients') THEN
            ALTER TABLE recipes RENAME COLUMN ingredients TO recipe_ingredient;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='instructions') THEN
            ALTER TABLE recipes RENAME COLUMN instructions TO recipe_instructions;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='servings') THEN
            ALTER TABLE recipes RENAME COLUMN servings TO recipe_yield;
            ALTER TABLE recipes ALTER COLUMN recipe_yield TYPE VARCHAR(50)
                USING CASE WHEN recipe_yield IS NOT NULL THEN recipe_yield::text || ' servings' ELSE NULL END;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='category') THEN
            ALTER TABLE recipes RENAME COLUMN category TO recipe_category;
            ALTER TABLE recipes ALTER COLUMN recipe_category TYPE JSONB
                USING CASE WHEN recipe_category IS NOT NULL THEN jsonb_build_array(recipe_category) ELSE NULL END;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='image_url') THEN
            ALTER TABLE recipes RENAME COLUMN image_url TO image;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='source_url') THEN
            ALTER TABLE recipes RENAME COLUMN source_url TO url;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='created_at') THEN
            ALTER TABLE recipes RENAME COLUMN created_at TO date_published;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='updated_at') THEN
            ALTER TABLE recipes RENAME COLUMN updated_at TO date_modified;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='recipes' AND column_name='prep_time' AND data_type='integer') THEN
            ALTER TABLE recipes ALTER COLUMN prep_time TYPE VARCHAR(20)
                USING CASE WHEN prep_time IS NOT NULL THEN 'PT' || prep_time || 'M' ELSE NULL END;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='recipes' AND column_name='cook_time' AND data_type='integer') THEN
            ALTER TABLE recipes ALTER COLUMN cook_time TYPE VARCHAR(20)
                USING CASE WHEN cook_time IS NOT NULL THEN 'PT' || cook_time || 'M' ELSE NULL END;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='recipe_cuisine') THEN
            ALTER TABLE recipes ADD COLUMN recipe_cuisine JSONB;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recipes' AND column_name='keywords') THEN
            ALTER TABLE recipes ADD COLUMN keywords JSONB;
        END IF;
    END $$;

    UPDATE recipes
    SET recipe_ingredient = (
        SELECT jsonb_agg(
            CASE
                WHEN jsonb_typeof(elem) = 'object' THEN
                    CASE
                        WHEN elem->>'quantity' IS NOT NULL AND trim(elem->>'quantity') != ''
                        THEN to_jsonb(trim(elem->>'quantity') || ' ' || trim(elem->>'name'))
                        ELSE to_jsonb(trim(elem->>'name'))
                    END
                ELSE elem
            END
        )
        FROM jsonb_array_elements(recipe_ingredient) AS elem
    )
    WHERE recipe_ingredient IS NOT NULL
      AND jsonb_array_length(recipe_ingredient) > 0
      AND jsonb_typeof(recipe_ingredient->0) = 'object';

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
