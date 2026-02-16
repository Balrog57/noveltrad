"""
Shared test fixtures for NovelTrad tests.
"""
import pytest
import os
import tempfile
from src.core.database import init_db, db, Project


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    init_db(path)
    yield path
    db.close()
    os.unlink(path)


@pytest.fixture
def sample_project(temp_db):
    """Create a sample project in the temp database."""
    project = Project.create(
        name="Test Project",
        source_language="en",
        target_language="fr",
        genre="general",
    )
    return project
