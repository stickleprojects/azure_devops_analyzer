/**
 * Service base URLs.
 *
 * All service endpoints are defined here so that moving away from localhost
 * (containerised dev, staging, production) is a single-file change.
 *
 * In development the Vite proxy (vite.config.ts) forwards /api and /health
 * to the Flask extraction-api, so API_BASE stays empty (relative paths).
 * In the nginx-served Docker image, nginx proxies those same paths.
 */

/** Grafana analytics dashboards */
export const GRAFANA_BASE = 'http://localhost:3000'

/** Celery Flower task monitor */
export const FLOWER_BASE = 'http://localhost:5555'

/** Flask extraction-API (empty = relative path resolved by nginx / Vite proxy) */
export const API_BASE = ''

/** All Grafana dashboards exposed as tiles on the Home page */
export const GRAFANA_DASHBOARDS = [
  { title: 'Home', uid: 'dashboard-home' },
  { title: 'Repositories', uid: 'repo-overview' },
  { title: 'Security', uid: 'security-dashboard' },
  { title: 'Technology', uid: 'technology-landscape' },
  { title: 'Admin', uid: 'admin-dashboard' },
  { title: 'Library Deep Dive', uid: 'library-detail-deep-dive' },
  { title: 'Repository Deep Dive', uid: 'repo-deep-dive' },
  { title: 'Dependency Vulnerabilities', uid: 'dep-vuln-portfolio' },
  { title: 'Pull Requests', uid: 'pull-requests' },
  { title: 'Teams', uid: 'team-overview' },
  { title: 'Services', uid: 'service-overview' },
  { title: 'Contributors', uid: 'contributor-analytics' },
  { title: 'Extraction Health', uid: 'extraction-health' },
] as const
