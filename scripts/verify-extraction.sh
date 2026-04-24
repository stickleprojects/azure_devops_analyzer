#!/usr/bin/env bash
# =============================================================================
# verify-extraction.sh
#
# Post-extraction invariant checker.
#
# Runs three SQL integrity checks against the target database and exits
# non-zero on any violation, printing a human-readable message and a sample
# of offending rows.
#
# Usage:
#   DATABASE_URL=<dsn> bash scripts/verify-extraction.sh
#
# When called from run-tests-docker.sh the DATABASE_URL is provided via the
# same environment that the integration tests use.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL="${DATABASE_URL:-${TEST_DATABASE_URL:-}}"

if [[ -z "$DATABASE_URL" ]]; then
    # Try to build from individual POSTGRES_* variables (same defaults as conftest)
    POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
    POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    POSTGRES_USER="${POSTGRES_USER:-postgres}"
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
    DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/repo_analyzer_test"
fi

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

run_check() {
    local description="$1"
    local query="$2"

    local count
    count=$(PGPASSWORD="${PGPASSWORD:-postgres}" psql "$DATABASE_URL" \
        --no-psqlrc --tuples-only --no-align \
        -c "$query" 2>&1) || {
        echo "ERROR: could not execute query for: $description"
        echo "  $count"
        FAIL=$((FAIL + 1))
        return
    }

    count=$(echo "$count" | tr -d '[:space:]')

    if [[ "$count" -eq 0 ]]; then
        echo "  ✓ $description"
        PASS=$((PASS + 1))
    else
        echo "  ✗ FAIL: $description"
        echo "    Violation count: $count"
        # Print a sample of offending rows
        local sample_query="$3"
        if [[ -n "$sample_query" ]]; then
            echo "    Sample offending rows:"
            PGPASSWORD="${PGPASSWORD:-postgres}" psql "$DATABASE_URL" \
                --no-psqlrc -c "$sample_query" 2>/dev/null | head -20 | sed 's/^/    /'
        fi
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

echo ""
echo "=== verify-extraction.sh: post-extraction invariant checks ==="
echo ""

# 1. No pull_requests row with NULL or dangling author_id
run_check \
    "No pull_requests row with NULL or dangling author_id" \
    "SELECT count(*) FROM pull_requests
     WHERE author_id IS NULL
        OR author_id NOT IN (SELECT id FROM contributors);" \
    "SELECT id, repo_id, pr_number, author_id FROM pull_requests
     WHERE author_id IS NULL
        OR author_id NOT IN (SELECT id FROM contributors)
     LIMIT 10;"

# 2. No pr_reviews row with NULL or dangling reviewer_id
run_check \
    "No pr_reviews row with NULL or dangling reviewer_id" \
    "SELECT count(*) FROM pr_reviews
     WHERE reviewer_id IS NULL
        OR reviewer_id NOT IN (SELECT id FROM contributors);" \
    "SELECT id, pr_id, reviewer_id FROM pr_reviews
     WHERE reviewer_id IS NULL
        OR reviewer_id NOT IN (SELECT id FROM contributors)
     LIMIT 10;"

# 3. No two contributors rows sharing the same normalised email
run_check \
    "No two contributors rows sharing lower(trim(email))" \
    "SELECT count(*) FROM (
         SELECT lower(trim(email)) AS norm_email
         FROM contributors
         GROUP BY lower(trim(email))
         HAVING count(*) > 1
     ) dupes;" \
    "SELECT lower(trim(email)) AS norm_email, count(*) AS occurrences,
            array_agg(id ORDER BY id) AS contributor_ids
     FROM contributors
     GROUP BY lower(trim(email))
     HAVING count(*) > 1
     LIMIT 10;"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo "INVARIANT VIOLATIONS DETECTED — review the output above."
    exit 1
fi

echo "All invariants satisfied."
exit 0
