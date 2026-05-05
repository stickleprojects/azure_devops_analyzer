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
