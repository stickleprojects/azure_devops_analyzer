import pytest
from sqlalchemy import text


PATTERN_CASES = [
    ("bad credentials", "AUTH", "AUTH_TOKEN_INVALID"),
    ("request requires authentication", "AUTH", "AUTH_UNAUTHORIZED"),
    ("token has expired", "AUTH", "AUTH_TOKEN_EXPIRED"),
    ("The Personal Access Token used has expired.", "AUTH", "AUTH_TOKEN_EXPIRED"),
    ("missing token", "AUTH", "AUTH_TOKEN_MISSING"),
    ("token not provided", "AUTH", "AUTH_TOKEN_MISSING"),
    ("401", "AUTH", "AUTH_UNAUTHORIZED"),
    ("resource not accessible by integration", "PERMISSION", "PERMISSION_SCOPE_INSUFFICIENT"),
    ("insufficient scopes", "PERMISSION", "PERMISSION_SCOPE_INSUFFICIENT"),
    ("access denied", "PERMISSION", "PERMISSION_RESOURCE_DENIED"),
    ("not authorized to access this resource", "PERMISSION", "PERMISSION_RESOURCE_DENIED"),
    ("VS30063", "PERMISSION", "PERMISSION_RESOURCE_DENIED"),
    ("TF400813", "PERMISSION", "PERMISSION_RESOURCE_DENIED"),
    ("permission denied", "PERMISSION", "PERMISSION_FORBIDDEN"),
    ("forbidden", "PERMISSION", "PERMISSION_FORBIDDEN"),
    ("403", "PERMISSION", "PERMISSION_FORBIDDEN"),
    ("account suspended", "PERMISSION", "PERMISSION_ACCOUNT_DISABLED"),
    ("rate limit exceeded", "RATE_LIMIT", None),
    ("secondary rate limit hit", "RATE_LIMIT", None),
    ("x-ratelimit-remaining: 0", "RATE_LIMIT", None),
    ("abuse detection mechanism", "RATE_LIMIT", None),
    ("connection reset by peer", "NETWORK", None),
    ("connection refused", "NETWORK", None),
    ("temporary failure in name resolution", "NETWORK", None),
    ("request timed out", "TIMEOUT", None),
    ("connect timeout", "TIMEOUT", None),
    ("service unavailable", "SERVICE_UNAVAILABLE", None),
    ("502 Bad Gateway", "SERVICE_UNAVAILABLE", None),
    ("404 not found", "NOT_FOUND", None),
    ("422 unprocessable entity", "VALIDATION", None),
]


@pytest.mark.integration
@pytest.mark.parametrize("message,expected_category,expected_subcategory", PATTERN_CASES)
def test_classify_extraction_error_pattern_table(db_session, message, expected_category, expected_subcategory):
    row = db_session.execute(
        text(
            """
            SELECT error_category, error_subcategory
            FROM classify_extraction_error(:message)
            """
        ),
        {"message": message},
    ).fetchone()

    assert row is not None
    assert row.error_category == expected_category
    assert row.error_subcategory == expected_subcategory


@pytest.mark.integration
def test_classify_extraction_error_precedence_rate_limit_over_permission(db_session):
    row = db_session.execute(
        text(
            """
            SELECT error_category, error_subcategory
            FROM classify_extraction_error('403 forbidden due to secondary rate limit')
            """
        )
    ).fetchone()

    assert row is not None
    assert row.error_category == "RATE_LIMIT"
    assert row.error_subcategory is None


@pytest.mark.integration
def test_classify_extraction_error_unknown_fallback(db_session):
    row = db_session.execute(
        text(
            """
            SELECT error_category, error_subcategory, is_credential_failure, is_authorization_failure
            FROM classify_extraction_error('unexpected parser exploded in module x')
            """
        )
    ).fetchone()

    assert row is not None
    assert row.error_category == "UNKNOWN"
    assert row.error_subcategory is None
    assert row.is_credential_failure is False
    assert row.is_authorization_failure is False
