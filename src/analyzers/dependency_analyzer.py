"""
Dependency analyzer module.

Analyzes repositories to extract dependency information from manifest files
across multiple ecosystems.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from fnmatch import fnmatch
from typing import Optional

from src.extractors.base import DependencyData, RepositoryExtractor
from src.analyzers.parsers import ParserRegistry
from src.analyzers.dependency_enricher import DependencyEnricher, EnrichedDependency

logger = logging.getLogger(__name__)


@dataclass
class DependencyAnalysisResult:
    """Results from dependency analysis."""

    repo_id: str
    branch: Optional[str]
    dependencies: list[DependencyData]
    enriched_dependencies: list[EnrichedDependency] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    files_scanned: int = 0
    files_parsed: int = 0
    parse_errors: list[str] = field(default_factory=list)
    enrichment_errors: list[str] = field(default_factory=list)

    @property
    def total_dependencies(self) -> int:
        """Total number of dependencies found."""
        return len(self.dependencies)

    @property
    def dev_dependencies(self) -> int:
        """Number of dev dependencies found."""
        return sum(1 for d in self.dependencies if d.is_dev_dependency)

    @property
    def prod_dependencies(self) -> int:
        """Number of production dependencies found."""
        return sum(1 for d in self.dependencies if not d.is_dev_dependency)

    @property
    def ecosystems(self) -> set[str]:
        """Set of ecosystems detected."""
        return {d.ecosystem for d in self.dependencies}

    def get_dependencies_by_ecosystem(self) -> dict[str, list[DependencyData]]:
        """Group dependencies by ecosystem."""
        result: dict[str, list[DependencyData]] = {}
        for dep in self.dependencies:
            if dep.ecosystem not in result:
                result[dep.ecosystem] = []
            result[dep.ecosystem].append(dep)
        return result


class DependencyAnalyzer:
    """
    Analyzer for extracting dependencies from repository manifest files.

    Uses the parser registry to find and parse manifest files across
    multiple ecosystems (Python, Node.js, Java, .NET, Go, Ruby, Rust).

    Optionally enriches dependencies with external API data:
    - Latest versions from OSV.dev
    - EOL dates from endoflife.date
    - Vulnerability information from OSV.dev

    Example:
        extractor = GitHubExtractor()
        analyzer = DependencyAnalyzer(enrich=True)
        result = analyzer.analyze(extractor, "owner/repo")

        for enriched_dep in result.enriched_dependencies:
            print(f"{enriched_dep.package_name}: {enriched_dep.version}")
            if enriched_dep.latest_version:
                print(f"  Latest: {enriched_dep.latest_version}")
            if enriched_dep.is_eol:
                print(f"  EOL: {enriched_dep.eol_date}")
    """

    def __init__(self, max_file_size: int = 1024 * 1024, enrich: bool = False):
        """
        Initialize the dependency analyzer.

        Args:
            max_file_size: Maximum file size to parse (default 1MB).
            enrich: Whether to enrich dependencies with external API data.
        """
        self.max_file_size = max_file_size
        self.enrich = enrich
        self.enricher = DependencyEnricher() if enrich else None

    def analyze(
        self,
        extractor: RepositoryExtractor,
        repo_id: str,
        branch: Optional[str] = None,
    ) -> DependencyAnalysisResult:
        """
        Analyze a repository to extract dependencies.

        Args:
            extractor: Repository extractor instance.
            repo_id: Repository identifier.
            branch: Branch to analyze (defaults to default branch).

        Returns:
            DependencyAnalysisResult with extracted dependencies.
        """
        logger.info("Analyzing dependencies for %s", repo_id)

        result = DependencyAnalysisResult(
            repo_id=repo_id,
            branch=branch,
            dependencies=[],
            analyzed_at=datetime.now(UTC),
        )

        # Get file tree
        try:
            file_tree = extractor.get_file_tree(repo_id, branch)
        except Exception as e:
            logger.error("Failed to get file tree for %s: %s", repo_id, e)
            result.parse_errors.append(f"Failed to get file tree: {e}")
            return result

        # Find manifest files
        manifest_files = self._find_manifest_files(file_tree)
        result.files_scanned = len(manifest_files)

        logger.info("Found %d manifest files in %s", len(manifest_files), repo_id)

        # Parse each manifest file
        for file_path in manifest_files:
            try:
                deps = self._parse_manifest_file(extractor, repo_id, file_path, branch)
                result.dependencies.extend(deps)
                result.files_parsed += 1
                logger.debug(
                    "Parsed %s: found %d dependencies", file_path, len(deps)
                )
            except Exception as e:
                logger.warning("Failed to parse %s: %s", file_path, e)
                result.parse_errors.append(f"{file_path}: {e}")

        # Deduplicate dependencies (same package from multiple files)
        result.dependencies = self._deduplicate_dependencies(result.dependencies)

        logger.info(
            "Dependency analysis complete for %s: %d dependencies from %d ecosystems",
            repo_id,
            result.total_dependencies,
            len(result.ecosystems),
        )

        # Enrich dependencies if requested
        if self.enrich and result.dependencies:
            logger.info("Enriching dependencies for %s", repo_id)
            try:
                result.enriched_dependencies = self.enricher.enrich(result.dependencies)
                logger.info(
                    "Enriched %d dependencies for %s",
                    len(result.enriched_dependencies),
                    repo_id,
                )
            except Exception as e:
                logger.error("Error enriching dependencies for %s: %s", repo_id, e)
                result.enrichment_errors.append(f"Enrichment failed: {e}")
                # Fall back to unenriched dependencies
                result.enriched_dependencies = [
                    EnrichedDependency(
                        package_name=d.package_name,
                        ecosystem=d.ecosystem,
                        version=d.version,
                        is_dev_dependency=d.is_dev_dependency,
                        source_file=d.source_file,
                        version_constraint=d.version_constraint,
                    )
                    for d in result.dependencies
                ]

        return result

    def _find_manifest_files(self, file_tree) -> list[str]:
        """
        Find all manifest files in the file tree.

        Args:
            file_tree: List of FileTreeItem from the extractor.

        Returns:
            List of file paths to parse.
        """
        manifest_files = []
        supported_patterns = ParserRegistry.get_supported_patterns()

        for item in file_tree:
            if item.is_directory:
                continue

            # Check if file matches any supported pattern
            file_name = item.path.split("/")[-1]
            for pattern in supported_patterns:
                if fnmatch(file_name, pattern):
                    manifest_files.append(item.path)
                    break

        return manifest_files

    def _parse_manifest_file(
        self,
        extractor: RepositoryExtractor,
        repo_id: str,
        file_path: str,
        branch: Optional[str],
    ) -> list[DependencyData]:
        """
        Parse a single manifest file.

        Args:
            extractor: Repository extractor instance.
            repo_id: Repository identifier.
            file_path: Path to the manifest file.
            branch: Branch to read from.

        Returns:
            List of dependencies extracted from the file.
        """
        # Get parser for this file
        parser = ParserRegistry.get_parser_for_file(file_path)
        if not parser:
            logger.debug("No parser found for %s", file_path)
            return []

        # Fetch file content
        content = extractor.get_file_content(repo_id, file_path, branch)
        if not content:
            logger.debug("Empty or missing file: %s", file_path)
            return []

        # Check file size
        if len(content) > self.max_file_size:
            logger.warning(
                "File %s exceeds max size (%d > %d)",
                file_path,
                len(content),
                self.max_file_size,
            )
            return []

        # Parse the file
        return parser.parse(content, file_path)

    def _deduplicate_dependencies(
        self, dependencies: list[DependencyData]
    ) -> list[DependencyData]:
        """
        Deduplicate dependencies by package name and ecosystem.

        When the same package appears in multiple files, prefer:
        1. Non-dev over dev dependency
        2. More specific version over less specific

        Args:
            dependencies: List of dependencies to deduplicate.

        Returns:
            Deduplicated list of dependencies.
        """
        seen: dict[tuple[str, str], DependencyData] = {}

        for dep in dependencies:
            key = (dep.ecosystem, dep.package_name.lower())

            if key not in seen:
                seen[key] = dep
            else:
                existing = seen[key]

                # Prefer non-dev over dev
                if existing.is_dev_dependency and not dep.is_dev_dependency:
                    seen[key] = dep
                # Prefer more specific version
                elif (
                    dep.version
                    and (not existing.version or len(dep.version) > len(existing.version))
                    and existing.is_dev_dependency == dep.is_dev_dependency
                ):
                    seen[key] = dep

        return list(seen.values())
