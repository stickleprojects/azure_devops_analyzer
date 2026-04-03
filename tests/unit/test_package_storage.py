"""
Unit tests for package storage functions.

Tests store_package_metadata() and store_repo_dependencies() in isolation,
verifying that:
- Package-level metadata (EOL, latest version, vulnerabilities) goes to packages table
- Per-repo usage (has_known_vulnerabilities) goes to repository_dependencies
- Upsert semantics are correct
- Two repos using the same package produce one Package row and two RepositoryDependency rows
"""

import pytest
from datetime import datetime, timezone, date
from unittest.mock import MagicMock, patch, call

from src.database.storage import store_package_metadata, store_repo_dependencies
from src.analyzers.dependency_enricher import EnrichedDependency, PackageMetadata


def _make_session():
    """Return a minimal mock session."""
    session = MagicMock()
    return session


class TestStorePackageMetadata:

    def test_creates_new_package_row(self):
        """store_package_metadata() inserts a Package when none exists."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        store_package_metadata(
            session,
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.31.0",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[],
        )

        session.add.assert_called()
        added_obj = session.add.call_args_list[0][0][0]
        assert added_obj.package_name == "requests"
        assert added_obj.ecosystem == "pypi"
        assert added_obj.latest_version == "2.31.0"
        assert added_obj.is_eol is False

    def test_updates_existing_package_row(self):
        """store_package_metadata() updates fields when a matching Package exists."""
        from src.database.models.package import Package
        existing = Package(
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.28.0",
            is_eol=False,
        )
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        store_package_metadata(
            session,
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.31.0",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[],
        )

        assert existing.latest_version == "2.31.0"
        assert existing.enriched_at is not None

    def test_does_not_store_has_known_vulnerabilities(self):
        """store_package_metadata() must NOT set has_known_vulnerabilities (it's per-repo)."""
        from src.database.models.package import Package
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        pkg = store_package_metadata(
            session,
            package_name="lodash",
            ecosystem="npm",
            latest_version="4.17.21",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[],
        )

        assert not hasattr(pkg, "has_known_vulnerabilities")

    def test_stores_vulnerability_records(self):
        """store_package_metadata() adds Vulnerability rows linked via package_id."""
        from src.database.models.package import Package
        existing = Package(package_name="django", ecosystem="pypi", id=42)
        existing.vulnerabilities = []
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        vulns = [
            {
                "cve_id": "CVE-2023-1234",
                "osv_id": "GHSA-test",
                "severity": "high",
                "summary": "SQL injection",
                "fixed_in_versions": ["3.2.19"],
                "references": [],
            }
        ]

        store_package_metadata(
            session,
            package_name="django",
            ecosystem="pypi",
            latest_version="4.2.5",
            is_eol=False,
            eol_date=None,
            vulnerabilities=vulns,
        )

        # A Vulnerability row should have been added
        added_types = [type(c[0][0]).__name__ for c in session.add.call_args_list]
        assert "Vulnerability" in added_types

    def test_replaces_vulnerability_records_on_update(self):
        """store_package_metadata() deletes old vulns and adds fresh ones on upsert."""
        from src.database.models.package import Package

        old_vuln = MagicMock()
        existing = Package(package_name="flask", ecosystem="pypi", id=99)
        existing.vulnerabilities = [old_vuln]

        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        store_package_metadata(
            session,
            package_name="flask",
            ecosystem="pypi",
            latest_version="3.0.0",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[],
        )

        # Old vulnerability should have been deleted
        session.delete.assert_called_with(old_vuln)


class TestStoreRepoDependencies:

    def test_creates_new_repo_dep(self):
        """store_repo_dependencies() inserts a RepositoryDependency when none exists."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        enriched = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=True,
            )
        ]

        store_repo_dependencies(session, "test/repo", enriched)

        session.add.assert_called()
        added = session.add.call_args_list[0][0][0]
        assert added.package_name == "requests"
        assert added.has_known_vulnerabilities is True
        assert added.repo_id == "test/repo"

    def test_updates_existing_repo_dep(self):
        """store_repo_dependencies() updates has_known_vulnerabilities on existing row."""
        from src.database.models.dependency import RepositoryDependency
        existing = RepositoryDependency(
            repo_id="test/repo",
            package_name="requests",
            ecosystem="pypi",
            version="2.27.0",
            has_known_vulnerabilities=False,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )

        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        enriched = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=True,
            )
        ]

        store_repo_dependencies(session, "test/repo", enriched)

        assert existing.version == "2.28.0"
        assert existing.has_known_vulnerabilities is True

    def test_two_repos_one_package_independent_flags(self):
        """Two repos using the same package can have different has_known_vulnerabilities."""
        session_a = _make_session()
        session_a.query.return_value.filter_by.return_value.first.return_value = None

        session_b = _make_session()
        session_b.query.return_value.filter_by.return_value.first.return_value = None

        dep_a = [
            EnrichedDependency(
                package_name="lodash", ecosystem="npm", version="4.17.20",
                is_dev_dependency=False, source_file="package.json",
                version_constraint=None, has_known_vulnerabilities=True,
            )
        ]
        dep_b = [
            EnrichedDependency(
                package_name="lodash", ecosystem="npm", version="4.17.21",
                is_dev_dependency=False, source_file="package.json",
                version_constraint=None, has_known_vulnerabilities=False,
            )
        ]

        store_repo_dependencies(session_a, "test/repo-a", dep_a)
        store_repo_dependencies(session_b, "test/repo-b", dep_b)

        added_a = session_a.add.call_args_list[0][0][0]
        added_b = session_b.add.call_args_list[0][0][0]

        assert added_a.has_known_vulnerabilities is True
        assert added_b.has_known_vulnerabilities is False
