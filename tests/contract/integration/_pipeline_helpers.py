"""
Shared pipeline helper for integration tests.

Both adversarial-scenario tests and idempotency tests run the same extraction
pipeline.  This module provides a single implementation to prevent the two test
files from drifting as the extraction surface grows.
"""

from sqlalchemy.orm import Session

from tests.fixtures.fixture_extractor import FixtureExtractor
from src.database.storage import (
    store_branch,
    store_commit,
    store_pull_request,
    store_languages,
)


def run_pipeline(session: Session, repo_id: str, extractor: FixtureExtractor) -> None:
    """Run branches → commits → PRs → languages for a single repository.

    Calls session.commit() once after all writes so callers get a clean
    committed state for subsequent reads or a second pass.
    """
    branches = extractor.get_branches(repo_id)
    default_branch = branches[0].name if branches else "main"

    for branch in branches:
        store_branch(session, repo_id, branch)
    session.flush()

    for commit_data in extractor.get_commits(repo_id):
        store_commit(session, repo_id, default_branch, commit_data)
    session.flush()

    for pr_data in extractor.get_pull_requests(repo_id):
        store_pull_request(session, repo_id, pr_data)
    session.flush()

    languages = extractor.get_languages(repo_id)
    if languages:
        store_languages(session, repo_id, languages)
        session.flush()

    session.commit()
