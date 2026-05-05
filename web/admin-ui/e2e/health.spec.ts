import { test, expect } from '@playwright/test'
import { FLOWER_BASE, GRAFANA_BASE } from '../src/config'

const GRAFANA_ADMIN = `${GRAFANA_BASE}/d/admin-dashboard`

test.describe('System Health page — success', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the /health API fetch. We navigate via the nav link to stay on the
    // SPA (React Router) so the Vite proxy doesn't intercept the page load.
    await page.route('**/health', async (route) => {
      if (['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', db: 'connected', celery: 'running', version: '2.1.0' }),
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
    await expect(page.getByRole('cell', { name: 'ok' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'db' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'connected' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'celery' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'running' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'version' })).toBeVisible()
    await expect(page.getByRole('cell', { name: '2.1.0' })).toBeVisible()
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

test.describe('System Health page — error', () => {
  test('shows error message when health endpoint fails', async ({ page }) => {
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

