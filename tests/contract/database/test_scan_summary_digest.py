"""Contract tests for scan_summary digest writer behavior."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from src.database.storage import complete_extraction_run


def _insert_repository(db_session, repo_id: str) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO repositories (repo_id, name, url, is_active)
            VALUES (:repo_id, :name, :url, TRUE)
            """
        ),
        {
            "repo_id": repo_id,
            "name": repo_id,
            "url": f"https://example.com/{repo_id}",
        },
    )


def test_scan_summary_written_on_run_completion_and_idempotent(db_session):
    now = datetime.now(UTC)
    run_1 = uuid.uuid4()
    run_2 = uuid.uuid4()

    _insert_repository(db_session, "repo-a")
    _insert_repository(db_session, "repo-b")
    _insert_repository(db_session, "repo-c")

    db_session.execute(
        text(
            """
            INSERT INTO extraction_runs (
                run_id, platform, status, total_repositories, processed_repositories,
                started_at, updated_at, completed_at
            ) VALUES
                (:run_1, 'github', 'completed', 2, 2, :r1_started, :r1_completed, :r1_completed),
                (:run_2, 'github', 'running',   2, 2, :r2_started, :r2_started, NULL)
            """
        ),
        {
            "run_1": run_1,
            "run_2": run_2,
            "r1_started": now - timedelta(hours=6),
            "r1_completed": now - timedelta(hours=4),
            "r2_started": now - timedelta(hours=1),
        },
    )
    db_session.execute(
        text(
            """
            INSERT INTO extraction_metrics (
                run_id, repository_id, platform, status, extraction_started_at,
                extraction_completed_at, commits_extracted, pull_requests_extracted,
                branches_extracted, contributors_extracted, cache_hits, cache_misses,
                correlation_id
            ) VALUES
                (:run_1, 'repo-a', 'github', 'completed', :t1, :t1, 2, 0, 0, 1, 0, 0, :c1),
                (:run_1, 'repo-b', 'github', 'completed', :t2, :t2, 3, 0, 0, 2, 0, 0, :c2),
                (:run_2, 'repo-b', 'github', 'completed', :t3, :t3, 5, 0, 0, 2, 0, 0, :c3),
                (:run_2, 'repo-c', 'github', 'completed', :t4, :t4, 7, 0, 0, 1, 0, 0, :c4)
            """
        ),
        {
            "run_1": run_1,
            "run_2": run_2,
            "t1": now - timedelta(hours=6),
            "t2": now - timedelta(hours=5, minutes=30),
            "t3": now - timedelta(minutes=55),
            "t4": now - timedelta(minutes=45),
            "c1": uuid.uuid4(),
            "c2": uuid.uuid4(),
            "c3": uuid.uuid4(),
            "c4": uuid.uuid4(),
        },
    )
    db_session.execute(
        text(
            """
            INSERT INTO repository_dependencies (
                repo_id, package_name, ecosystem, is_dev_dependency, has_known_vulnerabilities,
                first_seen_at, last_seen_at
            ) VALUES
                ('repo-b', 'existing-lib', 'npm', FALSE, FALSE, :old_dep, :old_dep),
                ('repo-c', 'new-vuln-lib', 'npm', FALSE, TRUE, :new_dep, :new_dep)
            """
        ),
        {
            "old_dep": now - timedelta(hours=10),
            "new_dep": now - timedelta(minutes=30),
        },
    )
    db_session.commit()

    complete_extraction_run(db_session, run_2)
    db_session.commit()

    row = db_session.execute(
        text(
            """
            SELECT
                repos_scanned, new_repos, retired_repos,
                total_new_commits, contributors, new_libraries, new_vulnerabilities
            FROM scan_summary
            WHERE run_id = :run_id
            """
        ),
        {"run_id": run_2},
    ).one()

    assert row.repos_scanned == 2
    assert row.new_repos == 1
    assert row.retired_repos == 1
    assert row.total_new_commits == 12
    assert row.contributors == 3
    assert row.new_libraries == 1
    assert row.new_vulnerabilities == 1

    complete_extraction_run(db_session, run_2)
    db_session.commit()

    digest_rows = db_session.execute(
        text("SELECT COUNT(*) FROM scan_summary WHERE run_id = :run_id"),
        {"run_id": run_2},
    ).scalar_one()
    assert digest_rows == 1
