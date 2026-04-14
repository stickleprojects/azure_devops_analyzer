"""
Technology enrichment service.

Queries endoflife.date API for EOL metadata and writes results to the
technologies table.  EOL data is stored once per (name, category) — it is a
global fact about a technology, not a per-repository fact.

Call this after store_detections() to ensure all detected technologies have
a row in the technologies table before enriching.
"""

import logging
from datetime import date, datetime, UTC
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from src.database.storage import store_technology_eol

logger = logging.getLogger(__name__)


class TechnologyEnricher:
    """Queries endoflife.date and writes results to the technologies table.

    EOL data is stored once per technology (name + category), not per
    repository.  Call this after store_detections() to ensure all detected
    technologies have a row in the technologies table before enriching.
    """

    BASE_URL = "https://endoflife.date/api"
    TIMEOUT = 10.0

    # Maps technology name → endoflife.date product slug.
    # None means no entry exists on endoflife.date; skip gracefully.
    EOL_SLUG_MAP: dict[str, Optional[str]] = {
        "Python": "python",
        "Node.js": "nodejs",
        "Java": "java",
        "C#": "dotnet",
        "Go": "go",
        "Ruby": "ruby",
        "PHP": "php",
        "Spring": "spring-framework",
        "Django": "django",
        "Rails": "rails",
        "Laravel": "laravel",
        "Angular": "angular",
        "React": None,          # no endoflife.date entry — skip gracefully
        "Vue": "vue",
        "ASP.NET": "dotnet",
        "Azure Pipelines": None,  # no endoflife.date entry — skip
    }

    def __init__(self, timeout: float = TIMEOUT):
        self.timeout = timeout

    def _fetch_cycles(self, slug: str) -> Optional[list[dict]]:
        """Fetch release cycle list from endoflife.date.

        Returns list of cycles on success, None on 404 or network error.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.BASE_URL}/{slug}.json")
                if response.status_code == 404:
                    logger.debug("endoflife.date: no entry for slug '%s'", slug)
                    return None
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.warning("endoflife.date timeout for slug '%s'", slug)
            return None
        except httpx.HTTPError as exc:
            logger.warning("endoflife.date HTTP error for slug '%s': %s", slug, exc)
            return None
        except Exception as exc:
            logger.warning("endoflife.date unexpected error for slug '%s': %s", slug, exc)
            return None

    def _parse_cycles(
        self, cycles: list[dict]
    ) -> tuple[bool, Optional[date], Optional[str]]:
        """Determine EOL status from a list of release cycles.

        Returns (is_eol, eol_date, latest_supported_version).
        - is_eol = True when all cycles have passed their EOL date.
        - latest_supported_version = the 'cycle' field of the most recent
          non-EOL cycle (or None when all are EOL).
        - eol_date = the EOL date of the most recently EOL'd cycle.
        """
        if not cycles:
            return False, None, None

        today = datetime.now(UTC).date()
        latest_supported: Optional[str] = None
        latest_eol_date: Optional[date] = None
        all_eol = True

        for cycle in cycles:
            eol_raw = cycle.get("eol")
            cycle_name = str(cycle.get("cycle", ""))

            # Parse EOL field: can be a date string, True (already EOL) or False
            if eol_raw is True:
                # Definitively EOL with no specific date
                eol_cycle_date: Optional[date] = None
                cycle_is_eol = True
            elif eol_raw is False or eol_raw is None:
                all_eol = False
                if latest_supported is None:
                    latest_supported = cycle_name
                continue
            else:
                try:
                    eol_cycle_date = date.fromisoformat(str(eol_raw))
                    cycle_is_eol = eol_cycle_date <= today
                except (ValueError, TypeError):
                    all_eol = False
                    continue

            if cycle_is_eol:
                if eol_cycle_date is not None:
                    if latest_eol_date is None or eol_cycle_date > latest_eol_date:
                        latest_eol_date = eol_cycle_date
            else:
                all_eol = False
                if latest_supported is None:
                    latest_supported = cycle_name

        return all_eol, latest_eol_date, latest_supported

    def enrich(self, session: Session, names: list[tuple[str, str]]) -> None:
        """Enrich technologies with EOL data from endoflife.date.

        Query endoflife.date for each (name, category) pair that has a slug
        mapping.  Calls store_technology_eol() for each result.

        Skips entries with no slug mapping, 404 responses, or network errors
        (logs a warning for each skip).

        Args:
            session: Database session (caller manages commit/rollback).
            names: List of (technology_name, category) pairs to enrich.
        """
        for tech_name, category in names:
            # Look up slug; skip if not in map
            if tech_name not in self.EOL_SLUG_MAP:
                logger.debug(
                    "No EOL slug mapping for '%s' (%s) — skipping", tech_name, category
                )
                continue

            slug = self.EOL_SLUG_MAP[tech_name]
            if slug is None:
                logger.debug(
                    "EOL slug is None for '%s' (%s) — skipping", tech_name, category
                )
                continue

            cycles = self._fetch_cycles(slug)
            if cycles is None:
                continue

            is_eol, eol_date, latest_version = self._parse_cycles(cycles)

            store_technology_eol(
                session,
                name=tech_name,
                category=category,
                is_eol=is_eol,
                eol_date=eol_date,
                latest_supported_version=latest_version,
            )
            logger.debug(
                "Enriched '%s' (%s): is_eol=%s eol_date=%s latest=%s",
                tech_name,
                category,
                is_eol,
                eol_date,
                latest_version,
            )
