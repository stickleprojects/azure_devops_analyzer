"""
Tech Radar categorization engine (Plan 022).

Categorizes packages into Thoughtworks Tech Radar rings
(Adopt / Trial / Assess / Hold) and quadrants
(Infrastructure / Platforms / Tools / Languages & Frameworks)
based on adoption metrics, health signals, and configurable rules.
"""

import fnmatch
import json
import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "radar_categorization_config.json"


class Ring(Enum):
    ADOPT = "Adopt"
    TRIAL = "Trial"
    ASSESS = "Assess"
    HOLD = "Hold"


class Quadrant(Enum):
    INFRASTRUCTURE = "Infrastructure"
    PLATFORMS = "Platforms"
    TOOLS = "Tools"
    LANGUAGES = "Languages & Frameworks"


@dataclass
class RadarBlip:
    """A single tech-radar blip produced by the categorization engine."""

    package_name: str
    ecosystem: str
    ring: Ring
    quadrant: Quadrant
    label: str
    description: str
    repo_count: int
    is_new: bool
    is_moved: bool
    adopted_date: Optional[date]
    exposed_to_cves: int
    is_eol: bool
    eol_date: Optional[date]
    latest_version: Optional[str]
    flags: dict = field(default_factory=dict)


class RadarCategorizer:
    """
    Categorizes packages into Adopt/Trial/Assess/Hold rings based on:

    1. Health signals  — EOL status, CVE exposure (highest priority)
    2. Adoption metrics — repo_count and time_in_use_days
    3. Quadrant mapping — derived from the detected technology category or ecosystem
    4. Configurable rules — loaded from radar_categorization_config.json

    Priority order (highest first): EOL > CVE Exposure > Adoption Metrics
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._config = self._load_config(config_path or _DEFAULT_CONFIG_PATH)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def categorize(
        self,
        package_name: str,
        ecosystem: str,
        metrics: dict,
        prior_ring: Optional[str] = None,
    ) -> RadarBlip:
        """Return a RadarBlip for *package_name* given *metrics*.

        *metrics* dict keys (all optional — safe defaults used if absent):
          - repo_count         (int)   breadth of usage
          - time_in_use_days   (int)   days since first_seen_at
          - exposed_cves       (int)   repos with a known-vulnerable version
          - is_eol             (bool)  package is end-of-life
          - eol_date           (date)  EOL date
          - category           (str)   technology category hint (language/framework/…)
          - adopted_date       (date)  first adoption date
          - latest_version     (str)   latest known version
        """
        repo_count = int(metrics.get("repo_count") or 0)
        time_in_use_days = int(metrics.get("time_in_use_days") or 0)
        exposed_cves = int(metrics.get("exposed_cves") or 0)
        is_eol = bool(metrics.get("is_eol", False))
        eol_date = metrics.get("eol_date")
        category = str(metrics.get("category") or "").lower()
        adopted_date = metrics.get("adopted_date")
        latest_version = metrics.get("latest_version")

        ring = self._determine_ring(repo_count, time_in_use_days, exposed_cves, is_eol)
        quadrant = self._determine_quadrant(category, ecosystem)

        is_moved = prior_ring is not None and prior_ring != ring.value

        label = metrics.get("label") or package_name
        description = self._build_description(package_name, repo_count, is_eol, exposed_cves)

        return RadarBlip(
            package_name=package_name,
            ecosystem=ecosystem,
            ring=ring,
            quadrant=quadrant,
            label=label,
            description=description,
            repo_count=repo_count,
            is_new=prior_ring is None,
            is_moved=is_moved,
            adopted_date=adopted_date,
            exposed_to_cves=exposed_cves,
            is_eol=is_eol,
            eol_date=eol_date,
            latest_version=latest_version,
        )

    def is_excluded(self, package_name: str) -> bool:
        """Return True if *package_name* matches any exclusion glob."""
        for pattern in self._config.get("exclusions", []):
            if fnmatch.fnmatch(package_name, pattern):
                return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_ring(
        self,
        repo_count: int,
        time_in_use_days: int,
        exposed_cves: int,
        is_eol: bool,
    ) -> Ring:
        """Apply priority-ordered ring rules.

        Priority: EOL > CVE Exposure > Adoption Metrics
        """
        # 1. EOL packages → Hold
        if is_eol:
            return Ring.HOLD

        # 2. Packages with active CVE exposure → Hold (high risk)
        if exposed_cves > 0:
            return Ring.HOLD

        return self._ring_from_adoption(repo_count, time_in_use_days)

    def _ring_from_adoption(self, repo_count: int, time_in_use_days: int) -> Ring:
        """Return ring based purely on adoption breadth and duration.

        Default thresholds (overridable via config):
          Adopt  → 25+ repos AND 180+ days
          Trial  →  5+ repos AND  90+ days
          Assess →  2+ repos
          Hold   → everything else (single repo or brand new)
        """
        rules = self._config.get("ring_rules", {})

        adopt_cfg = rules.get("adopt", {})
        trial_cfg = rules.get("trial", {})
        assess_cfg = rules.get("assess", {})

        adopt_min_repos = int(adopt_cfg.get("min_repo_count", 25))
        adopt_min_days = int(adopt_cfg.get("min_time_in_use_days", 180))

        trial_min_repos = int(trial_cfg.get("min_repo_count", 5))
        trial_min_days = int(trial_cfg.get("min_time_in_use_days", 90))

        assess_min_repos = int(assess_cfg.get("min_repo_count", 2))

        if repo_count >= adopt_min_repos and time_in_use_days >= adopt_min_days:
            return Ring.ADOPT

        if repo_count >= trial_min_repos and time_in_use_days >= trial_min_days:
            return Ring.TRIAL

        if repo_count >= assess_min_repos:
            return Ring.ASSESS

        return Ring.HOLD

    def _determine_quadrant(self, category: str, ecosystem: str) -> Quadrant:
        """Map a technology category (or ecosystem) to a radar quadrant."""
        mapping = self._config.get("quadrant_mapping", {})

        for key, quadrant_name in mapping.items():
            if key in category:
                return self._quadrant_from_name(quadrant_name)

        # Fallback: map common ecosystems
        eco = ecosystem.lower()
        if eco in ("pypi", "npm", "maven", "nuget", "rubygems", "go"):
            return Quadrant.LANGUAGES
        if eco in ("docker", "helm"):
            return Quadrant.INFRASTRUCTURE

        return Quadrant.TOOLS

    @staticmethod
    def _quadrant_from_name(name: str) -> Quadrant:
        mapping = {
            "Infrastructure": Quadrant.INFRASTRUCTURE,
            "Platforms": Quadrant.PLATFORMS,
            "Tools": Quadrant.TOOLS,
            "Languages & Frameworks": Quadrant.LANGUAGES,
        }
        return mapping.get(name, Quadrant.TOOLS)

    @staticmethod
    def _build_description(
        package_name: str, repo_count: int, is_eol: bool, exposed_cves: int
    ) -> str:
        parts = [f"Used in {repo_count} repo(s)."]
        if is_eol:
            parts.append("Package is end-of-life.")
        if exposed_cves > 0:
            parts.append(f"{exposed_cves} repo(s) exposed to known CVEs.")
        return " ".join(parts)

    @staticmethod
    def _load_config(path: Path) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            logger.warning("Radar config not found at %s; using empty defaults", path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in radar config %s: %s", path, exc)
            return {}
