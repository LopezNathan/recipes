"""PostgreSQL database setup with asyncpg."""

import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/recipes")

_pool: Optional[asyncpg.Pool] = None

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS recipes (
        id          SERIAL PRIMARY KEY,
        title       VARCHAR(255) NOT NULL,
        description TEXT,
        ingredients JSONB NOT NULL,
        instructions TEXT NOT NULL,
        prep_time   INTEGER,
        cook_time   INTEGER,
        category    VARCHAR(100),
        image_url   VARCHAR(500),
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_recipes_title      ON recipes (title);
    CREATE INDEX IF NOT EXISTS idx_recipes_category   ON recipes (category);
    CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes (created_at DESC);
"""


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
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
