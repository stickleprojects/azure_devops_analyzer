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

import logging
from flask import Flask, jsonify, request
from src.scheduler.celery_app import celery_app
from src.database import get_session
from src.database.models.repository import Repository
from src.database.models.package import Package
from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.service import RepositoryService, Service

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
