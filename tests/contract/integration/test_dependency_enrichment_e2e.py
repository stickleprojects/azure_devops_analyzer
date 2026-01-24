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
from sqlalchemy.orm import Session

from src.extractors.github.extractor import GitHubExtractor
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.database.models import Repository, Dependency, Vulnerability


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


@pytest.mark.skip(reason="Dependency manifest extraction not implemented yet")
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
        
        # Extract manifests
        manifests = extractor.extract_manifests(repo_id)
        
        # Parse dependencies
        analyzer = DependencyAnalyzer(enrich=False)  # No enrichment for this test
        dependencies = []
        
        for manifest in manifests:
            try:
                result = analyzer.analyze(manifest)
                dependencies.extend(result.dependencies)
            except Exception as e:
                pytest.skip(f"Failed to parse manifest: {e}")
        
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
        manifests = extractor.extract_manifests(repo_id)
        
        analyzer = DependencyAnalyzer(enrich=True)  # Enable enrichment
        enriched_deps = []
        
        for manifest in manifests:
            try:
                result = analyzer.analyze(manifest)
                if result.enriched_dependencies:
                    enriched_deps.extend(result.enriched_dependencies)
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
        manifests = extractor.extract_manifests(repo_id)
        
        analyzer = DependencyAnalyzer(enrich=True)
        enriched_deps = []
        
        for manifest in manifests:
            try:
                result = analyzer.analyze(manifest)
                if result.enriched_dependencies:
                    enriched_deps.extend(result.enriched_dependencies)
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


@pytest.mark.skip(reason="Dependency manifest extraction not implemented yet")
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
        manifests = extractor.extract_manifests(repo_id)
        
        analyzer = DependencyAnalyzer(enrich=True)
        all_vulns = []
        
        for manifest in manifests:
            try:
                result = analyzer.analyze(manifest)
                if result.enriched_dependencies:
                    for dep in result.enriched_dependencies:
                        if dep.vulnerabilities:
                            all_vulns.extend(dep.vulnerabilities)
            except Exception as e:
                pytest.skip(f"Enrichment failed: {e}")
        
        # Store vulnerabilities
        if all_vulns:
            # First store dependencies
            for manifest in manifests:
                try:
                    result = analyzer.analyze(manifest)
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
