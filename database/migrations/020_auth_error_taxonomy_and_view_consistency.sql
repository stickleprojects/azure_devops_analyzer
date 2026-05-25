-- Migration 020: Auth error taxonomy and cross-view classification consistency
--
-- Introduces canonical error classification via classify_extraction_error(text)
-- and refactors dashboard-facing extraction/auth views to use the same taxonomy.

CREATE OR REPLACE FUNCTION classify_extraction_error(error_message text)
RETURNS TABLE (
    error_category text,
    error_subcategory text,
    is_credential_failure boolean,
    is_authorization_failure boolean
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    WITH normalized AS (
        SELECT lower(coalesce(error_message, '')) AS msg
    ),
    classified AS (
        SELECT
            msg,
            CASE
                WHEN msg LIKE '%rate limit%'
                  OR msg LIKE '%secondary rate limit%'
                  OR msg LIKE '%abuse detection%'
                  OR msg LIKE '%x-ratelimit-remaining: 0%' THEN 'RATE_LIMIT'
                WHEN msg LIKE '%connection reset%'
                  OR msg LIKE '%connection refused%'
                  OR msg LIKE '%temporary failure in name resolution%' THEN 'NETWORK'
                WHEN msg LIKE '%timed out%'
                  OR msg LIKE '%timeout%'
                  OR msg LIKE '%read timeout%'
                  OR msg LIKE '%connect timeout%' THEN 'TIMEOUT'
                WHEN msg LIKE '%service unavailable%'
                  OR msg LIKE '%bad gateway%'
                  OR msg LIKE '% 502 %'
                  OR msg LIKE '% 503 %'
                  OR msg LIKE '% 504 %'
                  OR msg LIKE '502%'
                  OR msg LIKE '503%'
                  OR msg LIKE '504%' THEN 'SERVICE_UNAVAILABLE'
                WHEN msg LIKE '%bad credentials%'
                  OR msg LIKE '%requires authentication%'
                  OR msg LIKE '%requires user authentication%'
                  OR msg LIKE '%token has expired%'
                  OR msg LIKE '%personal access token used has expired%'
                  OR msg LIKE '%no token%'
                  OR msg LIKE '%missing token%'
                  OR msg LIKE '%token not provided%'
                  OR msg LIKE '%401%'
                  OR msg LIKE '%unauthorized%' THEN 'AUTH'
                WHEN msg LIKE '%resource not accessible by integration%'
                  OR msg LIKE '%insufficient scopes%'
                  OR msg LIKE '%access denied%'
                  OR msg LIKE '%not authorized to access this resource%'
                  OR msg LIKE '%vs30063%'
                  OR msg LIKE '%tf400813%'
                  OR msg LIKE '%permission denied%'
                  OR msg LIKE '%forbidden%'
                  OR msg LIKE '%403%'
                  OR msg LIKE '%not authorized%'
                  OR msg LIKE '%account disabled%'
                  OR msg LIKE '%account suspended%' THEN 'PERMISSION'
                WHEN msg LIKE '%404%'
                  OR msg LIKE '%not found%' THEN 'NOT_FOUND'
                WHEN msg LIKE '%422%'
                  OR msg LIKE '%unprocessable%' THEN 'VALIDATION'
                WHEN msg LIKE '%409%'
                  OR msg LIKE '%conflict%' THEN 'CONFLICT'
                WHEN msg LIKE '%data integrity%'
                  OR msg LIKE '%corrupt data%'
                  OR msg LIKE '%inconsistent data%' THEN 'DATA_INTEGRITY'
                WHEN msg LIKE '%api error%'
                  OR msg LIKE '%upstream api%' THEN 'PLATFORM_API'
                ELSE 'UNKNOWN'
            END AS category
        FROM normalized
    ),
    finalized AS (
        SELECT
            category,
            CASE
                WHEN category = 'AUTH' AND msg LIKE '%bad credentials%' THEN 'AUTH_TOKEN_INVALID'
                WHEN category = 'AUTH' AND (
                    msg LIKE '%token has expired%'
                  OR msg LIKE '%personal access token used has expired%'
                ) THEN 'AUTH_TOKEN_EXPIRED'
                WHEN category = 'AUTH' AND (
                    msg LIKE '%no token%'
                  OR msg LIKE '%missing token%'
                  OR msg LIKE '%token not provided%'
                ) THEN 'AUTH_TOKEN_MISSING'
                WHEN category = 'AUTH' AND (
                    msg LIKE '%requires authentication%'
                  OR msg LIKE '%requires user authentication%'
                  OR msg LIKE '%401%'
                  OR msg LIKE '%unauthorized%'
                ) THEN 'AUTH_UNAUTHORIZED'
                WHEN category = 'PERMISSION' AND (
                    msg LIKE '%resource not accessible by integration%'
                  OR msg LIKE '%insufficient scopes%'
                ) THEN 'PERMISSION_SCOPE_INSUFFICIENT'
                WHEN category = 'PERMISSION' AND (
                    msg LIKE '%access denied%'
                  OR msg LIKE '%not authorized to access this resource%'
                  OR msg LIKE '%vs30063%'
                  OR msg LIKE '%tf400813%'
                ) THEN 'PERMISSION_RESOURCE_DENIED'
                WHEN category = 'PERMISSION' AND (
                    msg LIKE '%account disabled%'
                  OR msg LIKE '%account suspended%'
                ) THEN 'PERMISSION_ACCOUNT_DISABLED'
                WHEN category = 'PERMISSION' AND (
                    msg LIKE '%permission denied%'
                  OR msg LIKE '%forbidden%'
                  OR msg LIKE '%403%'
                  OR msg LIKE '%not authorized%'
                ) THEN 'PERMISSION_FORBIDDEN'
                ELSE NULL
            END AS subcategory
        FROM classified
    )
    SELECT
        category AS error_category,
        subcategory AS error_subcategory,
        category = 'AUTH' AS is_credential_failure,
        category = 'PERMISSION' AS is_authorization_failure
    FROM finalized
$$;

CREATE OR REPLACE VIEW v_extraction_runs_recent AS
SELECT
    r.run_id,
    r.platform,
    r.organization_name,
    r.project_name,
    r.status,
    r.processed_repositories,
    r.total_repositories,
    r.current_repository_id,
    r.updated_at,
    r.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
ORDER BY r.updated_at DESC
LIMIT 20;

CREATE OR REPLACE VIEW v_auth_errors_by_platform AS
SELECT
    r.platform,
    COUNT(*) AS error_count,
    COUNT(DISTINCT r.run_id) AS affected_runs,
    MAX(r.updated_at) AS last_error_time,
    c.error_category
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
WHERE r.status = 'failed'
  AND r.updated_at > NOW() - INTERVAL '24 hours'
  AND c.error_category IN ('AUTH', 'PERMISSION')
GROUP BY r.platform, c.error_category
ORDER BY error_count DESC;

CREATE OR REPLACE VIEW v_auth_errors_24h_total AS
SELECT COALESCE(SUM(error_count), 0) AS auth_errors
FROM v_auth_errors_by_platform;

CREATE OR REPLACE VIEW v_extraction_metrics_with_errors AS
SELECT
    em.id,
    em.run_id,
    em.repository_id,
    COALESCE(r.name, em.repository_id) AS repository_name,
    em.platform,
    em.status,
    em.extraction_started_at,
    em.extraction_completed_at,
    em.extraction_duration_seconds,
    em.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_metrics em
LEFT JOIN repositories r ON em.repository_id = r.repo_id
CROSS JOIN LATERAL classify_extraction_error(em.error_message) c
ORDER BY em.extraction_started_at DESC
LIMIT 500;

CREATE OR REPLACE VIEW v_extraction_metrics_recent AS
SELECT
    COALESCE(r.name, em.repository_id) AS repository,
    em.platform,
    em.status,
    em.extraction_started_at,
    em.extraction_completed_at,
    em.extraction_duration_seconds,
    em.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_metrics em
LEFT JOIN repositories r ON em.repository_id = r.repo_id
CROSS JOIN LATERAL classify_extraction_error(em.error_message) c
ORDER BY em.extraction_started_at DESC
LIMIT 50;

CREATE OR REPLACE VIEW v_extraction_errors_unknown_recent AS
SELECT
    date_trunc('day', r.updated_at) AS day,
    left(r.error_message, 80) AS message_prefix,
    count(*) AS occurrences
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
WHERE r.status = 'failed'
  AND r.error_message IS NOT NULL
  AND c.error_category = 'UNKNOWN'
  AND r.updated_at >= now() - interval '7 days'
GROUP BY 1, 2
ORDER BY occurrences DESC;
