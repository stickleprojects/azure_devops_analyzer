"""
Integration Tests Package

End-to-end tests that verify actual data flows through the complete pipeline:
- Real GitHub API calls (with live credentials)
- Real database operations (test PostgreSQL)
- Real enrichment from OSV.dev and endoflife.date

These tests validate that:
1. Data extraction works with actual APIs
2. Enrichment successfully populates database fields
3. Database schema and constraints are correct
4. Timezone handling is UTC-aware
5. No silent data loss or corruption occurs

Run with: pytest tests/integration/ -v
"""
