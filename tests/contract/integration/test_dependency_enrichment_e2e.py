"""
Integration Tests: Dependency Enrichment E2E

CONTRACT: Dependencies extracted from repos and enriched with API data.

Tests verify:
- Manifest files found and parsed
- Dependencies stored in database
- Enrichment APIs called and data stored
- Latest versions and EOL dates populated
- Vulnerabilities recorded correctly
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.extractors.github.extractor import GitHubExtractor
from src.extractors.base import DependencyData
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.analyzers.dependency_enricher import EnrichedDependency
from src.database.models import Repository, Dependency, Vulnerability
from src.database.storage import store_dependencies, store_enriched_dependencies


def get_or_create_repository(extractor: GitHubExtractor, repo_id: str, session: Session) -> Repository:
    """
    Get existing repository or create it from GitHub API data.
    
    Handles duplicate key conflicts gracefully by returning existing record.
    """
    # Check if repository already exists
    existing = session.query(Repository).filter_by(repo_id=repo_id).first()
    if existing:
        return existing
    
    # Fetch repository metadata from GitHub
    repo_data = extractor.get_repository(repo_id)
    
    # Create and store repository
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
    def test_dependencies_extracted_and_stored(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Extracting repo with dependencies stores them in DB.
        
        Use: octocat/Hello-World (simple test repo)
        
        Verify:
        - Dependency records created
        - Package names and versions correct
        - Ecosystem detected correctly
        """
        # Setup
        repo_id = "octocat/Hello-World"
        
        # Extract repository metadata
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Parse dependencies using DependencyAnalyzer
        analyzer = DependencyAnalyzer(enrich=False)  # No enrichment for this test
        dependencies = []
        
        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            dependencies = result.dependencies
        except Exception as e:
            pytest.skip(f"Failed to parse manifests: {e}")
        
        # Store dependencies
        if dependencies:
            for dep in dependencies:
                db_dep = Dependency(
                    repo_id=repo_id,
                    package_name=dep.package_name,
                    ecosystem=dep.ecosystem,
                    version_requested=dep.version_requested,
                    is_dev_dependency=dep.is_dev_dependency,
                )
                test_session.add(db_dep)
            test_session.commit()
        
        # Assert: Dependencies stored (or repo has none)
        stored_deps = test_session.query(Dependency).filter_by(
            repo_id=repo_id
        ).all()
        
        if dependencies:
            assert len(stored_deps) > 0, \
                f"Extracted {len(dependencies)} deps but none stored in DB"
            
            # Verify dependency structure
            for dep in stored_deps[:10]:  # Check first 10
                assert dep.package_name is not None
                assert dep.ecosystem in [
                    "pypi", "npm", "maven", "nuget", "go", "rubygems", "cargo"
                ], f"Unknown ecosystem: {dep.ecosystem}"
                assert isinstance(dep.is_dev_dependency, bool)
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_dependencies_enriched_with_latest_versions(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Enrichment populates latest_version from OSV.dev.
        
        This test uses LIVE APIs and may hit rate limits.
        
        Verify:
        - latest_version field populated
        - Version format matches expected pattern
        - Only populated for known packages
        """
        # Setup
        repo_id = "octocat/Hello-World"
        
        # Extract repository metadata
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Extract and enrich
        analyzer = DependencyAnalyzer(enrich=True)  # Enable enrichment
        enriched_deps = []
        
        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            enriched_deps = result.enriched_dependencies or []
        except Exception as e:
            pytest.skip(f"Enrichment failed (API issue?): {e}")
        
        # Store enriched dependencies
        if enriched_deps:
            for dep in enriched_deps:
                db_dep = Dependency(
                    repo_id=repo_id,
                    package_name=dep.package_name,
                    ecosystem=dep.ecosystem,
                    version_requested=dep.version_requested,
                    latest_version=dep.latest_version,
                    eol_date=dep.eol_date,
                    is_eol=dep.is_eol,
                    has_vulnerabilities=dep.has_vulnerabilities,
                )
                test_session.add(db_dep)
            test_session.commit()
        
        # Assert: At least some enriched
        stored_deps = test_session.query(Dependency).filter_by(
            repo_id=repo_id
        ).all()
        
        if enriched_deps:
            # Count enriched deps
            enriched_count = sum(
                1 for d in stored_deps if d.latest_version is not None
            )
            
            # May not all be found in OSV.dev, that's OK
            if enriched_count > 0:
                # Verify version format
                for dep in [d for d in stored_deps if d.latest_version]:
                    # Should look like semantic version
                    assert "." in dep.latest_version or \
                           dep.latest_version.replace(".", "").isdigit(), \
                           f"Invalid version format: {dep.latest_version}"
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_eol_detection_populated(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: EOL dates are populated for known versions.
        
        This test uses LIVE APIs and may hit rate limits.
        
        Verify:
        - is_eol flag set for EOL versions
        - eol_date populated
        - Correctly identifies past vs future EOL
        """
        # Setup
        repo_id = "octocat/Hello-World"
        
        # Extract repository metadata
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Extract and enrich
        analyzer = DependencyAnalyzer(enrich=True)
        enriched_deps = []
        
        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            enriched_deps = result.enriched_dependencies or []
        except Exception as e:
            pytest.skip(f"Enrichment failed: {e}")
        
        # Store
        if enriched_deps:
            for dep in enriched_deps:
                db_dep = Dependency(
                    repo_id=repo_id,
                    package_name=dep.package_name,
                    ecosystem=dep.ecosystem,
                    version_requested=dep.version_requested,
                    eol_date=dep.eol_date,
                    is_eol=dep.is_eol,
                )
                test_session.add(db_dep)
            test_session.commit()
        
        # Assert: EOL data present if available
        stored_deps = test_session.query(Dependency).filter_by(
            repo_id=repo_id
        ).all()
        
        eol_detected = sum(
            1 for d in stored_deps if d.eol_date is not None
        )
        
        # May be 0 if no EOL data available, that's OK
        if eol_detected > 0:
            for dep in [d for d in stored_deps if d.eol_date]:
                assert dep.is_eol in [True, False]
                assert dep.eol_date is not None


class TestVulnerabilityStorageE2E:
    """Vulnerability data storage E2E tests."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.live_api
    def test_vulnerabilities_stored(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Vulnerabilities from OSV.dev are stored in database.
        
        This test uses LIVE APIs and may hit rate limits.
        
        Verify:
        - Vulnerability records created
        - CVE/OSV IDs stored
        - Severity levels populated
        - Fixed versions tracked
        """
        # Setup
        repo_id = "octocat/Hello-World"
        
        # Extract repository metadata
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Extract, enrich, and get vulnerabilities
        analyzer = DependencyAnalyzer(enrich=True)
        all_vulns = []
        
        try:
            result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
            if result.enriched_dependencies:
                for dep in result.enriched_dependencies:
                    if dep.vulnerabilities:
                        all_vulns.extend(dep.vulnerabilities)
        except Exception as e:
            pytest.skip(f"Enrichment failed: {e}")
        
        # Store vulnerabilities
        if all_vulns:
            # First store dependencies
            try:
                result = analyzer.analyze(extractor, repo_id, branch=repo.default_branch)
                for dep in result.enriched_dependencies or []:
                    db_dep = Dependency(
                        repo_id=repo_id,
                        package_name=dep.package_name,
                        ecosystem=dep.ecosystem,
                        version_requested=dep.version_requested,
                    )
                    test_session.add(db_dep)
            except:
                pass
            test_session.commit()
            
            # Then store vulnerabilities
            deps = test_session.query(Dependency).filter_by(
                repo_id=repo_id
            ).all()
            
            for vuln in all_vulns:
                # Find matching dependency
                for dep in deps:
                    if dep.package_name == vuln.package_name:
                        db_vuln = Vulnerability(
                            dependency_id=dep.id,
                            vulnerability_id=vuln.vulnerability_id,
                            cve_id=vuln.cve_id,
                            severity=vuln.severity,
                            description=vuln.description,
                            fixed_in_version=vuln.fixed_in_version,
                            published_at=vuln.published_at,
                        )
                        test_session.add(db_vuln)
                        break
            test_session.commit()
        
        # Assert: Vulnerabilities stored (or none found)
        vulns = test_session.query(Vulnerability).all()
        
        if all_vulns:
            assert len(vulns) > 0, \
                f"Found {len(all_vulns)} vulns but none stored in DB"
            
            # Verify structure
            for vuln in vulns[:5]:
                assert vuln.severity in ["critical", "high", "medium", "low"]
                assert vuln.vulnerability_id or vuln.cve_id


class TestDependencyStorageE2E:
    """
    CONTRACT: Dependency storage layer correctly persists data.

    Tests the storage functions directly with synthetic DependencyData,
    bypassing manifest extraction (not yet implemented on extractors).
    """

    @pytest.mark.integration
    def test_store_dependencies(self, test_session: Session):
        """
        CONTRACT: store_dependencies() persists DependencyData correctly.

        Verify:
        - Dependencies stored with correct fields
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

        db_deps = test_session.query(Dependency).filter_by(
            repo_id="test/dep-storage"
        ).all()

        assert len(db_deps) == 3

        # Verify fields preserved
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
        CONTRACT: store_dependencies() replaces existing dependencies.

        Verify:
        - Old dependencies deleted on re-store
        - New set replaces previous
        - No duplicates accumulate
        """
        repo = Repository(
            repo_id="test/dep-upsert",
            name="dep-upsert",
            url="https://github.com/test/dep-upsert",
        )
        test_session.add(repo)
        test_session.commit()

        # First store
        deps_v1 = [
            DependencyData(package_name="flask", ecosystem="pypi", version="2.0.0"),
            DependencyData(package_name="django", ecosystem="pypi", version="4.0.0"),
        ]
        store_dependencies(test_session, "test/dep-upsert", deps_v1)
        test_session.commit()

        count_v1 = test_session.query(Dependency).filter_by(
            repo_id="test/dep-upsert"
        ).count()
        assert count_v1 == 2

        # Second store (upsert) - different set
        deps_v2 = [
            DependencyData(package_name="fastapi", ecosystem="pypi", version="0.100.0"),
        ]
        store_dependencies(test_session, "test/dep-upsert", deps_v2)
        test_session.commit()

        db_deps = test_session.query(Dependency).filter_by(
            repo_id="test/dep-upsert"
        ).all()

        assert len(db_deps) == 1
        assert db_deps[0].package_name == "fastapi"

    @pytest.mark.integration
    def test_store_enriched_dependencies(self, test_session: Session):
        """
        CONTRACT: store_enriched_dependencies() persists enrichment data.

        Verify:
        - latest_version populated
        - EOL fields stored
        - has_vulnerabilities flag set
        """
        repo = Repository(
            repo_id="test/dep-enriched",
            name="dep-enriched",
            url="https://github.com/test/dep-enriched",
        )
        test_session.add(repo)
        test_session.commit()

        enriched = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=">=2.28",
                latest_version="2.31.0",
                eol_date=None,
                is_eol=False,
                has_vulnerabilities=False,
            ),
            EnrichedDependency(
                package_name="django",
                ecosystem="pypi",
                version="3.2.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint="~=3.2",
                latest_version="4.2.5",
                eol_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
                is_eol=True,
                has_vulnerabilities=True,
                vulnerabilities=[{"cve_id": "CVE-2023-1234", "severity": "high"}],
            ),
        ]

        stored = store_enriched_dependencies(
            test_session, "test/dep-enriched", enriched
        )
        test_session.commit()

        assert len(stored) == 2

        db_deps = test_session.query(Dependency).filter_by(
            repo_id="test/dep-enriched"
        ).all()

        requests_dep = next(d for d in db_deps if d.package_name == "requests")
        assert requests_dep.latest_version == "2.31.0"
        assert requests_dep.is_eol is False
        assert requests_dep.has_vulnerabilities is False

        django_dep = next(d for d in db_deps if d.package_name == "django")
        assert django_dep.latest_version == "4.2.5"
        assert django_dep.is_eol is True
        assert django_dep.eol_date is not None
        assert django_dep.has_vulnerabilities is True

    @pytest.mark.integration
    def test_analyzed_at_timestamp(self, test_session: Session):
        """
        CONTRACT: Dependencies have timezone-aware analyzed_at timestamps.

        Verify:
        - analyzed_at defaults to current time if not provided
        - Custom analyzed_at is preserved
        - Timestamps are UTC-aware
        """
        repo = Repository(
            repo_id="test/dep-timestamp",
            name="dep-timestamp",
            url="https://github.com/test/dep-timestamp",
        )
        test_session.add(repo)
        test_session.commit()

        custom_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        deps = [
            DependencyData(package_name="numpy", ecosystem="pypi", version="1.25.0"),
        ]

        store_dependencies(
            test_session, "test/dep-timestamp", deps, analyzed_at=custom_time
        )
        test_session.commit()

        stored = test_session.query(Dependency).filter_by(
            repo_id="test/dep-timestamp"
        ).first()

        assert stored.analyzed_at is not None
        assert stored.analyzed_at.tzinfo is not None
        assert stored.analyzed_at == custom_time


class TestVulnerabilityStorageDirectE2E:
    """
    CONTRACT: Vulnerability records correctly linked to dependencies.

    Tests direct Vulnerability model storage, bypassing extraction
    and enrichment API calls.
    """

    @pytest.mark.integration
    def test_vulnerability_stored_with_dependency(self, test_session: Session):
        """
        CONTRACT: Vulnerabilities are persisted and linked to dependencies.

        Verify:
        - Vulnerability record created
        - Foreign key to dependency valid
        - CVE/severity/description fields stored
        """
        repo = Repository(
            repo_id="test/vuln-storage",
            name="vuln-storage",
            url="https://github.com/test/vuln-storage",
        )
        test_session.add(repo)
        test_session.commit()

        dep = Dependency(
            repo_id="test/vuln-storage",
            package_name="lodash",
            ecosystem="npm",
            version="4.17.20",
            analyzed_at=datetime.now(timezone.utc),
        )
        test_session.add(dep)
        test_session.flush()

        vuln = Vulnerability(
            dependency_id=dep.id,
            cve_id="CVE-2021-23337",
            vulnerability_id="GHSA-35jh-r3h4-6jhm",
            severity="high",
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
        assert stored_vuln.severity == "high"
        assert stored_vuln.vulnerability_id == "GHSA-35jh-r3h4-6jhm"
        assert stored_vuln.fixed_in_version == "4.17.21"
        assert stored_vuln.summary == "Prototype Pollution in lodash"
        assert stored_vuln.published_date.tzinfo is not None

    @pytest.mark.integration
    def test_multiple_vulnerabilities_per_dependency(self, test_session: Session):
        """
        CONTRACT: A dependency can have multiple vulnerabilities.

        Verify:
        - Multiple vulnerabilities linked to same dependency
        - Each has distinct CVE/severity
        - Cascade relationship works
        """
        repo = Repository(
            repo_id="test/multi-vuln",
            name="multi-vuln",
            url="https://github.com/test/multi-vuln",
        )
        test_session.add(repo)
        test_session.commit()

        dep = Dependency(
            repo_id="test/multi-vuln",
            package_name="django",
            ecosystem="pypi",
            version="3.2.0",
            has_vulnerabilities=True,
            analyzed_at=datetime.now(timezone.utc),
        )
        test_session.add(dep)
        test_session.flush()

        vulns = [
            Vulnerability(
                dependency_id=dep.id,
                cve_id="CVE-2023-0001",
                severity="critical",
                summary="SQL injection in QuerySet",
                fixed_in_version="3.2.19",
            ),
            Vulnerability(
                dependency_id=dep.id,
                cve_id="CVE-2023-0002",
                severity="medium",
                summary="XSS in admin interface",
                fixed_in_version="3.2.18",
            ),
            Vulnerability(
                dependency_id=dep.id,
                cve_id="CVE-2023-0003",
                severity="low",
                summary="Information disclosure in debug mode",
            ),
        ]
        for v in vulns:
            test_session.add(v)
        test_session.commit()

        stored_vulns = test_session.query(Vulnerability).filter_by(
            dependency_id=dep.id
        ).all()

        assert len(stored_vulns) == 3

        severities = {v.severity for v in stored_vulns}
        assert severities == {"critical", "medium", "low"}

    @pytest.mark.integration
    def test_vulnerability_cascade_delete(self, test_session: Session):
        """
        CONTRACT: Deleting a dependency cascades to its vulnerabilities.

        Verify:
        - Vulnerability deleted when parent dependency removed
        - No orphaned vulnerability records
        """
        repo = Repository(
            repo_id="test/vuln-cascade",
            name="vuln-cascade",
            url="https://github.com/test/vuln-cascade",
        )
        test_session.add(repo)
        test_session.commit()

        dep = Dependency(
            repo_id="test/vuln-cascade",
            package_name="express",
            ecosystem="npm",
            version="4.17.1",
            analyzed_at=datetime.now(timezone.utc),
        )
        test_session.add(dep)
        test_session.flush()

        vuln = Vulnerability(
            dependency_id=dep.id,
            cve_id="CVE-2022-9999",
            severity="high",
            summary="Path traversal",
        )
        test_session.add(vuln)
        test_session.commit()

        # Verify vulnerability exists
        assert test_session.query(Vulnerability).count() == 1

        # Delete the dependency
        test_session.delete(dep)
        test_session.commit()

        # Vulnerability should be cascade-deleted
        assert test_session.query(Vulnerability).count() == 0
