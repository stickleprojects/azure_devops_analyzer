import { test, expect } from '@playwright/test'
import { GRAFANA_BASE, GRAFANA_DASHBOARDS } from '../src/config'

test.describe('Home page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('renders the page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Grafana Dashboards' })).toBeVisible()
  })

  test('shows all 13 dashboard tiles', async ({ page }) => {
    // Scope to the main content area to avoid nav links with the same names
    const main = page.getByRole('main')
    for (const { title } of GRAFANA_DASHBOARDS) {
      await expect(main.getByText(title, { exact: true }).first()).toBeVisible()
    }
  })

  test('each tile links to the correct Grafana URL and opens in a new tab', async ({ page }) => {
    const main = page.getByRole('main')
    for (const { title, uid } of GRAFANA_DASHBOARDS) {
      const link = main.getByRole('link', { name: title }).first()
      await expect(link).toHaveAttribute('href', `${GRAFANA_BASE}/d/${uid}`)
      await expect(link).toHaveAttribute('target', '_blank')
    }
  })
})

