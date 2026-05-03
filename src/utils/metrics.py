"""
Metrics emission module.

Emits :class:`~src.utils.extraction_health.HealthReport` results as structured
log lines and, when the ``extraction_health_log`` table is available in the
database, persists them for Grafana dashboards to query.

Design notes
------------
* **No Prometheus dependency** — ``prometheus_client`` is not in the project's
  requirements.  Emission falls back to structured logs + PostgreSQL storage.
  When Prometheus infrastructure is wired in future, this module can be
  extended with a ``prometheus_client`` gauge alongside the existing emission.
* Writes are fire-and-forget; failures are logged as warnings and swallowed so
  that a bug here can never crash an extraction.
* Intentionally does not import from ``src/extractors/``, ``src/analyzers/``,
  or ``src/workflows/``.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from src.utils.extraction_health import HealthReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_health_report(report: HealthReport) -> None:
    """Emit *report* as structured log lines and persist to the DB if possible.

    A warning-level log line is emitted for each invariant with violations > 0.
    One info-level summary line is always emitted.

    Parameters
    ----------
    report:
        A :class:`~src.utils.extraction_health.HealthReport` returned by
        :func:`~src.utils.extraction_health.compute_extraction_health`.
    """
    try:
        _emit_logs(report)
    except Exception as exc:
        logger.warning("Failed to emit health report logs: %s", exc)

    try:
        _persist_to_db(report)
    except Exception as exc:
        logger.warning("Failed to persist health report to DB: %s", exc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _emit_logs(report: HealthReport) -> None:
    """Write structured log lines for the health report."""
    total_violations = sum(r.violations for r in report.invariants)
    checked = len(report.invariants)

    logger.info(
        "extraction-health summary: platform=%s repo_id=%s "
        "checked=%d violations=%d healthy=%s",
        report.platform,
        report.repo_id,
        checked,
        total_violations,
        report.is_healthy,
    )

    for inv in report.invariants:
        if inv.violations > 0:
            logger.warning(
                "extraction-health violation: platform=%s repo_id=%s "
                "invariant=%s violations=%d sample=%r",
                report.platform,
                report.repo_id,
                inv.name,
                inv.violations,
                inv.sample_rows,
            )


def _persist_to_db(report: HealthReport) -> None:
    """Persist the health report to ``extraction_health_log`` if the table exists.

    Uses its own short-lived session via :func:`~src.database.connection.session_scope`
    so that a DB write failure does not roll back any caller transaction.
    The write is skipped gracefully when the table has not yet been created
    (e.g. during CI runs against a schema from an older migration set).
    """
    from sqlalchemy import text

    from src.database.connection import session_scope

    with session_scope() as session:
        # Check table exists before attempting insert
        exists = session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_name = 'extraction_health_log'"
                ")"
            )
        ).scalar()

        if not exists:
            logger.debug(
                "extraction_health_log table not present — skipping DB persist"
            )
            return

        for inv in report.invariants:
            session.execute(
                text(
                    "INSERT INTO extraction_health_log "
                    "  (platform, repo_id, invariant_name, violations, sample_rows, checked_at) "
                    "VALUES "
                    "  (:platform, :repo_id, :invariant_name, :violations, :sample_rows::jsonb, :checked_at)"
                ),
                {
                    "platform": report.platform,
                    "repo_id": report.repo_id,
                    "invariant_name": inv.name,
                    "violations": inv.violations,
                    "sample_rows": _json_safe(inv.sample_rows),
                    "checked_at": report.timestamp,
                },
            )


def _json_safe(obj: object) -> str:
    """Serialise *obj* to a JSON string suitable for a jsonb column."""
    import json

    def _default(o: object) -> str:
        return str(o)

    return json.dumps(obj, default=_default)
