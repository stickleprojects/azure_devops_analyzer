"""
Integration Test Fixtures

Provides database setup, GitHub API configuration, and session management
for end-to-end integration tests that verify actual data pipelines.
"""

import os
import pytest
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from src.database.models import Base
from src.config.github import GitHubExtractorConfig

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def env_setup():
    """Load environment variables from .env.resolved."""
    env_file = Path(__file__).parent.parent.parent / ".env.resolved"
    
    if not env_file.exists():
        # Fall back to .env if .resolved doesn't exist
        env_file = Path(__file__).parent.parent.parent / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
    
    return env_file


@pytest.fixture(scope="session")
def test_database_url(env_setup):
    """Get test database URL from environment."""
    db_url = os.environ.get(
        "TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "")
    )
    
    if not db_url:
        pytest.skip(
            "TEST_DATABASE_URL not configured. "
            "Set in .env or environment variable."
        )
    
    # Ensure it's a test database (safety check)
    if "test" not in db_url.lower() and "dev" not in db_url.lower():
        pytest.skip(
            f"Database URL must contain 'test' or 'dev': {db_url}. "
            "Refusing to run integration tests against production."
        )
    
    return db_url


@pytest.fixture(scope="session")
def github_config(env_setup):
    """Load GitHub API configuration from environment."""
    try:
        config = GitHubExtractorConfig.from_env()
        if not config.token:
            pytest.skip("GITHUB_TOKEN not configured")
        return config
    except Exception as e:
        pytest.skip(f"Failed to load GitHub config: {e}")


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def integration_test_engine(test_database_url):
    """
    Create database engine for integration tests.
    
    Creates the database and all tables at session start.
    Drops all tables at session end.
    """
    logger.info(f"Creating test database engine: {test_database_url[:50]}...")
    
    engine = create_engine(test_database_url, echo=False)
    
    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Test database connection successful")
    except Exception as e:
        pytest.fail(f"Failed to connect to test database: {e}")
    
    # Create all tables from models
    logger.info("Creating database schema...")
    Base.metadata.create_all(engine)
    logger.info("✓ Database schema created")
    
    yield engine
    
    # Cleanup: Drop all tables
    logger.info("Cleaning up test database...")
    try:
        # Drop entire schema to avoid FK dependency errors during teardown
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
        logger.info("✓ Dropped and recreated public schema")
    except Exception as e:
        logger.warning(f"Schema drop failed, falling back to metadata drop: {e}")
        Base.metadata.drop_all(engine)
    finally:
        engine.dispose()
        logger.info("✓ Test database cleanup complete")


@pytest.fixture
def test_session(integration_test_engine):
    """
    Provide a clean database session for each test.
    
    Each test gets an isolated session that is rolled back after the test,
    ensuring clean state for the next test.
    """
    Session = sessionmaker(bind=integration_test_engine)
    session = Session()
    
    yield session
    
    # Cleanup after test
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def cleanup_database(test_session):
    """
    Automatically clean up all test data after each test.
    
    Deletes test data in reverse order of foreign key dependencies.
    """
    yield
    
    # Delete in reverse order to respect FK constraints
    try:
        from src.database.models import (
            Vulnerability, Dependency,
            Commit, Contributor, Branch, Repository
        )
        
        test_session.query(Vulnerability).delete()
        test_session.query(Dependency).delete()
        test_session.query(Commit).delete()
        test_session.query(Contributor).delete()
        test_session.query(Branch).delete()
        test_session.query(Repository).delete()
        test_session.commit()
        
        logger.debug("✓ Test data cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning up test data: {e}")
        test_session.rollback()


# ============================================================================
# API MOCKING FIXTURES (Optional - for rate limit avoidance)
# ============================================================================

@pytest.fixture
def mock_osv_client():
    """
    Mock OSV.dev client for tests that want to avoid rate limits.
    
    Use this fixture when you want to test enrichment logic without
    calling the real OSV.dev API.
    """
    from unittest.mock import Mock
    from src.analyzers.osv_client import OSVClient
    
    mock = Mock(spec=OSVClient)
    
    # Default mock behavior - return None (no vulnerabilities found)
    mock.get_package_info.return_value = {
        "vulnerabilities": [],
        "latest_version": "1.0.0"
    }
    
    return mock


@pytest.fixture
def mock_eol_client():
    """
    Mock endoflife.date client for tests that want to avoid rate limits.
    
    Use this fixture when you want to test EOL detection without
    calling the real endoflife.date API.
    """
    from unittest.mock import Mock
    from src.analyzers.eol_client import EndOfLifeClient
    
    mock = Mock(spec=EndOfLifeClient)
    
    # Default mock behavior - return None (no EOL found)
    mock.get_eol_date.return_value = None
    mock.is_eol.return_value = False
    
    return mock


# ============================================================================
# PYTEST HOOKS AND CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Register custom markers for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: end-to-end integration tests requiring live database"
    )
    config.addinivalue_line(
        "markers",
        "slow: slow integration tests (30+ seconds)"
    )
    config.addinivalue_line(
        "markers",
        "live_api: tests using live GitHub/OSV APIs (may hit rate limits)"
    )


@pytest.fixture(scope="session", autouse=True)
def log_test_info(test_database_url):
    """Log test configuration at start."""
    logger.info("=" * 70)
    logger.info("INTEGRATION TEST SESSION STARTING")
    logger.info("=" * 70)
    logger.info(f"Test Database: {test_database_url[:60]}...")
    logger.info("=" * 70)
    
    yield
    
    logger.info("=" * 70)
    logger.info("INTEGRATION TEST SESSION COMPLETE")
    logger.info("=" * 70)
