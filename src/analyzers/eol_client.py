"""
endoflife.date API client for end-of-life information.

This module provides a client for querying endoflife.date to determine
when specific software versions reach end-of-life.

API Docs: https://endoflife.date/docs/api/
"""

import logging
from typing import Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# endoflife.date product name mapping - maps our ecosystems to product names
EOL_PRODUCT_MAP = {
    "pypi": "python",  # Note: Python as a language, not individual packages
    "npm": "nodejs",   # Node.js for npm packages
    "maven": "java",   # Java for Maven
    "nuget": "dotnet", # .NET for NuGet
    "go": "go",
    "rubygems": "ruby",
    "cargo": "rust",
}


class EndOfLifeClient:
    """Client for endoflife.date API."""

    BASE_URL = "https://endoflife.date/api"
    TIMEOUT = 10.0

    def __init__(self, timeout: float = TIMEOUT):
        """
        Initialize the endoflife.date client.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    def get_eol_date(
        self, package_name: str, ecosystem: str, version: Optional[str] = None
    ) -> Optional[datetime]:
        """
        Get end-of-life date for a package version.

        Args:
            package_name: Name of the package.
            ecosystem: Ecosystem (pypi, npm, maven, etc.).
            version: Version to check (if None, checks language runtime).

        Returns:
            datetime of EOL date or None if not found.
        """
        product = EOL_PRODUCT_MAP.get(ecosystem.lower())
        if not product:
            logger.debug("Unsupported ecosystem for endoflife.date: %s", ecosystem)
            return None

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Query the product lifecycle
                response = client.get(f"{self.BASE_URL}/{product}.json")
                response.raise_for_status()
                releases = response.json()

                # Find matching version
                if version:
                    for release in releases:
                        if release.get("release") == version:
                            eol = release.get("eol")
                            if eol and eol != "false":
                                try:
                                    return datetime.fromisoformat(str(eol))
                                except (ValueError, TypeError):
                                    pass
                            break

                return None

        except httpx.TimeoutException:
            logger.warning(
                "endoflife.date timeout for %s/%s v%s",
                product,
                package_name,
                version,
            )
            return None
        except httpx.HTTPError as e:
            logger.warning(
                "endoflife.date API error for %s: %s", product, e
            )
            return None
        except Exception as e:
            logger.error("Unexpected error querying endoflife.date: %s", e)
            return None

    def is_eol(
        self, ecosystem: str, version: Optional[str] = None
    ) -> bool:
        """
        Check if a version is end-of-life.

        Args:
            ecosystem: Ecosystem name.
            version: Version to check.

        Returns:
            True if EOL date has passed, False otherwise.
        """
        if not version:
            return False

        eol_date = self.get_eol_date("", ecosystem, version)
        if not eol_date:
            return False

        return datetime.now(eol_date.tzinfo) > eol_date
