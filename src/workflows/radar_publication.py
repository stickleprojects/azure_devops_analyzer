"""
RadarPublicationWorkflow — orchestrates Tech Radar generation (Plan 022).

Steps:
  1. Query packages + repository_dependencies + vulnerabilities
  2. Categorize each package via RadarCategorizer
  3. Detect ring movements vs. the prior publication (including removed packages)
  4. Store radar_publications + radar_blips + radar_blip_history
  5. Mark new publication as is_latest, clear the flag on prior ones
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.analyzers.radar_categorization import RadarBlip, RadarCategorizer
from src.database.models.dependency import RepositoryDependency
from src.database.models.package import Package
from src.database.models.radar import (
    RadarBlip as RadarBlipModel,
    RadarBlipHistory,
    RadarPublication,
)

logger = logging.getLogger(__name__)


class RadarPublicationWorkflow:
    """Generate and persist a new Tech Radar publication."""

    def __init__(self, session: Session, categorizer: Optional[RadarCategorizer] = None):
        self._session = session
        self._categorizer = categorizer or RadarCategorizer()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        description: Optional[str] = None,
        published_by: str = "automated",
        publication_version: Optional[str] = None,
    ) -> RadarPublication:
        """Generate a new radar publication and persist it.

        Returns the newly created RadarPublication ORM object.
        """
        logger.info("Starting radar publication (published_by=%s)", published_by)

        # 1. Load prior blips for movement detection
        prior_blip_data = self._load_prior_blip_data()
        has_prior_publication = len(prior_blip_data) > 0

        # 2. Query packages with usage metrics
        package_metrics = self._load_package_metrics()
        logger.info("Loaded metrics for %d packages", len(package_metrics))

        # 3. Categorize each package
        blips: list[RadarBlip] = []
        for key, metrics in package_metrics.items():
            package_name, ecosystem = key
            if self._categorizer.is_excluded(package_name):
                continue
            prior_ring = prior_blip_data[key]["ring"] if key in prior_blip_data else None
            blip = self._categorizer.categorize(
                package_name, ecosystem, metrics,
                prior_ring=prior_ring,
                has_prior_publication=has_prior_publication,
            )
            blips.append(blip)

        # 4. Detect movements (ring changes, new packages, removed packages)
        history_rows = self._detect_movements(prior_blip_data, blips)

        # 5. Persist
        publication = self._store_publication(blips, history_rows, description, published_by, publication_version)

        logger.info(
            "Radar publication %d created: %d blips, %d history rows",
            publication.id,
            len(blips),
            len(history_rows),
        )
        return publication

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_prior_blip_data(self) -> dict[tuple[str, str], dict]:
        """Return per-package data from the latest publication.

        Returns {(package_name, ecosystem): {"ring": str, "repo_count": int, "exposed_to_cves": int}}
        """
        latest = (
            self._session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .first()
        )
        if not latest:
            return {}

        rows = (
            self._session.query(
                RadarBlipModel.package_name,
                RadarBlipModel.ecosystem,
                RadarBlipModel.ring,
                RadarBlipModel.repo_count,
                RadarBlipModel.exposed_to_cves,
            )
            .filter(RadarBlipModel.publication_id == latest.id)
            .all()
        )
        return {
            (r.package_name, r.ecosystem): {
                "ring": r.ring,
                "repo_count": r.repo_count or 0,
                "exposed_to_cves": r.exposed_to_cves or 0,
            }
            for r in rows
        }

    def _load_package_metrics(self) -> dict[tuple[str, str], dict]:
        """Aggregate per-package metrics from repository_dependencies and packages."""
        rows = self._session.execute(
            text(
                """
                SELECT
                    d.package_name,
                    d.ecosystem,
                    COUNT(DISTINCT d.repo_id)            AS repo_count,
                    MIN(d.first_seen_at)                 AS first_seen_at,
                    SUM(CASE WHEN d.has_known_vulnerabilities THEN 1 ELSE 0 END)
                                                         AS exposed_cves
                FROM repository_dependencies d
                GROUP BY d.package_name, d.ecosystem
                """
            )
        ).fetchall()

        # Enrich with package-level EOL / latest_version
        pkg_info: dict[tuple[str, str], Package] = {}
        for pkg in self._session.query(Package).all():
            pkg_info[(pkg.package_name, pkg.ecosystem)] = pkg

        metrics: dict[tuple[str, str], dict] = {}
        now = datetime.now(UTC)

        for row in rows:
            package_name = row.package_name
            ecosystem = row.ecosystem
            key = (package_name, ecosystem)
            first_seen = row.first_seen_at
            time_in_use_days = (now - first_seen).days if first_seen else 0

            pkg = pkg_info.get(key)

            metrics[key] = {
                "repo_count": row.repo_count,
                "time_in_use_days": max(0, time_in_use_days),
                "exposed_cves": int(row.exposed_cves or 0),
                "is_eol": pkg.is_eol if pkg else False,
                "eol_date": pkg.eol_date if pkg else None,
                "adopted_date": first_seen.date() if first_seen else None,
                "latest_version": pkg.latest_version if pkg else None,
            }

        return metrics

    def _detect_movements(
        self,
        prior: dict[tuple[str, str], dict],
        current: list[RadarBlip],
    ) -> list[dict]:
        """Build history rows for ring changes, new blips, and removed packages.

        ``prior`` maps (package_name, ecosystem) → {"ring", "repo_count", "exposed_to_cves"}.
        History is written for:
        - new packages (present in current, absent in prior)
        - ring movements (present in both, ring changed)
        - removed packages (present in prior, absent in current)
        """
        history = []
        today = datetime.now(UTC).date()
        current_keys = {(blip.package_name, blip.ecosystem) for blip in current}

        # New / moved blips
        for blip in current:
            key = (blip.package_name, blip.ecosystem)
            prior_data = prior.get(key)
            prior_ring = prior_data["ring"] if prior_data else None

            if prior_ring is not None and prior_ring == blip.ring.value:
                # Ring unchanged — no history record needed
                continue

            prior_repo_count = prior_data["repo_count"] if prior_data else 0
            prior_exposed = prior_data["exposed_to_cves"] if prior_data else 0
            current_exposed = blip.exposed_to_cves

            repo_count_delta = blip.repo_count - prior_repo_count

            if prior_exposed == 0 and current_exposed > 0:
                vulnerability_change = "now_exposed"
            elif prior_exposed > 0 and current_exposed == 0:
                vulnerability_change = "fixed"
            else:
                vulnerability_change = "unchanged"

            history.append(
                {
                    "package_name": blip.package_name,
                    "ecosystem": blip.ecosystem,
                    "publication_date": today,
                    "prior_ring": prior_ring,
                    "current_ring": blip.ring.value,
                    "repo_count_delta": repo_count_delta,
                    "vulnerability_change": vulnerability_change,
                }
            )

        # Removed packages (in prior but no longer in current snapshot)
        for (package_name, ecosystem), prior_data in prior.items():
            if (package_name, ecosystem) not in current_keys:
                prior_exposed = prior_data["exposed_to_cves"]
                history.append(
                    {
                        "package_name": package_name,
                        "ecosystem": ecosystem,
                        "publication_date": today,
                        "prior_ring": prior_data["ring"],
                        "current_ring": "Removed",
                        "repo_count_delta": -prior_data["repo_count"],
                        "vulnerability_change": "fixed" if prior_exposed > 0 else "unchanged",
                    }
                )

        return history

    def _store_publication(
        self,
        blips: list[RadarBlip],
        history: list[dict],
        description: Optional[str],
        published_by: str,
        publication_version: Optional[str],
    ) -> RadarPublication:
        """Insert publication, blips, and history; mark prior publications as not latest."""
        now = datetime.now(UTC)

        # Clear is_latest on previous publications
        (
            self._session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .update({"is_latest": False})
        )

        pub = RadarPublication(
            publication_date=now,
            publication_version=publication_version
            or now.strftime("%Y-%m-%d"),
            description=description,
            published_by=published_by,
            is_latest=True,
            created_at=now,
        )
        self._session.add(pub)
        self._session.flush()  # populate pub.id

        for blip in blips:
            self._session.add(
                RadarBlipModel(
                    publication_id=pub.id,
                    package_name=blip.package_name,
                    ecosystem=blip.ecosystem,
                    ring=blip.ring.value,
                    quadrant=blip.quadrant.value,
                    label=blip.label,
                    description=blip.description,
                    is_new=blip.is_new,
                    is_moved=blip.is_moved,
                    adopted_date=blip.adopted_date,
                    repo_count=blip.repo_count,
                    exposed_to_cves=blip.exposed_to_cves,
                    is_eol=blip.is_eol,
                    eol_date=blip.eol_date,
                    latest_version=blip.latest_version,
                    flags=blip.flags,
                    created_at=now,
                )
            )

        for h in history:
            self._session.add(
                RadarBlipHistory(
                    package_name=h["package_name"],
                    ecosystem=h["ecosystem"],
                    publication_date=h["publication_date"],
                    prior_ring=h["prior_ring"],
                    current_ring=h["current_ring"],
                    repo_count_delta=h.get("repo_count_delta"),
                    vulnerability_change=h.get("vulnerability_change"),
                    created_at=now,
                )
            )

        self._session.flush()
        return pub
