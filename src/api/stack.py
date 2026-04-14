"""
Flask API endpoints for technology stack queries.

Provides HTTP endpoints to query technology stack data across repositories
and services. Registered on the same Flask app as rescan.py.

Endpoints:
    GET /api/stack/summary    — org-wide technology summary
    GET /api/stack/by-service — per-service technology breakdown
    GET /api/stack/eol        — EOL / expiring technologies
    GET /api/stack/by-repo    — per-repository technology stack
"""

import logging
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func, text

from src.database import get_session
from src.database.models.repository_stack import RepositoryStack
from src.database.models.technology import Technology

logger = logging.getLogger(__name__)

stack_bp = Blueprint("stack", __name__)


@stack_bp.route("/api/stack/summary", methods=["GET"])
def stack_summary():
    """Org-wide technology summary.

    Query parameters:
        category  — filter by category (language, framework, database, …)
        source    — filter by source (platform_api, heuristic)
        is_eol    — 'true' to return only EOL technologies

    Returns JSON list of {name, category, source, repo_count, is_eol, eol_date}.
    """
    category_filter = request.args.get("category")
    source_filter = request.args.get("source")
    is_eol_filter = request.args.get("is_eol")

    try:
        with get_session() as session:
            q = session.query(
                RepositoryStack.name,
                RepositoryStack.category,
                RepositoryStack.source,
                func.count(func.distinct(RepositoryStack.repo_id)).label("repo_count"),
            ).group_by(
                RepositoryStack.name,
                RepositoryStack.category,
                RepositoryStack.source,
            )

            if category_filter:
                q = q.filter(RepositoryStack.category == category_filter)
            if source_filter:
                q = q.filter(RepositoryStack.source == source_filter)

            rows = q.all()

            # Join EOL data
            tech_map = {
                (t.name, t.category): t
                for t in session.query(Technology).all()
            }

            results = []
            for row in rows:
                tech = tech_map.get((row.name, row.category))
                if is_eol_filter and is_eol_filter.lower() == "true":
                    if not (tech and tech.is_eol):
                        continue
                results.append({
                    "name": row.name,
                    "category": row.category,
                    "source": row.source,
                    "repo_count": row.repo_count,
                    "is_eol": tech.is_eol if tech else None,
                    "eol_date": tech.eol_date.isoformat() if tech and tech.eol_date else None,
                })

            return jsonify({"status": "ok", "data": results, "count": len(results)})

    except Exception as exc:
        logger.error("stack/summary error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@stack_bp.route("/api/stack/by-service", methods=["GET"])
def stack_by_service():
    """Per-service technology breakdown.

    Query parameters:
        name      — filter to a specific technology name
        category  — filter by category

    Returns JSON list of service-level stack entries with EOL status.
    """
    name_filter = request.args.get("name")
    category_filter = request.args.get("category")

    try:
        with get_session() as session:
            sql = text("""
                SELECT
                    s.name AS service_name,
                    rs.category,
                    rs.name AS tech_name,
                    rs.source,
                    COUNT(DISTINCT rs.repo_id) AS repo_count,
                    t.is_eol,
                    t.eol_date
                FROM repository_stack rs
                JOIN repository_services rsvc ON rsvc.repo_id = rs.repo_id
                JOIN services s ON s.service_id = rsvc.service_id
                LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
                WHERE (:name IS NULL OR rs.name = :name)
                  AND (:category IS NULL OR rs.category = :category)
                GROUP BY s.name, rs.category, rs.name, rs.source, t.is_eol, t.eol_date
                ORDER BY s.name, rs.category, rs.name
            """)

            rows = session.execute(
                sql,
                {
                    "name": name_filter,
                    "category": category_filter,
                },
            ).fetchall()

            results = [
                {
                    "service_name": row.service_name,
                    "category": row.category,
                    "tech_name": row.tech_name,
                    "source": row.source,
                    "repo_count": row.repo_count,
                    "is_eol": row.is_eol,
                    "eol_date": row.eol_date.isoformat() if row.eol_date else None,
                }
                for row in rows
            ]

            return jsonify({"status": "ok", "data": results, "count": len(results)})

    except Exception as exc:
        logger.error("stack/by-service error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@stack_bp.route("/api/stack/eol", methods=["GET"])
def stack_eol():
    """Technologies that are EOL or expiring within 90 days.

    Returns JSON list of technologies with affected repo and service counts.
    """
    cutoff = date.today() + timedelta(days=90)

    try:
        with get_session() as session:
            sql = text("""
                SELECT
                    t.name,
                    t.category,
                    t.is_eol,
                    t.eol_date,
                    t.latest_supported_version,
                    COUNT(DISTINCT rs.repo_id) AS affected_repos,
                    COUNT(DISTINCT rsvc.service_id) AS affected_services
                FROM technologies t
                LEFT JOIN repository_stack rs
                    ON rs.name = t.name AND rs.category = t.category
                LEFT JOIN repository_services rsvc ON rsvc.repo_id = rs.repo_id
                WHERE t.is_eol = TRUE
                   OR (t.eol_date IS NOT NULL AND t.eol_date <= :cutoff)
                GROUP BY t.name, t.category, t.is_eol, t.eol_date, t.latest_supported_version
                ORDER BY t.eol_date NULLS LAST, t.name
            """)

            rows = session.execute(sql, {"cutoff": cutoff}).fetchall()

            results = [
                {
                    "name": row.name,
                    "category": row.category,
                    "is_eol": row.is_eol,
                    "eol_date": row.eol_date.isoformat() if row.eol_date else None,
                    "latest_supported_version": row.latest_supported_version,
                    "affected_repos": row.affected_repos,
                    "affected_services": row.affected_services,
                }
                for row in rows
            ]

            return jsonify({"status": "ok", "data": results, "count": len(results)})

    except Exception as exc:
        logger.error("stack/eol error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@stack_bp.route("/api/stack/by-repo", methods=["GET"])
def stack_by_repo():
    """All stack entries for a specific repository, grouped by category.

    Query parameters:
        repo_id  (required) — repository ID to query

    Returns JSON list of stack entries with EOL status.
    """
    repo_id = request.args.get("repo_id")
    if not repo_id:
        return jsonify({"status": "error", "message": "repo_id parameter required"}), 400

    try:
        with get_session() as session:
            sql = text("""
                SELECT
                    rs.category,
                    rs.name,
                    rs.source,
                    rs.percentage,
                    rs.byte_count,
                    rs.confidence,
                    rs.first_seen_at,
                    rs.last_seen_at,
                    t.is_eol,
                    t.eol_date,
                    t.latest_supported_version
                FROM repository_stack rs
                LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
                WHERE rs.repo_id = :repo_id
                ORDER BY rs.category, rs.name
            """)

            rows = session.execute(sql, {"repo_id": repo_id}).fetchall()

            results = [
                {
                    "category": row.category,
                    "name": row.name,
                    "source": row.source,
                    "percentage": float(row.percentage) if row.percentage is not None else None,
                    "byte_count": row.byte_count,
                    "confidence": float(row.confidence) if row.confidence is not None else None,
                    "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                    "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                    "is_eol": row.is_eol,
                    "eol_date": row.eol_date.isoformat() if row.eol_date else None,
                    "latest_supported_version": row.latest_supported_version,
                }
                for row in rows
            ]

            return jsonify({"status": "ok", "data": results, "count": len(results)})

    except Exception as exc:
        logger.error("stack/by-repo error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500
