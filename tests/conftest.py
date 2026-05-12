"""Shared test fixtures."""

import asyncio
import asyncpg
import os
import pytest
from fastapi.testclient import TestClient

import main
from database import CREATE_TABLE_SQL
from db import PostgresRecipeDatabase

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://localhost/recipes_test")


@pytest.fixture
def client():
    """Create test client with a fresh Postgres table for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def setup():
        pool = await asyncpg.create_pool(TEST_DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS recipes")
            await conn.execute(CREATE_TABLE_SQL)
        return pool

    pool = loop.run_until_complete(setup())

    async def override_get_recipe_db():
        async with pool.acquire() as conn:
            yield PostgresRecipeDatabase(conn)

    main.app.dependency_overrides[main.get_recipe_db] = override_get_recipe_db
    test_client = TestClient(main.app)
    yield test_client

    async def teardown():
        await pool.close()

    loop.run_until_complete(teardown())
    main.app.dependency_overrides.clear()
