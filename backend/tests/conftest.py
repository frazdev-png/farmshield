import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Determine isolated test database URL
# Prioritize TEST_DATABASE_URL if configured; otherwise use dedicated isolated test db
TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or settings.TEST_DATABASE_URL

if not TEST_DB_URL:
    # Use dedicated isolated test database to protect development data
    test_db_file = (backend_path / "farmshield_test_isolated.db").as_posix()
    TEST_DB_URL = f"sqlite:///{test_db_file}"

test_engine_kwargs = {}
if TEST_DB_URL.startswith("sqlite"):
    test_engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }

test_engine = create_engine(TEST_DB_URL, **test_engine_kwargs)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Setup clean schema in isolated test database at session start and tear down at finish.
    Guarantees the development database is NEVER touched or reset.
    """
    settings.APP_ENV = "testing"
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if "farmshield_test_isolated.db" in TEST_DB_URL:
        test_file = Path(backend_path / "farmshield_test_isolated.db")
        if test_file.exists():
            try:
                test_file.unlink()
            except OSError:
                pass


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Yields a database session from the isolated test database."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Provides an isolated TestClient instance for each API integration test
    with get_db dependency overridden to the isolated test database.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
