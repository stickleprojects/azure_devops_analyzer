"""
OSV.dev API client for vulnerability and version information.

This module provides a client for querying OSV.dev (Open Source Vulnerabilities)
to enrich dependency information with:
- Latest version information
- Known vulnerabilities (CVE/OSV IDs)
- Severity and remediation guidance

API Docs: https://api.osv.dev/v1/query
"""

import logging
from typing import Optional
from datetime import datetime, UTC
import httpx

from src.extractors.base import DependencyData

logger = logging.getLogger(__name__)

# OSV.dev ecosystem names - maps our ecosystems to OSV names
OSV_ECOSYSTEM_MAP = {
    "pypi": "PyPI",
    "npm": "npm",
    "maven": "Maven",
    "nuget": "NuGet",
    "go": "Go",
    "rubygems": "RubyGems",
    "cargo": "crates.io",
}


class OSVClient:
    """Client for OSV.dev vulnerability database."""

    BASE_URL = "https://api.osv.dev/v1"
    TIMEOUT = 10.0
    
    def __init__(self, timeout: float = TIMEOUT):
        """
        Initialize the OSV.dev client.
        
        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    def get_package_info(
        self, package_name: str, ecosystem: str, version: Optional[str] = None
    ) -> dict:
        """
        Get package information from OSV.dev.

        Args:
            package_name: Name of the package.
            ecosystem: Ecosystem (pypi, npm, maven, etc.).
            version: Optional version to query.

        Returns:
            Dictionary with package info including latest_version and vulnerabilities.
            Returns empty dict if package not found or API error.
        """
        osv_ecosystem = OSV_ECOSYSTEM_MAP.get(ecosystem.lower())
        if not osv_ecosystem:
            logger.debug("Unsupported ecosystem for OSV: %s", ecosystem)
            return {}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Query for vulnerabilities affecting this package
                response = client.post(
                    f"{self.BASE_URL}/query",
                    json={
                        "package": {
                            "name": package_name,
                            "ecosystem": osv_ecosystem,
                        }
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "vulnerabilities": data.get("vulns", []),
                    "package_name": package_name,
                    "ecosystem": ecosystem,
                }
        except httpx.TimeoutException:
            logger.warning("OSV.dev timeout for %s/%s", ecosystem, package_name)
            return {}
        except httpx.HTTPError as e:
            logger.warning("OSV.dev API error for %s/%s: %s", ecosystem, package_name, e)
            return {}
        except Exception as e:
            logger.error("Unexpected error querying OSV.dev: %s", e)
            return {}

    def extract_latest_version(self, vulns: list[dict]) -> Optional[str]:
        """
        Extract the latest known version from vulnerability data.

        Args:
            vulns: List of vulnerability records from OSV.dev.

        Returns:
            Latest version string or None if not found.
        """
        if not vulns:
            return None

        # Collect all affected versions
        affected_versions = set()
        for vuln in vulns:
            affected = vuln.get("affected", [])
            for aff in affected:
                ranges = aff.get("ranges", [])
                for r in ranges:
                    # Get the latest version from the range
                    events = r.get("events", [])
                    for event in events:
                        if "introduced" in event:
                            affected_versions.add(event["introduced"])
                        if "fixed" in event:
                            affected_versions.add(event["fixed"])

        if affected_versions:
            # Sort and return the highest version (best effort)
            try:
                # This is a simplistic approach - real implementation might use packaging.version
                return sorted(affected_versions, key=lambda x: x)[-1]
            except Exception:
                return None

        return None

    def extract_vulnerabilities(self, vulns: list[dict]) -> list[dict]:
        """
        Extract vulnerability information from OSV data.

        Args:
            vulns: List of vulnerability records from OSV.dev.

        Returns:
            List of vulnerability records with structured data.
        """
        result = []
        for vuln in vulns:
            vuln_record = {
                "cve_id": vuln.get("cve_id"),
                "osv_id": vuln.get("id"),
                "summary": vuln.get("summary"),
                "details": vuln.get("details"),
                "severity": self._extract_severity(vuln),
                "published_at": vuln.get("published"),
                "modified_at": vuln.get("modified"),
                "fixed_in_versions": self._extract_fixed_versions(vuln),
                "references": vuln.get("references", []),
            }
            result.append(vuln_record)
        
        return result

    def _extract_severity(self, vuln: dict) -> Optional[str]:
        """Extract severity from vulnerability record."""
        # Try to get severity from severity field
        severity_data = vuln.get("severity", [])
        if isinstance(severity_data, list) and severity_data:
            # Format: [{"type": "CVSS_V3", "score": "7.5"}]
            for sev in severity_data:
                if sev.get("type") == "CVSS_V3":
                    score = float(sev.get("score", 0))
                    if score >= 9.0:
                        return "critical"
                    elif score >= 7.0:
                        return "high"
                    elif score >= 4.0:
                        return "medium"
                    else:
                        return "low"
        
        return None

    def _extract_fixed_versions(self, vuln: dict) -> list[str]:
        """Extract versions where this vulnerability is fixed."""
        fixed_versions = []
        affected = vuln.get("affected", [])
        
        for aff in affected:
            ranges = aff.get("ranges", [])
            for r in ranges:
                events = r.get("events", [])
                for event in events:
                    if "fixed" in event:
                        fixed_versions.append(event["fixed"])
        
        return list(set(fixed_versions))  # Deduplicate
