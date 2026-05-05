import { test, expect } from '@playwright/test'

const GRAFANA_BASE = 'http://localhost:3000'

const dashboards = [
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
]

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
    for (const { title } of dashboards) {
      await expect(main.getByText(title, { exact: true }).first()).toBeVisible()
    }
  })

  test('each tile links to the correct Grafana URL and opens in a new tab', async ({ page }) => {
    const main = page.getByRole('main')
    for (const { title, uid } of dashboards) {
      const link = main.getByRole('link', { name: title }).first()
      await expect(link).toHaveAttribute('href', `${GRAFANA_BASE}/d/${uid}`)
      await expect(link).toHaveAttribute('target', '_blank')
    }
  })
})
