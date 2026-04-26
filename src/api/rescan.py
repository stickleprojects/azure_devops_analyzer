"""
Flask API for triggering on-demand repository rescans.

Provides HTTP endpoints to trigger GitHub and Azure DevOps extraction tasks.
Useful for dashboard integration and manual rescan triggers.

Usage:
    python -m src.api.rescan
    
    Then access:
    POST http://localhost:5000/api/rescan/github
    POST http://localhost:5000/api/rescan/azure-devops
    POST http://localhost:5000/api/compute/service-metrics
"""

import csv
import io
import logging
from flask import Flask, jsonify, request, Response
from src.scheduler.celery_app import celery_app
from src.database import get_session
from src.database.models.repository import Repository
from src.database.models.package import Package
from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.service import RepositoryService, Service
from src.database.models.radar import RadarBlip as RadarBlipModel, RadarBlipHistory, RadarPublication

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Register technology stack blueprint
from src.api.stack import stack_bp  # noqa: E402
app.register_blueprint(stack_bp)


@app.route("/api/rescan/github", methods=["GET", "POST"])
def trigger_github_rescan():
    """
    Trigger an on-demand GitHub repository rescan.
    
    Sends the run_github_extraction task to Celery for immediate execution.
    
    Accepts:
        GET /api/rescan/github (from dashboard links)
        POST /api/rescan/github (from API calls)
    
    Returns:
        JSON with task_id and status
    """
    try:
        logger.info("Triggering GitHub rescan via API")
        
        # Send task to Celery
        task = celery_app.send_task("tasks.run_github_extraction")
        
        logger.info(f"GitHub rescan task submitted: {task.id}")
        
        return jsonify({
            "status": "submitted",
            "task_id": task.id,
            "message": "GitHub extraction task queued for immediate execution",
        }), 202
        
    except Exception as e:
        logger.error(f"Failed to trigger GitHub rescan: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/rescan/azure-devops", methods=["GET", "POST"])
def trigger_azure_rescan():
    """
    Trigger an on-demand Azure DevOps repository rescan.
    
    Sends the run_azure_devops_extraction_task task to Celery for immediate execution.
    
    Accepts:
        GET /api/rescan/azure-devops (from dashboard links)
        POST /api/rescan/azure-devops (from API calls)
    
    Returns:
        JSON with task_id and status
    """
    try:
        logger.info("Triggering Azure DevOps rescan via API")
        
        # Send task to Celery
        task = celery_app.send_task("tasks.run_azure_devops_extraction_task")
        
        logger.info(f"Azure DevOps rescan task submitted: {task.id}")
        
        return jsonify({
            "status": "submitted",
            "task_id": task.id,
            "message": "Azure DevOps extraction task queued for immediate execution",
        }), 202
        
    except Exception as e:
        logger.error(f"Failed to trigger Azure DevOps rescan: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/rescan/repository/<path:repo_id>", methods=["POST", "DELETE"])
def force_rescan_repository(repo_id: str):
    """
    Force a rescan of a specific repository by clearing its last_analyzed_at timestamp.
    
    This bypasses the min_scan_interval check and allows immediate re-extraction.
    
    Args:
        repo_id: Repository identifier (URL-encoded)
        
    Methods:
        POST   - Clear last_analyzed_at (prepare for rescan)
        DELETE - Same as POST (RESTful alternative)
        
    Examples:
        POST /api/rescan/repository/stickleprojects%2Fazure_devops_analyzer
        POST /api/rescan/repository/12345678-1234-1234-1234-123456789abc
    
    Returns:
        JSON with status and repository info
    """
    try:
        logger.info(f"Force rescan requested for repository: {repo_id}")
        
        session = get_session()
        try:
            # Find the repository
            repo = session.query(Repository).filter_by(repo_id=repo_id).first()
            
            if not repo:
                return jsonify({
                    "status": "error",
                    "message": f"Repository not found: {repo_id}",
                }), 404
            
            # Store previous timestamp
            previous_analyzed_at = repo.last_analyzed_at
            
            # Clear the last_analyzed_at to force rescan
            repo.last_analyzed_at = None
            session.commit()
            
            logger.info(
                f"Cleared last_analyzed_at for {repo.name} "
                f"(was: {previous_analyzed_at})"
            )
            
            return jsonify({
                "status": "success",
                "repository": {
                    "repo_id": repo.repo_id,
                    "name": repo.name,
                    "previous_analyzed_at": previous_analyzed_at.isoformat() if previous_analyzed_at else None,
                },
                "message": f"Repository {repo.name} marked for forced rescan. Trigger a platform rescan to process it.",
                "next_steps": [
                    "POST /api/rescan/github (if GitHub repo)",
                    "POST /api/rescan/azure-devops (if Azure DevOps repo)",
                ],
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to force rescan for repository {repo_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/repositories", methods=["GET"])
def list_repositories():
    """
    List all repositories in the database.
    
    Query Parameters:
        limit (int): Maximum number of repositories to return (default: 100)
        offset (int): Offset for pagination (default: 0)
        search (str): Filter by repository name (case-insensitive partial match)
        
    Returns:
        JSON with list of repositories
    """
    try:
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', '').strip()
        
        session = get_session()
        try:
            query = session.query(Repository).filter(Repository.is_active == True)
            
            if search:
                query = query.filter(Repository.name.ilike(f'%{search}%'))
            
            total = query.count()
            repos = query.order_by(Repository.name).limit(limit).offset(offset).all()
            
            return jsonify({
                "status": "success",
                "total": total,
                "count": len(repos),
                "limit": limit,
                "offset": offset,
                "repositories": [
                    {
                        "repo_id": r.repo_id,
                        "name": r.name,
                        "url": r.url,
                        "last_analyzed_at": r.last_analyzed_at.isoformat() if r.last_analyzed_at else None,
                        "is_active": r.is_active,
                    }
                    for r in repos
                ],
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to list repositories: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/compute/service-metrics", methods=["GET", "POST"])
def compute_service_metrics():
    """
    Trigger service metrics computation.
    
    Computes and persists service-level metrics for repositories.
    
    Query Parameters / JSON Body:
        service_id (int, optional): Specific service ID (omit for all services)
        period_start (str, optional): Start date YYYY-MM-DD (default: first day of current month)
        period_end (str, optional): End date YYYY-MM-DD (default: today)
        
    Examples:
        GET  /api/compute/service-metrics
        POST /api/compute/service-metrics
        GET  /api/compute/service-metrics?service_id=5
        POST /api/compute/service-metrics?period_start=2025-01-01&period_end=2025-12-31
        POST /api/compute/service-metrics
             Content-Type: application/json
             {"service_id": 5, "period_start": "2025-01-01"}
    
    Returns:
        JSON with task_id and status
    """
    try:
        # Extract parameters from query string or JSON body
        if request.is_json:
            params = request.get_json()
        else:
            params = request.args.to_dict()
        
        service_id = params.get('service_id')
        period_start = params.get('period_start')
        period_end = params.get('period_end')
        
        # Convert service_id to int if provided
        if service_id is not None:
            try:
                service_id = int(service_id)
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "service_id must be an integer",
                }), 400
        
        logger.info(
            f"Triggering service metrics computation via API "
            f"(service_id={service_id}, period_start={period_start}, period_end={period_end})"
        )
        
        # Send task to Celery
        task = celery_app.send_task(
            "tasks.compute_service_metrics",
            kwargs={
                "service_id": service_id,
                "period_start": period_start,
                "period_end": period_end,
            }
        )
        
        logger.info(f"Service metrics computation task submitted: {task.id}")
        
        response_data = {
            "status": "submitted",
            "task_id": task.id,
            "message": "Service metrics computation task queued for execution",
            "parameters": {
                "service_id": service_id or "all",
                "period_start": period_start or "first day of current month",
                "period_end": period_end or "today",
            }
        }
        
        return jsonify(response_data), 202
        
    except Exception as e:
        logger.error(f"Failed to trigger service metrics computation: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON with status
    """
    try:
        # Verify Celery connection
        celery_app.Control().inspect().ping()
        status = "healthy"
        code = 200
    except Exception as e:
        logger.warning(f"Health check: Celery connection issue: {e}")
        status = "degraded"
        code = 503
    
    return jsonify({
        "status": status,
        "service": "extraction-api",
    }), code


@app.route("/api/packages/search", methods=["GET"])
def search_packages():
    """
    Search for packages by name and/or ecosystem.

    Query params:
      ?name=       partial match on package_name
      ?ecosystem=  exact match
      ?version=    when provided, filters repository_dependencies to this exact version
                   and returns repos list instead of aggregate counts

    Returns:
      Without ?version: aggregate counts per package
      With    ?version: repos/services using that exact version
    """
    name = request.args.get("name", "").strip()
    ecosystem = request.args.get("ecosystem", "").strip()
    version = request.args.get("version", "").strip()

    try:
        with get_session() as session:
            query = session.query(Package)
            if name:
                query = query.filter(Package.package_name.ilike(f"%{name}%"))
            if ecosystem:
                query = query.filter(Package.ecosystem == ecosystem)

            packages = query.all()

            if version:
                results = []
                for pkg in packages:
                    repo_deps = (
                        session.query(RepositoryDependency)
                        .filter_by(
                            package_name=pkg.package_name,
                            ecosystem=pkg.ecosystem,
                            version=version,
                        )
                        .all()
                    )
                    if repo_deps:
                        results.append({
                            "package_name": pkg.package_name,
                            "ecosystem": pkg.ecosystem,
                            "version": version,
                            "repos": [rd.repo_id for rd in repo_deps],
                        })
                return jsonify(results)
            else:
                results = []
                for pkg in packages:
                    repo_count = (
                        session.query(RepositoryDependency)
                        .filter_by(package_name=pkg.package_name, ecosystem=pkg.ecosystem)
                        .distinct(RepositoryDependency.repo_id)
                        .count()
                    )
                    results.append({
                        "package_name": pkg.package_name,
                        "ecosystem": pkg.ecosystem,
                        "latest_version": pkg.latest_version,
                        "is_eol": pkg.is_eol,
                        "eol_date": pkg.eol_date.isoformat() if pkg.eol_date else None,
                        "repo_count": repo_count,
                    })
                return jsonify(results)
    except Exception as e:
        logger.error("Package search error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/by-repo", methods=["GET"])
def packages_by_repo():
    """
    All packages used by a specific repository.

    Query params:
      ?repo_id=   required

    Returns per-repo dependency rows joined with package metadata.
    """
    repo_id = request.args.get("repo_id", "").strip()
    if not repo_id:
        return jsonify({"status": "error", "message": "repo_id is required"}), 400

    try:
        with get_session() as session:
            deps = (
                session.query(RepositoryDependency)
                .filter_by(repo_id=repo_id)
                .all()
            )
            results = []
            for dep in deps:
                pkg = (
                    session.query(Package)
                    .filter_by(package_name=dep.package_name, ecosystem=dep.ecosystem)
                    .first()
                )
                results.append({
                    "package_name": dep.package_name,
                    "ecosystem": dep.ecosystem,
                    "version": dep.version,
                    "is_dev_dependency": dep.is_dev_dependency,
                    "has_known_vulnerabilities": dep.has_known_vulnerabilities,
                    "latest_version": pkg.latest_version if pkg else None,
                    "is_eol": pkg.is_eol if pkg else None,
                    "eol_date": pkg.eol_date.isoformat() if pkg and pkg.eol_date else None,
                })
            return jsonify(results)
    except Exception as e:
        logger.error("Packages by-repo error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/vulnerable", methods=["GET"])
def vulnerable_packages():
    """
    Repos where has_known_vulnerabilities=true, grouped by package.

    Returns package name, repo count, and CVE summary.
    """
    try:
        with get_session() as session:
            rows = (
                session.query(RepositoryDependency)
                .filter_by(has_known_vulnerabilities=True)
                .all()
            )
            by_package: dict = {}
            for dep in rows:
                key = (dep.package_name, dep.ecosystem)
                if key not in by_package:
                    pkg = (
                        session.query(Package)
                        .filter_by(package_name=dep.package_name, ecosystem=dep.ecosystem)
                        .first()
                    )
                    cves = (
                        [v.cve_id for v in pkg.vulnerabilities if v.cve_id]
                        if pkg else []
                    )
                    by_package[key] = {
                        "package_name": dep.package_name,
                        "ecosystem": dep.ecosystem,
                        "repo_count": 0,
                        "cves": cves,
                    }
                by_package[key]["repo_count"] += 1

            return jsonify(list(by_package.values()))
    except Exception as e:
        logger.error("Vulnerable packages error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/eol", methods=["GET"])
def eol_packages():
    """
    Packages that are EOL or expiring within 90 days, with repo counts.
    """
    from datetime import date, timedelta
    cutoff = date.today() + timedelta(days=90)

    try:
        with get_session() as session:
            pkgs = (
                session.query(Package)
                .filter(
                    (Package.is_eol == True) |  # noqa: E712
                    ((Package.eol_date != None) & (Package.eol_date <= cutoff))  # noqa: E711
                )
                .all()
            )
            results = []
            for pkg in pkgs:
                repo_count = (
                    session.query(RepositoryDependency)
                    .filter_by(package_name=pkg.package_name, ecosystem=pkg.ecosystem)
                    .distinct(RepositoryDependency.repo_id)
                    .count()
                )
                results.append({
                    "package_name": pkg.package_name,
                    "ecosystem": pkg.ecosystem,
                    "is_eol": pkg.is_eol,
                    "eol_date": pkg.eol_date.isoformat() if pkg.eol_date else None,
                    "repo_count": repo_count,
                })
            return jsonify(results)
    except Exception as e:
        logger.error("EOL packages error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/by-service", methods=["GET"])
def packages_by_service():
    """
    Services that have repos using a specific package.

    Query params:
      ?name=       required; exact match on package_name
      ?ecosystem=  optional; exact match
      ?version=    optional; filter to repos on this exact version

    Returns one row per service that has >=1 repo using the package,
    ordered by service_name. Repos not linked to any service are excluded.
    """
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"status": "error", "message": "name is required"}), 400

    ecosystem = request.args.get("ecosystem", "").strip()
    version = request.args.get("version", "").strip()

    try:
        with get_session() as session:
            query = (
                session.query(
                    Service.service_id,
                    Service.name,
                    RepositoryDependency.repo_id,
                    RepositoryDependency.version,
                )
                .join(RepositoryService, RepositoryService.service_id == Service.service_id)
                .join(
                    RepositoryDependency,
                    RepositoryDependency.repo_id == RepositoryService.repo_id,
                )
                .filter(RepositoryDependency.package_name == name)
            )
            if ecosystem:
                query = query.filter(RepositoryDependency.ecosystem == ecosystem)
            if version:
                query = query.filter(RepositoryDependency.version == version)
            rows = query.all()

            by_service: dict = {}
            for row in rows:
                key = row.service_id
                if key not in by_service:
                    by_service[key] = {
                        "service_name": row.name,
                        "repos": set(),
                        "versions": set(),
                    }
                by_service[key]["repos"].add(row.repo_id)
                if row.version:
                    by_service[key]["versions"].add(row.version)

            results = [
                {
                    "service_name": v["service_name"],
                    "repo_count": len(v["repos"]),
                    "versions_in_use": sorted(v["versions"]),
                }
                for v in sorted(by_service.values(), key=lambda x: x["service_name"])
            ]
            return jsonify(results)
    except Exception as e:
        logger.error("Packages by-service error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/radar", methods=["GET"])
def get_radar():
    """
    Return the latest Tech Radar publication in Thoughtworks format.

    https://github.com/thoughtworks/build-your-own-radar/blob/master/doc/data_format.md

    Returns:
        JSON with documentTitle, quadrants, rings, and entries.
    """
    try:
        with get_session() as session:
            pub = (
                session.query(RadarPublication)
                .filter(RadarPublication.is_latest == True)  # noqa: E712
                .first()
            )

            if pub is None:
                return jsonify({
                    "documentTitle": "Organization Tech Radar",
                    "quadrants": [
                        {"name": "Infrastructure"},
                        {"name": "Platforms"},
                        {"name": "Tools"},
                        {"name": "Languages & Frameworks"},
                    ],
                    "rings": [
                        {"name": "Adopt",  "color": "#00AA00"},
                        {"name": "Trial",  "color": "#00FFFF"},
                        {"name": "Assess", "color": "#FFFF00"},
                        {"name": "Hold",   "color": "#FF0000"},
                    ],
                    "entries": [],
                }), 200

            blips = (
                session.query(RadarBlipModel)
                .filter(RadarBlipModel.publication_id == pub.id)
                .all()
            )

            entries = [
                {
                    "id": b.id,
                    "label": b.label or b.package_name,
                    "description": b.description or "",
                    "quadrant": b.quadrant,
                    "ring": b.ring,
                    "isNew": b.is_new,
                    "isMoved": b.is_moved,
                }
                for b in blips
            ]

            return jsonify({
                "documentTitle": "Organization Tech Radar",
                "quadrants": [
                    {"name": "Infrastructure"},
                    {"name": "Platforms"},
                    {"name": "Tools"},
                    {"name": "Languages & Frameworks"},
                ],
                "rings": [
                    {"name": "Adopt",  "color": "#00AA00"},
                    {"name": "Trial",  "color": "#00FFFF"},
                    {"name": "Assess", "color": "#FFFF00"},
                    {"name": "Hold",   "color": "#FF0000"},
                ],
                "entries": entries,
                "publication": {
                    "id": pub.id,
                    "version": pub.publication_version,
                    "date": pub.publication_date.isoformat(),
                    "published_by": pub.published_by,
                },
            }), 200

    except Exception as e:
        logger.error("Failed to retrieve radar: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/api/radar/history", methods=["GET"])
def radar_history():
    """
    Return ring-movement timeline for one or all packages.

    Query Parameters:
        package_name (str): filter to a single package
        limit        (int): max number of records (default 100)

    Returns:
        JSON with a 'timeline' list sorted by publication_date descending.
    """
    try:
        package_name = request.args.get("package_name", "").strip() or None
        limit = min(int(request.args.get("limit", 100)), 1000)

        with get_session() as session:
            query = session.query(RadarBlipHistory).order_by(
                RadarBlipHistory.publication_date.desc()
            )
            if package_name:
                query = query.filter(RadarBlipHistory.package_name == package_name)

            rows = query.limit(limit).all()

            return jsonify({
                "timeline": [
                    {
                        "publication_date": str(r.publication_date),
                        "package_name": r.package_name,
                        "ecosystem": r.ecosystem,
                        "prior_ring": r.prior_ring,
                        "current_ring": r.current_ring,
                        "repo_count_delta": r.repo_count_delta,
                        "vulnerability_change": r.vulnerability_change,
                    }
                    for r in rows
                ]
            }), 200

    except Exception as e:
        logger.error("Failed to retrieve radar history: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/api/radar/export", methods=["GET"])
def export_radar():
    """
    Export a radar publication.

    Query Parameters:
        format (str): 'json' (default) or 'csv'
        date   (str): YYYY-MM-DD — return the publication closest to this date;
                      if not found, returns 404.

    Returns:
        A downloadable file attachment.
    """
    try:
        fmt = request.args.get("format", "json").lower()
        date_str = request.args.get("date", "").strip() or None

        with get_session() as session:
            if date_str:
                # Validate date
                try:
                    from datetime import datetime as _dt
                    target_date = _dt.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return jsonify({"status": "error", "message": f"Invalid date format: {date_str}"}), 404

                # Find closest publication on or before the given date
                pub = (
                    session.query(RadarPublication)
                    .filter(RadarPublication.publication_date <= f"{date_str} 23:59:59")
                    .order_by(RadarPublication.publication_date.desc())
                    .first()
                )
                if pub is None:
                    return jsonify({"status": "error", "message": f"No radar publication found for date {date_str}"}), 404
                filename_date = date_str
            else:
                pub = (
                    session.query(RadarPublication)
                    .filter(RadarPublication.is_latest == True)  # noqa: E712
                    .first()
                )
                if pub is None:
                    return jsonify({"status": "error", "message": "No radar publication available"}), 404
                filename_date = pub.publication_date.strftime("%Y-%m-%d")

            blips = (
                session.query(RadarBlipModel)
                .filter(RadarBlipModel.publication_id == pub.id)
                .all()
            )

            if fmt == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    "package_name", "ecosystem", "ring", "quadrant",
                    "label", "description", "repo_count",
                    "is_new", "is_moved", "is_eol", "exposed_to_cves",
                ])
                for b in blips:
                    writer.writerow([
                        b.package_name, b.ecosystem, b.ring, b.quadrant,
                        b.label or b.package_name, b.description or "",
                        b.repo_count, b.is_new, b.is_moved, b.is_eol, b.exposed_to_cves,
                    ])
                csv_data = output.getvalue()
                return Response(
                    csv_data,
                    mimetype="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=radar-{filename_date}.csv"
                    },
                )

            # Default: JSON in TW format
            entries = [
                {
                    "id": b.id,
                    "label": b.label or b.package_name,
                    "description": b.description or "",
                    "quadrant": b.quadrant,
                    "ring": b.ring,
                    "isNew": b.is_new,
                    "isMoved": b.is_moved,
                }
                for b in blips
            ]
            payload = jsonify({
                "documentTitle": "Organization Tech Radar",
                "quadrants": [
                    {"name": "Infrastructure"},
                    {"name": "Platforms"},
                    {"name": "Tools"},
                    {"name": "Languages & Frameworks"},
                ],
                "rings": [
                    {"name": "Adopt",  "color": "#00AA00"},
                    {"name": "Trial",  "color": "#00FFFF"},
                    {"name": "Assess", "color": "#FFFF00"},
                    {"name": "Hold",   "color": "#FF0000"},
                ],
                "entries": entries,
            })
            payload.headers["Content-Disposition"] = (
                f"attachment; filename=radar-{filename_date}.json"
            )
            return payload, 200

    except Exception as e:
        logger.error("Failed to export radar: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/api/packages/health", methods=["GET"])
def packages_health():
    """
    Portfolio health summary for all packages.

    Optional filters:
      ?team=<name>      — restrict to repos belonging to this team
      ?service=<name>   — restrict to repos linked to this service
      ?severity=<level> — only include packages at this severity or above

    Returns one key per health_status bucket:
      healthy, high_exposed, critical_exposed, eol, approaching_eol
    """
    team = request.args.get("team", "").strip()
    service = request.args.get("service", "").strip()
    severity_filter = request.args.get("severity", "").strip().upper()

    _severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    try:
        with get_session() as session:
            from sqlalchemy import text as _text

            base_sql = """
                SELECT
                    h.package_name,
                    h.ecosystem,
                    h.health_status,
                    h.repo_count,
                    h.exposed_cve_count,
                    h.eol_date
                FROM v_package_health_latest h
            """
            filters = []
            params: dict = {}

            if team or service:
                base_sql += """
                    JOIN (
                        SELECT DISTINCT p2.package_name, p2.ecosystem
                        FROM packages p2
                        JOIN repository_dependencies rd2
                            ON p2.package_name = rd2.package_name AND p2.ecosystem = rd2.ecosystem
                        JOIN repositories r2 ON rd2.repo_id = r2.repo_id
                """
                if team:
                    base_sql += " JOIN teams t2 ON t2.team_id = r2.team_id"
                    filters.append("t2.name = :team")
                    params["team"] = team
                if service:
                    base_sql += (
                        " JOIN repository_services rs2 ON rs2.repo_id = r2.repo_id"
                        " JOIN services svc2 ON svc2.service_id = rs2.service_id"
                    )
                    filters.append("svc2.name = :service")
                    params["service"] = service
                if filters:
                    base_sql += " WHERE " + " AND ".join(filters)
                base_sql += ") AS pkg_filter USING (package_name, ecosystem)"

            if severity_filter and severity_filter in _severity_rank:
                allowed = [s for s, r in _severity_rank.items() if r >= _severity_rank[severity_filter]]
                base_sql += (
                    " WHERE EXISTS ("
                    "  SELECT 1 FROM v_package_vulnerabilities_detail pvd"
                    "  WHERE pvd.package_name = h.package_name"
                    "    AND pvd.ecosystem = h.ecosystem"
                    "    AND pvd.severity = ANY(:allowed_severities)"
                    " )"
                )
                params["allowed_severities"] = allowed

            rows = session.execute(_text(base_sql), params).fetchall()

            buckets: dict = {
                "healthy": {"count": 0, "packages": []},
                "high_exposed": {"count": 0, "packages": []},
                "critical_exposed": {"count": 0, "packages": []},
                "eol": {"count": 0, "packages": []},
                "approaching_eol": {"count": 0, "packages": []},
            }
            _status_map = {
                "HEALTHY": "healthy",
                "HIGH_EXPOSED": "high_exposed",
                "CRITICAL_EXPOSED": "critical_exposed",
                "EOL": "eol",
                "APPROACHING_EOL": "approaching_eol",
            }
            for row in rows:
                bucket_key = _status_map.get(row.health_status, "healthy")
                entry = {
                    "package_name": row.package_name,
                    "ecosystem": row.ecosystem,
                    "repo_count": row.repo_count,
                    "exposed_cve_count": row.exposed_cve_count,
                    "eol_date": row.eol_date.isoformat() if row.eol_date else None,
                }
                buckets[bucket_key]["count"] += 1
                buckets[bucket_key]["packages"].append(entry)

            return jsonify(buckets), 200
    except Exception as e:
        logger.error("Package health error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/adoption", methods=["GET"])
def package_adoption():
    """
    Adoption timeline for a package or top-N packages.

    Query params:
      ?name=<name>        — package_name (exact); if omitted, returns top-N
      ?ecosystem=<eco>    — optional ecosystem filter (used with name)
      ?top=<n>            — top N packages by current repo_count (default 10)
      ?days=<n>           — limit timeline to last N days (default 90, max 365)
    """
    name = request.args.get("name", "").strip()
    ecosystem = request.args.get("ecosystem", "").strip()
    try:
        top_n = int(request.args.get("top", 10))
    except ValueError:
        top_n = 10
    try:
        days = min(int(request.args.get("days", 90)), 365)
    except ValueError:
        days = 90

    try:
        with get_session() as session:
            from sqlalchemy import text as _text

            if name:
                sql = """
                    SELECT package_name, ecosystem, adoption_date, repo_count
                    FROM v_package_adoption_timeline
                    WHERE package_name = :name
                      AND adoption_date >= CURRENT_DATE - CAST(:days AS INT)
                """
                params: dict = {"name": name, "days": days}
                if ecosystem:
                    sql += " AND ecosystem = :ecosystem"
                    params["ecosystem"] = ecosystem
                sql += " ORDER BY adoption_date"
                rows = session.execute(_text(sql), params).fetchall()
            else:
                # Top-N packages by most recent repo_count
                sql = """
                    SELECT t.package_name, t.ecosystem, t.adoption_date, t.repo_count
                    FROM v_package_adoption_timeline t
                    JOIN (
                        SELECT package_name, ecosystem
                        FROM v_package_portfolio_latest
                        ORDER BY repo_count DESC
                        LIMIT :top_n
                    ) top_pkgs USING (package_name, ecosystem)
                    WHERE t.adoption_date >= CURRENT_DATE - CAST(:days AS INT)
                    ORDER BY t.package_name, t.ecosystem, t.adoption_date
                """
                rows = session.execute(_text(sql), {"top_n": top_n, "days": days}).fetchall()

            timeline = [
                {
                    "package_name": row.package_name,
                    "ecosystem": row.ecosystem,
                    "adoption_date": row.adoption_date.isoformat() if row.adoption_date else None,
                    "repo_count": row.repo_count,
                }
                for row in rows
            ]
            return jsonify(timeline), 200
    except Exception as e:
        logger.error("Package adoption error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/packages/library/<name>/<ecosystem>", methods=["GET"])
def library_detail(name: str, ecosystem: str):
    """
    Detailed information for a single library.

    Returns:
      - metadata:  package_name, ecosystem, latest_version, is_eol, eol_date
      - cves:      list of CVEs with severity / fixed_in_version / exposed_repo_count
      - usage:     list of {repo_id, team_name, version, has_known_vulnerabilities}
      - by_team:   list of {team_name, repo_count, exposed_repos, versions_in_use}
    """
    try:
        with get_session() as session:
            from sqlalchemy import text as _text

            pkg = (
                session.query(Package)
                .filter_by(package_name=name, ecosystem=ecosystem)
                .first()
            )
            if not pkg:
                return jsonify({"status": "error", "message": "Package not found"}), 404

            cve_rows = session.execute(
                _text(
                    """
                    SELECT cve_id, severity, summary, fixed_in_version,
                           published_date, exposed_repo_count
                    FROM v_package_vulnerabilities_detail
                    WHERE package_name = :name AND ecosystem = :eco
                    ORDER BY severity DESC, cve_id
                    """
                ),
                {"name": name, "eco": ecosystem},
            ).fetchall()

            usage_rows = session.execute(
                _text(
                    """
                    SELECT rd.repo_id, COALESCE(t.name, 'Unknown') AS team_name,
                           rd.version, rd.has_known_vulnerabilities
                    FROM repository_dependencies rd
                    JOIN repositories r ON r.repo_id = rd.repo_id
                    LEFT JOIN teams t ON t.team_id = r.team_id
                    WHERE rd.package_name = :name AND rd.ecosystem = :eco
                    ORDER BY rd.has_known_vulnerabilities DESC, rd.repo_id
                    """
                ),
                {"name": name, "eco": ecosystem},
            ).fetchall()

            team_rows = session.execute(
                _text(
                    """
                    SELECT team_name, repo_count, exposed_repos, versions_in_use
                    FROM v_package_by_team_latest
                    WHERE package_name = :name AND ecosystem = :eco
                    ORDER BY repo_count DESC
                    """
                ),
                {"name": name, "eco": ecosystem},
            ).fetchall()

            return jsonify(
                {
                    "metadata": {
                        "package_name": pkg.package_name,
                        "ecosystem": pkg.ecosystem,
                        "latest_version": pkg.latest_version,
                        "is_eol": pkg.is_eol,
                        "eol_date": pkg.eol_date.isoformat() if pkg.eol_date else None,
                    },
                    "cves": [
                        {
                            "cve_id": r.cve_id,
                            "severity": r.severity,
                            "summary": r.summary,
                            "fixed_in_version": r.fixed_in_version,
                            "published_date": r.published_date.isoformat() if r.published_date else None,
                            "exposed_repo_count": r.exposed_repo_count,
                        }
                        for r in cve_rows
                    ],
                    "usage": [
                        {
                            "repo_id": r.repo_id,
                            "team_name": r.team_name,
                            "version": r.version,
                            "has_known_vulnerabilities": r.has_known_vulnerabilities,
                        }
                        for r in usage_rows
                    ],
                    "by_team": [
                        {
                            "team_name": r.team_name,
                            "repo_count": r.repo_count,
                            "exposed_repos": r.exposed_repos,
                            "versions_in_use": r.versions_in_use,
                        }
                        for r in team_rows
                    ],
                }
            ), 200
    except Exception as e:
        logger.error("Library detail error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    """Handle 405 errors."""
    return jsonify({
        "status": "error",
        "message": "Method not allowed. Rescan endpoints accept GET or POST.",
    }), 405


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    app.run(host="0.0.0.0", port=5000, debug=False)
