#!/usr/bin/env bash
# =============================================================================
# capture-api-snapshot.sh
#
# Captures raw API responses from a small real repository and saves them as
# anonymised fixture scenario JSON under tests/fixtures/snapshots/<platform>/.
#
# Usage:
#   # GitHub:
#   GITHUB_TOKEN=<pat> GITHUB_ORG=<org> GITHUB_REPO=<repo> \
#       bash scripts/capture-api-snapshot.sh --platform github
#
#   # Azure DevOps:
#   AZURE_DEVOPS_PAT=<pat> AZURE_DEVOPS_ORG_URL=<url> \
#   AZURE_DEVOPS_PROJECT=<project> AZURE_DEVOPS_REPO=<repo> \
#       bash scripts/capture-api-snapshot.sh --platform azure_devops
#
# Environment variables:
#   GITHUB_TOKEN            GitHub personal access token
#   GITHUB_ORG              GitHub organisation/user
#   GITHUB_REPO             Repository name (e.g. my-small-repo)
#   AZURE_DEVOPS_PAT        Azure DevOps personal access token
#   AZURE_DEVOPS_ORG_URL    Organisation URL (e.g. https://dev.azure.com/myorg)
#   AZURE_DEVOPS_PROJECT    Project name
#   AZURE_DEVOPS_REPO       Repository name
#
# After running this script, run:
#   python scripts/anonymise-snapshot.py
# to strip PII before committing.
#
# Size budget: keep raw captures under 500 KB total.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SNAPSHOTS_ROOT="${PROJECT_ROOT}/tests/fixtures/snapshots"
RAW_DIR="${PROJECT_ROOT}/tmp/snapshots-raw"
PLATFORM="github"

# ─── Argument parsing ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform) PLATFORM="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

mkdir -p "${RAW_DIR}/${PLATFORM}"

# ─── Helper: URL-encode a single path segment ────────────────────────────────
# Usage: url_encode_path <value>
url_encode_path() {
    _SEG_VALUE="$1" python3 -c "import os, urllib.parse; print(urllib.parse.quote(os.environ['_SEG_VALUE'], safe=''))"
}

# ─── GitHub ──────────────────────────────────────────────────────────────────
if [[ "${PLATFORM}" == "github" ]]; then
    : "${GITHUB_TOKEN:?GITHUB_TOKEN must be set}"
    : "${GITHUB_ORG:?GITHUB_ORG must be set}"
    : "${GITHUB_REPO:?GITHUB_REPO must be set}"

    BASE="https://api.github.com/repos/$(url_encode_path "${GITHUB_ORG}")/$(url_encode_path "${GITHUB_REPO}")"
    AUTH="Authorization: Bearer ${GITHUB_TOKEN}"

    echo "Capturing GitHub commits for ${GITHUB_ORG}/${GITHUB_REPO}…"
    curl -s -H "${AUTH}" -H "Accept: application/vnd.github+json" \
        "${BASE}/commits?per_page=30" \
        > "${RAW_DIR}/${PLATFORM}/commits.json"
    echo "  ✓ commits.json"

    echo "Capturing GitHub pull requests…"
    curl -s -H "${AUTH}" -H "Accept: application/vnd.github+json" \
        "${BASE}/pulls?state=all&per_page=20&sort=updated&direction=desc" \
        > "${RAW_DIR}/${PLATFORM}/pull_requests.json"
    echo "  ✓ pull_requests.json"

    # Capture reviews for the most recent PR
    PR_NUMBER=$(RAW_FILE="${RAW_DIR}/${PLATFORM}/pull_requests.json" python3 -c "
import json, os, sys
with open(os.environ['RAW_FILE']) as f:
    prs = json.load(f)
if prs:
    print(prs[0]['number'])
")
    if [[ -n "${PR_NUMBER:-}" ]]; then
        echo "Capturing reviews for PR #${PR_NUMBER}…"
        curl -s -H "${AUTH}" -H "Accept: application/vnd.github+json" \
            "${BASE}/pulls/${PR_NUMBER}/reviews" \
            > "${RAW_DIR}/${PLATFORM}/pr_reviews.json"
        echo "  ✓ pr_reviews.json"
    fi

# ─── Azure DevOps ────────────────────────────────────────────────────────────
elif [[ "${PLATFORM}" == "azure_devops" ]]; then
    : "${AZURE_DEVOPS_PAT:?AZURE_DEVOPS_PAT must be set}"
    : "${AZURE_DEVOPS_ORG_URL:?AZURE_DEVOPS_ORG_URL must be set}"
    : "${AZURE_DEVOPS_PROJECT:?AZURE_DEVOPS_PROJECT must be set}"
    : "${AZURE_DEVOPS_REPO:?AZURE_DEVOPS_REPO must be set}"

    B64_PAT=$(printf ":%s" "${AZURE_DEVOPS_PAT}" | base64)
    AUTH="Authorization: Basic ${B64_PAT}"
    ORG_URL="${AZURE_DEVOPS_ORG_URL%/}"
    BASE="${ORG_URL}/$(url_encode_path "${AZURE_DEVOPS_PROJECT}")/_apis/git/repositories/$(url_encode_path "${AZURE_DEVOPS_REPO}")"
    API_VER="api-version=7.1"

    echo "Capturing Azure DevOps commits…"
    curl -s -H "${AUTH}" \
        "${BASE}/commits?searchCriteria.\$top=30&${API_VER}" \
        > "${RAW_DIR}/${PLATFORM}/commits.json"
    echo "  ✓ commits.json"

    echo "Capturing Azure DevOps pull requests…"
    curl -s -H "${AUTH}" \
        "${BASE}/pullrequests?searchCriteria.status=all&searchCriteria.\$top=20&${API_VER}" \
        > "${RAW_DIR}/${PLATFORM}/pull_requests.json"
    echo "  ✓ pull_requests.json"

    PR_ID=$(RAW_FILE="${RAW_DIR}/${PLATFORM}/pull_requests.json" python3 -c "
import json, os, sys
with open(os.environ['RAW_FILE']) as f:
    data = json.load(f)
prs = data.get('value', [])
if prs:
    print(prs[0]['pullRequestId'])
")
    if [[ -n "${PR_ID:-}" ]]; then
        echo "Capturing reviewers for PR ${PR_ID}…"
        curl -s -H "${AUTH}" \
            "${ORG_URL}/$(url_encode_path "${AZURE_DEVOPS_PROJECT}")/_apis/git/pullrequests/${PR_ID}/reviewers?${API_VER}" \
            > "${RAW_DIR}/${PLATFORM}/pr_reviews.json"
        echo "  ✓ pr_reviews.json"
    fi

else
    echo "Unknown platform: ${PLATFORM}. Use --platform github or --platform azure_devops."
    exit 1
fi

echo ""
echo "Raw captures saved to: ${RAW_DIR}/${PLATFORM}/"
echo ""
echo "Next step — anonymise before committing:"
echo "  python scripts/anonymise-snapshot.py --platform ${PLATFORM}"
