"""Fixtures shared by every test. pytest finds this file automatically; tests never import it.

A fixture is a function that prepares something a test needs (a database, a client, a category).
A test asks for it just by naming it as a parameter, e.g. `def test_x(client, food): ...`.
"""

import os

# Set these BEFORE importing the app, because settings are read once at import time.
# Real environment variables win over .env, so the developer's .env is never used by tests:
# - DATABASE_URL: an in-memory database, so nothing can ever reach backend/spendwise.db.
# - Gemini: dummy values, so no test can use (or spend quota on) the real API key.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["GEMINI_MODEL"] = "test-model"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.db import get_session  # noqa: E402
from app.main import app  # noqa: E402  (importing it also registers every module's tables)
from app.modules import categories  # noqa: E402


@pytest.fixture
def engine():
    # A brand-new, empty database for every test, so tests can't affect each other.
    # StaticPool reuses one connection: with "sqlite://", every new connection would be a new, empty database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    yield engine
    # Everything after `yield` is clean-up, run when the test finishes (even if it failed).
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session):
    # Make every request in this test use the test's session instead of the app's real one.
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


# Ready-made categories, created through the categories module's public interface.
@pytest.fixture
def food(session) -> categories.CategoryRead:
    return categories.create_category(session, categories.CategoryCreate(name="Food", icon="utensils"))


@pytest.fixture
def travel(session) -> categories.CategoryRead:
    return categories.create_category(session, categories.CategoryCreate(name="Travel", icon="plane"))
