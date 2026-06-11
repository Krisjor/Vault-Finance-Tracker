"""
Pytest fixtures.

Spin up a Flask test app with an in-memory SQLite DB so tests are
isolated and fast — they don't need PostgreSQL running.
"""
import os
import pytest

# Force testing config BEFORE importing the app
os.environ["FLASK_ENV"] = "testing"
os.environ["DATABASE_URL_TEST"] = "sqlite:///:memory:"

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Reset DB state between tests."""
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        yield _db
