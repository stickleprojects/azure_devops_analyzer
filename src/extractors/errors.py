"""Cross-platform classification of extractor exceptions.

Extractors raise platform-specific exception types (``github.GithubException``,
``azure.devops.exceptions.AzureDevOpsServiceError``) whose HTTP status surfaces
under slightly different attribute names. Workflows need a single predicate
that answers "should we treat this as 'no access to this scope' and skip" so
the skip behaviour is identical across platforms.

The classifier here is duck-typed on the attribute names the SDKs already
expose, so this module deliberately avoids importing either SDK.
"""

from __future__ import annotations

from typing import Optional


_PERMISSION_STATUSES = frozenset({401, 403, 404})


def http_status(exc: BaseException) -> Optional[int]:
    """Return the HTTP status carried by ``exc``, or ``None`` if there isn't one.

    Looks at, in order:

    * ``exc.status`` — used by PyGithub's ``GithubException``.
    * ``exc.status_code`` — used by ``AzureDevOpsServiceError``.
    * ``exc.inner_exception.status_code`` — Azure DevOps wraps the real HTTP
      error here when the outer error is generic.
    """
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status

    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status

    inner = getattr(exc, "inner_exception", None)
    if inner is not None:
        status = getattr(inner, "status_code", None)
        if isinstance(status, int):
            return status

    return None


def is_permission_error(exc: BaseException) -> bool:
    """Return ``True`` if ``exc`` indicates the caller cannot access a resource.

    Covers 401 (unauthorised), 403 (forbidden), and 404. 404 is included
    because both GitHub and Azure DevOps return it for private resources the
    caller cannot see — distinguishing "not found" from "no access" is not
    possible from the response alone, and for the purposes of workflow
    behaviour the right action is identical: skip the scope and continue.
    """
    return http_status(exc) in _PERMISSION_STATUSES
