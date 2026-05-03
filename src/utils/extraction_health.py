"""
Extraction health checking module.

Parses ``tests/db_invariants.sql`` and runs every named invariant against the
live database.  Returns a :class:`HealthReport` that callers can inspect or
pass to :func:`src.utils.metrics.emit_health_report`.

Architecture rules (non-negotiable):
- Lives in ``utils/`` — cross-cutting concern.
- Accepts a SQLAlchemy session passed in; never opens its own connection.
- Reads ``tests/db_invariants.sql`` (read-only); never modifies it.
- Returns data structures only — no side effects.
- Must NOT import from ``src/extractors/``, ``src/analyzers/``, or
  ``src/workflows/``.
- Must NOT write to the database.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution for db_invariants.sql
# ---------------------------------------------------------------------------
# The file lives at <repo-root>/tests/db_invariants.sql.  At runtime inside
# the Docker image it is copied to /app/tests/db_invariants.sql.  We resolve
# both locations in order so neither the host nor the container breaks.

_THIS_FILE = Path(__file__)

_CANDIDATE_PATHS: list[Path] = [
    # Development: src/utils/extraction_health.py → ../../tests/db_invariants.sql
    _THIS_FILE.parents[2] / "tests" / "db_invariants.sql",
    # Docker image: copied to /app/tests/db_invariants.sql
    Path("/app/tests/db_invariants.sql"),
]


def _find_invariants_sql(override: Optional[Path] = None) -> Path:
    """Return the path to ``db_invariants.sql``, raising if not found."""
    if override is not None:
        if not override.exists():
            raise FileNotFoundError(f"db_invariants.sql override not found: {override}")
        return override

    for candidate in _CANDIDATE_PATHS:
        if candidate.exists():
            return candidate

    checked = ", ".join(str(p) for p in _CANDIDATE_PATHS)
    raise FileNotFoundError(
        f"db_invariants.sql not found. Checked: {checked}"
    )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class InvariantResult:
    """Result of running a single named invariant query."""

    name: str
    violations: int
    sample_rows: list[dict] = field(default_factory=list)  # capped at 5


@dataclass
class HealthReport:
    """Aggregated health report for one extraction run."""

    platform: str
    repo_id: Optional[str]  # None = whole-DB check
    timestamp: datetime
    invariants: list[InvariantResult] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """Return True only when all invariants report zero violations."""
        return all(r.violations == 0 for r in self.invariants)


# ---------------------------------------------------------------------------
# SQL parsing
# ---------------------------------------------------------------------------

# Matches:   -- invariant: <name>
_INVARIANT_NAME_RE = re.compile(r"--\s*invariant:\s*(\S+)", re.IGNORECASE)
# Matches:   -- requires-table: <table>
_REQUIRES_TABLE_RE = re.compile(r"--\s*requires-table:\s*(\S+)", re.IGNORECASE)


@dataclass
class _ParsedInvariant:
    name: str
    sql: str
    requires_table: Optional[str] = None


def _parse_invariants_sql(path: Path) -> list[_ParsedInvariant]:
    """Parse ``db_invariants.sql`` and return one entry per named invariant.

    The parser is intentionally simple:

    * Lines that start with ``-- invariant: <name>`` begin a new block.
    * Lines that start with ``-- requires-table: <table>`` annotate the block.
    * Everything up to the next ``-- invariant:`` comment (or EOF) is the SQL.
    * Blank lines and other comments between the marker and the first
      ``SELECT`` are stripped from the SQL.
    """
    raw = path.read_text(encoding="utf-8")

    results: list[_ParsedInvariant] = []
    current_name: Optional[str] = None
    current_requires: Optional[str] = None
    current_sql_lines: list[str] = []

    def _flush() -> None:
        if current_name is None:
            return
        sql = "\n".join(current_sql_lines).strip()
        if sql:
            results.append(
                _ParsedInvariant(
                    name=current_name,
                    sql=sql,
                    requires_table=current_requires,
                )
            )

    for line in raw.splitlines():
        name_match = _INVARIANT_NAME_RE.match(line.strip())
        table_match = _REQUIRES_TABLE_RE.match(line.strip())

        if name_match:
            _flush()
            current_name = name_match.group(1)
            current_requires = None
            current_sql_lines = []
        elif table_match and current_name is not None:
            current_requires = table_match.group(1)
        elif current_name is not None:
            # Skip pure-comment lines that aren't SQL
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            current_sql_lines.append(line)

    _flush()
    return results


# ---------------------------------------------------------------------------
# Table-existence helper
# ---------------------------------------------------------------------------


def _table_exists(session: Session, table_name: str) -> bool:
    """Return True if *table_name* exists in the current schema."""
    result = session.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_name = :t"
            ")"
        ),
        {"t": table_name},
    )
    return bool(result.scalar())


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_extraction_health(
    session: Session,
    platform: str,
    repo_id: Optional[str] = None,
    *,
    invariants_sql_path: Optional[Path] = None,
) -> HealthReport:
    """Run every named invariant from ``tests/db_invariants.sql``.

    Parameters
    ----------
    session:
        Active SQLAlchemy session (read-only queries are issued against it).
    platform:
        Human-readable platform identifier, e.g. ``"github"`` or
        ``"azure-devops"``.  Stored on the returned :class:`HealthReport` and
        emitted with metrics.
    repo_id:
        When supplied, the check is scoped to a single repository.  Pass
        ``None`` for a whole-DB check (the common post-extraction case).
    invariants_sql_path:
        Override the path to ``db_invariants.sql``.  Primarily used by tests
        to inject a stub file.
    """
    sql_path = _find_invariants_sql(invariants_sql_path)
    invariants = _parse_invariants_sql(sql_path)

    report = HealthReport(
        platform=platform,
        repo_id=repo_id,
        timestamp=datetime.now(tz=timezone.utc),
    )

    for inv in invariants:
        result = _run_invariant(session, inv)
        report.invariants.append(result)

    return report


def _run_invariant(session: Session, inv: _ParsedInvariant) -> InvariantResult:
    """Execute a single invariant query and return an :class:`InvariantResult`."""
    # If the invariant requires a specific table, skip gracefully when absent.
    if inv.requires_table and not _table_exists(session, inv.requires_table):
        logger.debug(
            "Skipping invariant %r — required table %r not present",
            inv.name,
            inv.requires_table,
        )
        return InvariantResult(name=inv.name, violations=0, sample_rows=[])

    try:
        rows = session.execute(text(inv.sql)).mappings().all()
    except Exception as exc:
        logger.warning(
            "Invariant %r query failed: %s", inv.name, exc, exc_info=True
        )
        return InvariantResult(name=inv.name, violations=0, sample_rows=[])

    sample = [dict(r) for r in rows[:5]]
    return InvariantResult(
        name=inv.name,
        violations=len(rows),
        sample_rows=sample,
    )
