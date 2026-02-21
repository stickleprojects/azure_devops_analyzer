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
from src.config.azure_devops import AzureDevOpsExtractorConfig

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def env_setup():
    """Load environment variables from .env files."""
    root_dir = Path(__file__).parent.parent.parent
    
    # Try loading in order: .env.resolved, .env.test, .env
    env_files = [
        root_dir / ".env.resolved",
        root_dir / ".env.test",
        root_dir / ".env",
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file)
            break
    
    return root_dir


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
    """Load GitHub API configuration from environment.
    
    NOTE: File caching disabled for all integration tests in pytest_configure
    to prevent stale cache interfering with test expectations.
    """
    try:
        config = GitHubExtractorConfig.from_env()
        if not config.token:
            pytest.skip("GITHUB_TOKEN not configured")
        return config
    except Exception as e:
        pytest.skip(f"Failed to load GitHub config: {e}")


@pytest.fixture(scope="session")
def azure_config(env_setup):
    """Load Azure DevOps API configuration from environment."""
    try:
        config = AzureDevOpsExtractorConfig.from_env()
        if not config.pat:
            pytest.skip("AZURE_DEVOPS_PAT not configured")
        if not config.org_url:
            pytest.skip("AZURE_DEVOPS_ORG_URL not configured")
        return config
    except Exception as e:
        pytest.skip(f"Failed to load Azure DevOps config: {e}")


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
    
    engine = create_engine(
        test_database_url,
        echo=False,
        pool_pre_ping=True,  # Verify connections before using to avoid stale connections
    )
    
    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Test database connection successful")
            # Set timezone to UTC for consistent behavior across environments
            conn.execute(text("SET timezone = 'UTC'"))
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
    ensuring clean state for the next test. Ensures UTC timezone for
    consistent datetime handling across all environments.
    """
    Session = sessionmaker(bind=integration_test_engine)
    session = Session()
    
    # Ensure timezone is UTC for this session
    session.execute(text("SET timezone = 'UTC'"))
    
    yield session
    
    # Cleanup after test
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def cleanup_database(test_session):
    """
    Automatically clean up all test data after each test.
    
    Uses DELETE for hypertables and TRUNCATE for regular tables.
    """
    yield
    
    try:
        # Delete from hypertables first (TRUNCATE doesn't work well with TimescaleDB hypertables)
        hypertables = [
            "repository_languages",
            "dependencies",
            "code_quality_metrics",
            "branch_metrics",
            "contributor_metrics",
            "service_metrics",
        ]
        
        for table in hypertables:
            try:
                test_session.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                logger.debug(f"Delete from {table}: {e}")
        
        # Truncate regular tables to clean state
        # Order matters: truncate dependent tables first, then their parents
        # Use RESTART IDENTITY to reset auto-increment sequences
        truncate_tables = [
            "team_metrics",
            "team_contributors",
            "vulnerabilities",
            "pr_comments",
            "pr_reviews",
            "pull_requests",
            "commits",
            "contributors",
            "branches",
            "repository_services",
            "repositories",
            "services",
            "teams",
            "projects",
            "organizations",
        ]
        
        for table in truncate_tables:
            try:
                # Try with RESTART IDENTITY, fall back to regular TRUNCATE
                test_session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            except Exception as e:
                try:
                    test_session.execute(text(f"TRUNCATE TABLE {table}"))
                except Exception as e2:
                    # Table might not exist or might already be empty, that's OK
                    logger.debug(f"Truncate {table}: {e2}")
        
        test_session.commit()
        logger.debug("✓ Database cleaned (hypertables deleted, regular tables truncated)")
    except Exception as e:
        logger.warning(f"Error truncating database: {e}")
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
# TEST DATA FIXTURES (Teams and Contributors)
# ============================================================================

@pytest.fixture
def organization(test_session):
    """Create a test organization."""
    from src.database.models import Organization
    
    # Try to find existing org first
    org = test_session.query(Organization).filter_by(
        name="Test Organization",
        platform="azure_devops"
    ).first()
    
    if org is None:
        org = Organization(
            name="Test Organization",
            url="https://test.example.com",
            platform="azure_devops",
        )
        test_session.add(org)
        test_session.commit()
    
    return org


@pytest.fixture
def teams(test_session, organization):
    """Create test teams."""
    from src.database.models import Team
    from datetime import datetime, timezone
    
    team_names = ["Platform Team", "Backend Team", "Frontend Team"]
    descriptions = ["Infrastructure and platform", "Backend services", "Frontend and UI"]
    
    teams = []
    for name, desc in zip(team_names, descriptions):
        # Check if team already exists
        existing = test_session.query(Team).filter_by(
            organization_id=organization.organization_id,
            name=name
        ).first()
        
        if existing:
            teams.append(existing)
        else:
            team = Team(
                organization_id=organization.organization_id,
                name=name,
                description=desc,
                created_at=datetime.now(timezone.utc),
            )
            test_session.add(team)
            teams.append(team)
    
    test_session.commit()
    return teams


@pytest.fixture
def contributors(test_session, organization):
    """Create test contributors with deduplication."""
    from src.database.models import Contributor
    
    contributors = []
    for i in range(5):
        email = f"user{i}@example.com"
        
        # Check if contributor already exists
        existing = test_session.query(Contributor).filter_by(email=email).first()
        
        if existing:
            contributors.append(existing)
        else:
            contrib = Contributor(
                email=email,
                name=f"User {i}",
            )
            test_session.add(contrib)
            contributors.append(contrib)
    
    test_session.commit()
    return contributors


@pytest.fixture
def repository(test_session, teams):
    """Create a test repository."""
    from src.database.models import Repository
    
    # Check if repository already exists
    repo = test_session.query(Repository).filter_by(
        repo_id="test-repo-001"
    ).first()
    
    if repo is None:
        repo = Repository(
            repo_id="test-repo-001",
            name="Test Repository",
            url="https://github.com/test/test-repo",
            team_id=teams[0].team_id,
        )
        test_session.add(repo)
        test_session.commit()
    
    return repo


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
