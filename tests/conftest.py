"""Shared test fixtures."""

import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

import app.database as db_module
import main
from app.database import CREATE_TABLE_SQL

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://localhost/recipes_test"
)


async def _reset_table():
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        await conn.execute("DROP TABLE IF EXISTS recipes")
        await conn.execute(CREATE_TABLE_SQL)
    finally:
        await conn.close()


@pytest.fixture(autouse=True)
def mock_validate_image_url(monkeypatch):
    async def passthrough(url, timeout=4.0):
        return url

    monkeypatch.setattr("main.validate_image_url", passthrough)


@pytest.fixture
def client():
    asyncio.run(_reset_table())

    db_module.DATABASE_URL = TEST_DATABASE_URL
    db_module._use_ssl = False
    db_module._pool = None

    with TestClient(main.app) as test_client:
        yield test_client

    db_module._pool = None


@pytest.fixture
def public_client():
    """TestClient bound to the read-only public_app."""
    asyncio.run(_reset_table())

    db_module.DATABASE_URL = TEST_DATABASE_URL
    db_module._use_ssl = False
    db_module._pool = None

    with TestClient(main.public_app) as test_client:
        yield test_client

    db_module._pool = None
