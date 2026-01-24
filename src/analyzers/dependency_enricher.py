"""
Dependency enrichment service.

Enriches extracted dependencies with additional information from external APIs:
- Latest version information from OSV.dev
- End-of-life dates from endoflife.date
- Vulnerability data
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.extractors.base import DependencyData
from src.analyzers.osv_client import OSVClient
from src.analyzers.eol_client import EndOfLifeClient

logger = logging.getLogger(__name__)


@dataclass
class EnrichedDependency:
    """Dependency with enriched information from external APIs."""
    
    # Original dependency data
    package_name: str
    ecosystem: str
    version: Optional[str]
    is_dev_dependency: bool
    source_file: str
    version_constraint: Optional[str]
    
    # Enriched data
    latest_version: Optional[str] = None
    eol_date: Optional[datetime] = None
    is_eol: bool = False
    has_vulnerabilities: bool = False
    vulnerabilities: list[dict] = field(default_factory=list)


class DependencyEnricher:
    """
    Enriches dependencies with external API data.
    
    Uses:
    - OSV.dev for latest versions and vulnerabilities
    - endoflife.date for end-of-life information
    
    Supports concurrent enrichment for performance.
    """

    def __init__(self, max_workers: int = 5):
        """
        Initialize the enricher.

        Args:
            max_workers: Number of concurrent API requests.
        """
        self.osv_client = OSVClient()
        self.eol_client = EndOfLifeClient()
        self.max_workers = max_workers

    def enrich(self, dependencies: list[DependencyData]) -> list[EnrichedDependency]:
        """
        Enrich a list of dependencies with external data.

        Args:
            dependencies: List of DependencyData to enrich.

        Returns:
            List of EnrichedDependency with additional information.
        """
        if not dependencies:
            return []

        logger.info("Enriching %d dependencies", len(dependencies))

        enriched = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all enrichment tasks
            future_to_dep = {
                executor.submit(self._enrich_single, dep): dep
                for dep in dependencies
            }

            # Collect results
            for future in as_completed(future_to_dep):
                dep = future_to_dep[future]
                try:
                    enriched_dep = future.result()
                    enriched.append(enriched_dep)
                except Exception as e:
                    logger.error("Error enriching %s/%s: %s", dep.ecosystem, dep.package_name, e)
                    # Return unenriched version
                    enriched.append(self._create_enriched_dependency(dep))

        logger.info("Enriched %d dependencies", len(enriched))
        return enriched

    def _enrich_single(self, dep: DependencyData) -> EnrichedDependency:
        """
        Enrich a single dependency.

        Args:
            dep: Dependency to enrich.

        Returns:
            EnrichedDependency with enriched data.
        """
        enriched = self._create_enriched_dependency(dep)

        # Get OSV.dev data (latest version + vulnerabilities)
        osv_data = self.osv_client.get_package_info(
            dep.package_name, dep.ecosystem, dep.version
        )

        if osv_data:
            vulns = osv_data.get("vulnerabilities", [])
            
            # Extract latest version
            if not enriched.latest_version:  # Don't override if already set
                enriched.latest_version = self.osv_client.extract_latest_version(vulns)
            
            # Extract vulnerabilities
            if vulns:
                enriched.has_vulnerabilities = True
                enriched.vulnerabilities = self.osv_client.extract_vulnerabilities(vulns)

        # Get endoflife.date data
        eol_date = self.eol_client.get_eol_date(
            dep.package_name, dep.ecosystem, dep.version
        )
        if eol_date:
            enriched.eol_date = eol_date
            enriched.is_eol = self.eol_client.is_eol(dep.ecosystem, dep.version)

        return enriched

    def _create_enriched_dependency(self, dep: DependencyData) -> EnrichedDependency:
        """Create an EnrichedDependency from DependencyData."""
        return EnrichedDependency(
            package_name=dep.package_name,
            ecosystem=dep.ecosystem,
            version=dep.version,
            is_dev_dependency=dep.is_dev_dependency,
            source_file=dep.source_file,
            version_constraint=dep.version_constraint,
        )
