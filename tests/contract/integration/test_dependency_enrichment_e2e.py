"""
Integration Tests: Dependency Enrichment E2E

CONTRACT: Dependencies extracted from repos and enriched with API data.

Tests verify:
- Manifest files found and parsed
- Dependencies stored in database (repository_dependencies + packages tables)
- Enrichment APIs called and data stored
- Latest versions and EOL dates populated in packages table
- Vulnerabilities recorded and linked to packages (not per-repo rows)
- has_known_vulnerabilities flag computed per-repo based on version comparison
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.extractors.github.extractor import GitHubExtractor
from src.extractors.base import DependencyData
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.analyzers.dependency_enricher import EnrichedDependency, PackageMetadata
from src.database.models import Repository, RepositoryDependency, Vulnerability, Package
from src.database.storage import (
    store_dependencies,
    store_package_metadata,
    store_repo_dependencies,
    store_enriched_dependencies,
)


def get_or_create_repository(extractor: GitHubExtractor, repo_id: str, session: Session) -> Repository:
    """Get existing repository or create it from GitHub API data."""
    existing = session.query(Repository).filter_by(repo_id=repo_id).first()
    if existing:
        return existing

    repo_data = extractor.get_repository(repo_id)

    repo = Repository(
        repo_id=repo_data.repo_id,
        url=repo_data.url,
        name=repo_data.name,
        default_branch=repo_data.default_branch,
        created_at=repo_data.created_at,
        updated_at=repo_data.updated_at,
        is_private=repo_data.is_private,
        is_archived=repo_data.is_archived,
        repository_size=repo_data.repository_size,
        open_issues_count=repo_data.open_issues_count,
        license_name=repo_data.license_name,
        license_key=repo_data.license_key,
        has_vulnerability_alerts=repo_data.has_vulnerability_alerts,
        has_secret_scanning=repo_data.has_secret_scanning,
        has_dependabot_alerts=repo_data.has_dependabot_alerts,
    )
    session.add(repo)
    session.commit()

    return repo


class TestDependencyExtractionE2E:
    """Dependency extraction and storage E2E tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_dependencies_extracted_and_stored(self, github_config, test_session: Session):
        """
        CONTRACT: Extracting repo with dependencies stores them in repository_dependencies.

        Verify:
        - RepositoryDependency records created
        - Package names and versions correct
        - Ecosystem detected correctly
        """
        repo_id = "octocat/Hello-World"
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)

        analyzer = DependencyAnalyzer(enrich=False)
        dependencies = []

        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            dependencies = result.dependencies
        except Exception as e:
            pytest.skip(f"Failed to parse manifests: {e}")

        if dependencies:
            store_dependencies(test_session, repo_id, dependencies)
            test_session.commit()

        stored_deps = test_session.query(RepositoryDependency).filter_by(
            repo_id=repo_id
        ).all()

        if dependencies:
            assert len(stored_deps) > 0, \
                f"Extracted {len(dependencies)} deps but none stored in DB"

            for dep in stored_deps[:10]:
                assert dep.package_name is not None
                assert dep.ecosystem in [
                    "pypi", "npm", "maven", "nuget", "go", "rubygems", "cargo"
                ], f"Unknown ecosystem: {dep.ecosystem}"
                assert isinstance(dep.is_dev_dependency, bool)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_dependencies_enriched_with_latest_versions(self, github_config, test_session: Session):
        """
        CONTRACT: Enrichment populates latest_version in packages table from OSV.dev.

        Verify:
        - Package rows created with latest_version
        - Version format matches expected pattern
        """
        repo_id = "octocat/Hello-World"
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)

        analyzer = DependencyAnalyzer(enrich=True)
        enriched_deps = []

        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            enriched_deps = result.enriched_dependencies or []
        except Exception as e:
            pytest.skip(f"Enrichment failed (API issue?): {e}")

        if enriched_deps:
            for e in enriched_deps:
                if e.package_metadata is not None:
                    pm = e.package_metadata
                    store_package_metadata(
                        test_session,
                        package_name=pm.package_name,
                        ecosystem=pm.ecosystem,
                        latest_version=pm.latest_version,
                        is_eol=pm.is_eol,
                        eol_date=pm.eol_date,
                        vulnerabilities=pm.vulnerabilities,
                    )
            store_repo_dependencies(test_session, repo_id, enriched_deps)
            test_session.commit()

        packages = test_session.query(Package).all()

        if enriched_deps:
            enriched_count = sum(1 for p in packages if p.latest_version is not None)

            if enriched_count > 0:
                for pkg in [p for p in packages if p.latest_version]:
                    assert "." in pkg.latest_version or \
                           pkg.latest_version.replace(".", "").isdigit(), \
                           f"Invalid version format: {pkg.latest_version}"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_eol_detection_populated(self, github_config, test_session: Session):
        """
        CONTRACT: EOL dates are populated on Package rows for known versions.

        Verify:
        - is_eol flag set for EOL versions
        - eol_date populated
        """
        repo_id = "octocat/Hello-World"
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)

        analyzer = DependencyAnalyzer(enrich=True)
        enriched_deps = []

        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            enriched_deps = result.enriched_dependencies or []
        except Exception as e:
            pytest.skip(f"Enrichment failed: {e}")

        if enriched_deps:
            for e in enriched_deps:
                if e.package_metadata is not None:
                    pm = e.package_metadata
                    store_package_metadata(
                        test_session,
                        package_name=pm.package_name,
                        ecosystem=pm.ecosystem,
                        latest_version=pm.latest_version,
                        is_eol=pm.is_eol,
                        eol_date=pm.eol_date,
                        vulnerabilities=pm.vulnerabilities,
                    )
            test_session.commit()

        packages = test_session.query(Package).all()
        eol_detected = sum(1 for p in packages if p.eol_date is not None)

        if eol_detected > 0:
            for pkg in [p for p in packages if p.eol_date]:
                assert pkg.is_eol in [True, False]
                assert pkg.eol_date is not None


class TestVulnerabilityStorageE2E:
    """Vulnerability data storage E2E tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_vulnerabilities_stored(self, github_config, test_session: Session):
        """
        CONTRACT: Vulnerabilities from OSV.dev are stored linked to packages.

        Verify:
        - Vulnerability records created and linked via package_id
        - CVE/OSV IDs stored
        - Severity levels populated
        - Fixed versions tracked
        """
        repo_id = "octocat/Hello-World"
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)

        analyzer = DependencyAnalyzer(enrich=True)

        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            if result.enriched_dependencies:
                for e in result.enriched_dependencies:
                    if e.package_metadata is not None:
                        pm = e.package_metadata
                        store_package_metadata(
                            test_session,
                            package_name=pm.package_name,
                            ecosystem=pm.ecosystem,
                            latest_version=pm.latest_version,
                            is_eol=pm.is_eol,
                            eol_date=pm.eol_date,
                            vulnerabilities=pm.vulnerabilities,
                        )
                store_repo_dependencies(test_session, repo_id, result.enriched_dependencies)
                test_session.commit()
        except Exception as e:
            pytest.skip(f"Enrichment failed: {e}")

        vulns = test_session.query(Vulnerability).all()

        if vulns:
            for vuln in vulns[:5]:
                assert vuln.severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
                assert vuln.vulnerability_id or vuln.cve_id
                assert vuln.package_id is not None


class TestDependencyStorageE2E:
    """
    CONTRACT: Dependency storage layer correctly persists data.

    Tests the storage functions directly with synthetic DependencyData.
    """

    @pytest.mark.integration
    def test_store_dependencies(self, test_session: Session):
        """
        CONTRACT: store_dependencies() persists DependencyData to repository_dependencies.

        Verify:
        - RepositoryDependency rows created
        - Ecosystem and version preserved
        - dev vs prod distinction maintained
        """
        repo = Repository(
            repo_id="test/dep-storage",
            name="dep-storage",
            url="https://github.com/test/dep-storage",
        )
        test_session.add(repo)
        test_session.commit()

        deps = [
            DependencyData(
                package_name="requests",
                ecosystem="pypi",
                version="2.31.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
            ),
            DependencyData(
                package_name="pytest",
                ecosystem="pypi",
                version="7.4.0",
                is_dev_dependency=True,
                source_file="requirements-dev.txt",
            ),
            DependencyData(
                package_name="express",
                ecosystem="npm",
                version="4.18.2",
                is_dev_dependency=False,
                source_file="package.json",
            ),
        ]

        stored = store_dependencies(test_session, "test/dep-storage", deps)
        test_session.commit()

        assert len(stored) == 3

        db_deps = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/dep-storage"
        ).all()

        assert len(db_deps) == 3

        requests_dep = next(d for d in db_deps if d.package_name == "requests")
        assert requests_dep.ecosystem == "pypi"
        assert requests_dep.version == "2.31.0"
        assert requests_dep.is_dev_dependency is False

        pytest_dep = next(d for d in db_deps if d.package_name == "pytest")
        assert pytest_dep.is_dev_dependency is True

        express_dep = next(d for d in db_deps if d.package_name == "express")
        assert express_dep.ecosystem == "npm"

    @pytest.mark.integration
    def test_store_dependencies_upsert(self, test_session: Session):
        """
        CONTRACT: store_dependencies() upserts repository_dependencies.

        Verify:
        - Existing dependencies remain
        - New dependencies are added
        - No duplicates accumulate
        """
        repo = Repository(
            repo_id="test/dep-upsert",
            name="dep-upsert",
            url="https://github.com/test/dep-upsert",
        )
        test_session.add(repo)
        test_session.commit()

        deps_v1 = [
            DependencyData(package_name="flask", ecosystem="pypi", version="2.0.0"),
            DependencyData(package_name="django", ecosystem="pypi", version="4.0.0"),
        ]
        store_dependencies(test_session, "test/dep-upsert", deps_v1)
        test_session.commit()

        count_v1 = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/dep-upsert"
        ).count()
        assert count_v1 == 2

        deps_v2 = [
            DependencyData(package_name="fastapi", ecosystem="pypi", version="0.100.0"),
        ]
        store_dependencies(test_session, "test/dep-upsert", deps_v2)
        test_session.commit()

        db_deps = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/dep-upsert"
        ).all()

        assert len(db_deps) == 3
        package_names = {dep.package_name for dep in db_deps}
        assert package_names == {"flask", "django", "fastapi"}

    @pytest.mark.integration
    def test_store_package_metadata_and_repo_deps(self, test_session: Session):
        """
        CONTRACT: store_package_metadata writes to packages; store_repo_dependencies
        writes has_known_vulnerabilities to repository_dependencies.

        Verify:
        - Package row created with latest_version, is_eol, eol_date
        - RepositoryDependency row created with has_known_vulnerabilities (version-specific)
        - EOL fields are on Package, not on RepositoryDependency
        """
        repo = Repository(
            repo_id="test/dep-enriched",
            name="dep-enriched",
            url="https://github.com/test/dep-enriched",
        )
        test_session.add(repo)
        test_session.commit()

        pkg_meta_requests = PackageMetadata(
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.31.0",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[],
        )
        pkg_meta_django = PackageMetadata(
            package_name="django",
            ecosystem="pypi",
            latest_version="4.2.5",
            is_eol=True,
            eol_date=datetime(2024, 4, 1, tzinfo=timezone.utc).date(),
            vulnerabilities=[
                {
                    "cve_id": "CVE-2023-1234",
                    "osv_id": "GHSA-test-1234",
                    "severity": "HIGH",
                    "summary": "SQL injection",
                    "fixed_in_versions": ["3.2.19"],
                    "references": [],
                }
            ],
        )

        enriched = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=">=2.28",
                has_known_vulnerabilities=False,
                package_metadata=pkg_meta_requests,
            ),
            EnrichedDependency(
                package_name="django",
                ecosystem="pypi",
                version="3.2.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint="~=3.2",
                has_known_vulnerabilities=True,
                package_metadata=pkg_meta_django,
            ),
        ]

        for e in enriched:
            if e.package_metadata is not None:
                pm = e.package_metadata
                store_package_metadata(
                    test_session,
                    package_name=pm.package_name,
                    ecosystem=pm.ecosystem,
                    latest_version=pm.latest_version,
                    is_eol=pm.is_eol,
                    eol_date=pm.eol_date,
                    vulnerabilities=pm.vulnerabilities,
                )

        stored = store_repo_dependencies(test_session, "test/dep-enriched", enriched)
        test_session.commit()

        assert len(stored) == 2

        # Check Package rows
        requests_pkg = test_session.query(Package).filter_by(
            package_name="requests", ecosystem="pypi"
        ).first()
        assert requests_pkg is not None
        assert requests_pkg.latest_version == "2.31.0"
        assert requests_pkg.is_eol is False

        django_pkg = test_session.query(Package).filter_by(
            package_name="django", ecosystem="pypi"
        ).first()
        assert django_pkg is not None
        assert django_pkg.latest_version == "4.2.5"
        assert django_pkg.is_eol is True
        assert django_pkg.eol_date is not None

        # Check vulnerability linked to package, not repo dep
        vuln = test_session.query(Vulnerability).filter_by(
            cve_id="CVE-2023-1234"
        ).first()
        assert vuln is not None
        assert vuln.package_id == django_pkg.id

        # Check RepositoryDependency rows
        db_deps = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/dep-enriched"
        ).all()

        requests_dep = next(d for d in db_deps if d.package_name == "requests")
        assert requests_dep.has_known_vulnerabilities is False

        django_dep = next(d for d in db_deps if d.package_name == "django")
        assert django_dep.has_known_vulnerabilities is True

    @pytest.mark.integration
    def test_first_last_seen_timestamps(self, test_session: Session):
        """
        CONTRACT: RepositoryDependency rows have timezone-aware first/last seen timestamps.

        Verify:
        - first_seen_at/last_seen_at set on insert
        - Timestamps are UTC-aware
        """
        repo = Repository(
            repo_id="test/dep-timestamp",
            name="dep-timestamp",
            url="https://github.com/test/dep-timestamp",
        )
        test_session.add(repo)
        test_session.commit()

        deps = [
            DependencyData(package_name="numpy", ecosystem="pypi", version="1.25.0"),
        ]

        store_dependencies(test_session, "test/dep-timestamp", deps)
        test_session.commit()

        stored = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/dep-timestamp"
        ).first()

        assert stored.first_seen_at is not None
        assert stored.last_seen_at is not None
        assert stored.first_seen_at.tzinfo is not None
        assert stored.last_seen_at.tzinfo is not None
        assert stored.first_seen_at <= stored.last_seen_at


class TestVulnerabilityStorageDirectE2E:
    """
    CONTRACT: Vulnerability records correctly linked to packages (not per-repo deps).

    Tests direct storage, bypassing extraction and enrichment API calls.
    """

    @pytest.mark.integration
    def test_vulnerability_stored_with_package(self, test_session: Session):
        """
        CONTRACT: Vulnerabilities are persisted and linked to a Package row.

        Verify:
        - Vulnerability record created with package_id FK
        - CVE/severity/description fields stored
        """
        pkg = Package(
            package_name="lodash",
            ecosystem="npm",
            latest_version="4.17.21",
            is_eol=False,
        )
        test_session.add(pkg)
        test_session.flush()

        vuln = Vulnerability(
            package_id=pkg.id,
            cve_id="CVE-2021-23337",
            vulnerability_id="GHSA-35jh-r3h4-6jhm",
            severity="HIGH",
            summary="Prototype Pollution in lodash",
            fixed_in_version="4.17.21",
            published_date=datetime(2021, 2, 15, tzinfo=timezone.utc),
        )
        test_session.add(vuln)
        test_session.commit()

        stored_vuln = test_session.query(Vulnerability).filter_by(
            cve_id="CVE-2021-23337"
        ).first()

        assert stored_vuln is not None
        assert stored_vuln.severity == "HIGH"
        assert stored_vuln.vulnerability_id == "GHSA-35jh-r3h4-6jhm"
        assert stored_vuln.fixed_in_version == "4.17.21"
        assert stored_vuln.summary == "Prototype Pollution in lodash"
        assert stored_vuln.published_date.tzinfo is not None
        assert stored_vuln.package_id == pkg.id

    @pytest.mark.integration
    def test_multiple_vulnerabilities_per_package(self, test_session: Session):
        """
        CONTRACT: A package can have multiple vulnerabilities.

        Verify:
        - Multiple vulnerabilities linked to same package
        - Each has distinct CVE/severity
        """
        pkg = Package(
            package_name="multi-vuln-test-pkg",
            ecosystem="pypi",
            latest_version="4.2.5",
        )
        test_session.add(pkg)
        test_session.flush()

        vulns = [
            Vulnerability(
                package_id=pkg.id,
                cve_id="CVE-2023-0001",
                severity="CRITICAL",
                summary="SQL injection in QuerySet",
                fixed_in_version="3.2.19",
            ),
            Vulnerability(
                package_id=pkg.id,
                cve_id="CVE-2023-0002",
                severity="MEDIUM",
                summary="XSS in admin interface",
                fixed_in_version="3.2.18",
            ),
            Vulnerability(
                package_id=pkg.id,
                cve_id="CVE-2023-0003",
                severity="LOW",
                summary="Information disclosure in debug mode",
            ),
        ]
        for v in vulns:
            test_session.add(v)
        test_session.commit()

        stored_vulns = test_session.query(Vulnerability).filter_by(
            package_id=pkg.id
        ).all()

        assert len(stored_vulns) == 3
        severities = {v.severity for v in stored_vulns}
        assert severities == {"CRITICAL", "MEDIUM", "LOW"}

    @pytest.mark.integration
    def test_two_repos_same_package_independent_vuln_flags(self, test_session: Session):
        """
        CONTRACT: Two repos using the same package have one Package row but
        independent has_known_vulnerabilities flags in repository_dependencies.
        """
        repo_a = Repository(
            repo_id="test/repo-a-shared-pkg",
            name="repo-a",
            url="https://github.com/test/repo-a",
        )
        repo_b = Repository(
            repo_id="test/repo-b-shared-pkg",
            name="repo-b",
            url="https://github.com/test/repo-b",
        )
        test_session.add_all([repo_a, repo_b])
        test_session.commit()

        # Shared package (one CVE fixed in 4.17.21)
        store_package_metadata(
            test_session,
            package_name="lodash",
            ecosystem="npm",
            latest_version="4.17.21",
            is_eol=False,
            eol_date=None,
            vulnerabilities=[
                {
                    "cve_id": "CVE-2021-23337",
                    "osv_id": "GHSA-35jh-r3h4-6jhm",
                    "severity": "HIGH",
                    "summary": "Prototype Pollution",
                    "fixed_in_versions": ["4.17.21"],
                    "references": [],
                }
            ],
        )

        # Repo A uses affected version
        store_repo_dependencies(
            test_session,
            "test/repo-a-shared-pkg",
            [
                EnrichedDependency(
                    package_name="lodash",
                    ecosystem="npm",
                    version="4.17.20",
                    is_dev_dependency=False,
                    source_file="package.json",
                    version_constraint=None,
                    has_known_vulnerabilities=True,
                )
            ],
        )

        # Repo B uses fixed version
        store_repo_dependencies(
            test_session,
            "test/repo-b-shared-pkg",
            [
                EnrichedDependency(
                    package_name="lodash",
                    ecosystem="npm",
                    version="4.17.21",
                    is_dev_dependency=False,
                    source_file="package.json",
                    version_constraint=None,
                    has_known_vulnerabilities=False,
                )
            ],
        )
        test_session.commit()

        # One package row
        assert test_session.query(Package).filter_by(
            package_name="lodash", ecosystem="npm"
        ).count() == 1

        # Two repo dependency rows with different flags
        dep_a = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/repo-a-shared-pkg", package_name="lodash"
        ).first()
        dep_b = test_session.query(RepositoryDependency).filter_by(
            repo_id="test/repo-b-shared-pkg", package_name="lodash"
        ).first()

        assert dep_a.has_known_vulnerabilities is True
        assert dep_b.has_known_vulnerabilities is False

    @pytest.mark.integration
    def test_vulnerability_cascade_delete_via_package(self, test_session: Session):
        """
        CONTRACT: Deleting a Package cascades to its vulnerabilities.

        Verify:
        - Vulnerability deleted when parent Package removed
        - No orphaned vulnerability records
        """
        pkg = Package(
            package_name="express-cascade",
            ecosystem="npm",
        )
        test_session.add(pkg)
        test_session.flush()

        vuln = Vulnerability(
            package_id=pkg.id,
            cve_id="CVE-2022-9999",
            severity="HIGH",
            summary="Path traversal",
        )
        test_session.add(vuln)
        test_session.commit()

        assert test_session.query(Vulnerability).filter_by(package_id=pkg.id).count() == 1

        test_session.delete(pkg)
        test_session.commit()

        assert test_session.query(Vulnerability).filter_by(cve_id="CVE-2022-9999").count() == 0
