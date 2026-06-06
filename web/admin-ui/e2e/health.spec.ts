import { test, expect } from '@playwright/test'
import { FLOWER_BASE, GRAFANA_BASE } from '../src/config'

const GRAFANA_ADMIN = `${GRAFANA_BASE}/d/admin-dashboard`

// Backend contract shape: { status: string, service: string }
// Matches src/api/rescan.py health_check() — both healthy (200) and degraded (503).
const HEALTHY_RESPONSE = { status: 'healthy', service: 'extraction-api' }
const DEGRADED_RESPONSE = { status: 'degraded', service: 'extraction-api' }

test.describe('System Health page — success', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the /health API fetch. We navigate via the nav link to stay on the
    // SPA (React Router) so the Vite proxy doesn't intercept the page load.
    await page.route('**/health', async (route) => {
      if (['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(HEALTHY_RESPONSE),
        })
      } else {
        await route.continue()
      }
    })
    await page.goto('/')
    await page.getByRole('link', { name: 'System Health' }).click()
  })

  test('renders key/value pairs from the health response', async ({ page }) => {
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'status' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'healthy' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'service' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'extraction-api' })).toBeVisible()
  })

  test('"Open Flower" link has the correct href and opens in a new tab', async ({ page }) => {
    const link = page.getByRole('link', { name: 'Open Flower ↗' })
    await expect(link).toBeVisible()
    await expect(link).toHaveAttribute('href', FLOWER_BASE)
    await expect(link).toHaveAttribute('target', '_blank')
  })

  test('"Grafana Admin Dashboard" link has the correct href and opens in a new tab', async ({ page }) => {
    const link = page.getByRole('link', { name: 'Grafana Admin Dashboard ↗' })
    await expect(link).toBeVisible()
    await expect(link).toHaveAttribute('href', GRAFANA_ADMIN)
    await expect(link).toHaveAttribute('target', '_blank')
  })
})

test.describe('System Health page — degraded (503 with JSON)', () => {
  // Regression guard: the UI must render the degraded status gracefully when
  // the backend returns 503 + JSON payload (e.g. Celery unreachable).
  // getHealth() in client.ts treats a 503 with a JSON body as valid data so
  // the table is populated rather than showing an opaque error banner.
  test.beforeEach(async ({ page }) => {
    await page.route('**/health', async (route) => {
      if (['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify(DEGRADED_RESPONSE),
        })
      } else {
        await route.continue()
      }
    })
    await page.goto('/')
    await page.getByRole('link', { name: 'System Health' }).click()
  })

  test('displays degraded status in the table without crashing', async ({ page }) => {
    // Page must not show an unhandled error — the table should render the
    // degraded payload just as it renders the healthy payload.
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'status' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'degraded' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'service' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'extraction-api' })).toBeVisible()
    // No raw crash / error banner
    await expect(page.getByText(/Failed to load health data/)).not.toBeVisible()
  })
})

test.describe('System Health page — error', () => {
  test('shows error message when health endpoint fails with non-JSON body', async ({ page }) => {
    // Fresh page — no cached success data — route error immediately
    await page.route('**/health', async (route) => {
      if (['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.fulfill({ status: 503, contentType: 'text/plain', body: 'Service temporarily unavailable' })
      } else {
        await route.continue()
      }
    })
    await page.goto('/')
    await page.getByRole('link', { name: 'System Health' }).click()
    // TanStack Query retries on error; allow up to 15 s for retries to exhaust
    await expect(page.getByText(/Failed to load health data/)).toBeVisible({ timeout: 15_000 })
  })
})

