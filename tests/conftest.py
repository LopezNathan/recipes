"""Shared test fixtures."""

import asyncio
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import main
from database import Base
from db import SQLiteRecipeDatabase


@pytest.fixture
def client():
    """Create test client with a fresh SQLite database for each test."""
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(db_path)  # Remove the file so SQLite creates it fresh

    # Create fresh event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Setup database
        async def setup():
            engine = create_async_engine(
                f"sqlite+aiosqlite:///{db_path}",
                connect_args={"check_same_thread": False},
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return engine
        
        engine = loop.run_until_complete(setup())
        
        # Create session factory
        TestSessionLocal = async_sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Override dependency
        async def override_get_recipe_db():
            async with TestSessionLocal() as session:
                return SQLiteRecipeDatabase(session)
        
        main.app.dependency_overrides[main.get_recipe_db] = override_get_recipe_db
        
        # Create and yield client
        test_client = TestClient(main.app)
        yield test_client
        
    finally:
        # Cleanup
        async def teardown():
            await engine.dispose()
        
        loop.run_until_complete(teardown())
        main.app.dependency_overrides.clear()
        loop.close()
        
        # Delete the temp database file
        try:
            os.unlink(db_path)
        except:
            pass
