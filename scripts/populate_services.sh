#!/bin/bash
# =============================================================================
# Populate Services Script
# =============================================================================
# Automatically creates services from repositories and links them
#
# Usage:
#   bash scripts/populate_services.sh
# =============================================================================

set -e

echo "🔧 Populating services from repository data..."

# Copy SQL file to container and execute
docker compose exec -T timescaledb psql -U analyzer -d repo_analyzer < scripts/populate_services.sql

echo "✓ Services populated successfully!"
echo ""
echo "You can now:"
echo "  1. View services in Grafana dashboards"
echo "  2. Compute service metrics: curl -X POST http://localhost:5000/api/compute/service-metrics"
echo "  3. Or click 'Compute Service Metrics' button in the Extraction Progress dashboard"
