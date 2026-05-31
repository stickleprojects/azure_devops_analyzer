"""Shared workflow helpers for handling per-scope repository listing.

Both the GitHub and Azure DevOps workflows iterate over a hierarchy of
scopes (org → optional project → repositories) and call
``extractor.get_repositories(...)`` to enumerate the repos in that scope.

If the PAT/token lacks permission for a single scope, the historical
behaviour diverged: the Azure DevOps extractor raised and aborted the
whole run, while the GitHub extractor silently returned ``[]`` with only
a debug log. Neither was correct: the run should skip the inaccessible
scope, log a visible warning, and continue with the next.

``list_repositories_or_skip`` centralises that decision so both workflows
behave identically. The only platform-specific bit — the exception's
status-code shape — is handled inside
``src.extractors.errors.is_permission_error``.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.extractors.base import RepositoryData, RepositoryExtractor
from src.extractors.errors import http_status, is_permission_error

logger = logging.getLogger(__name__)


def list_repositories_or_skip(
    extractor: RepositoryExtractor,
    organization: str,
    *,
    project: Optional[str] = None,
    scope_label: str,
) -> Optional[list[RepositoryData]]:
    """List repositories for a scope, returning ``None`` if it is inaccessible.

    Args:
        extractor: The platform extractor.
        organization: Organization / user name to list under.
        project: Optional project name (Azure DevOps only — GitHub ignores it).
        scope_label: Human-readable label for the scope used in log messages
            (e.g. ``"project MyOrg/PaymentsTeam"`` or ``"org acme-corp"``).

    Returns:
        The list of repositories, or ``None`` if the scope was skipped
        because the caller lacks permission. Returning ``None`` rather than
        ``[]`` lets the workflow distinguish "scope exists but is empty"
        from "scope is inaccessible and was skipped" — useful for deciding
        whether to record an extraction-run row.
    """
    try:
        if project is not None:
            return extractor.get_repositories(organization, project=project)
        return extractor.get_repositories(organization)
    except Exception as exc:
        if is_permission_error(exc):
            logger.warning(
                "Skipping %s: insufficient permissions to list repositories "
                "(HTTP %s) — continuing with remaining scopes",
                scope_label,
                http_status(exc),
            )
            return None
        raise
