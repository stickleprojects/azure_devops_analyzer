import { expect, test } from '@playwright/test'

test.describe('Tech Radar page', () => {
  test('renders visual radar when entries are returned', async ({ page }) => {
    await page.route('**/api/radar', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documentTitle: 'Organization Tech Radar',
          quadrants: [
            { name: 'Infrastructure' },
            { name: 'Platforms' },
            { name: 'Tools' },
            { name: 'Languages & Frameworks' },
          ],
          rings: [
            { name: 'Adopt', color: '#00AA00' },
            { name: 'Trial', color: '#00FFFF' },
            { name: 'Assess', color: '#FFFF00' },
            { name: 'Hold', color: '#FF0000' },
          ],
          entries: [
            {
              id: 1,
              label: 'react',
              description: 'UI',
              quadrant: 'Languages & Frameworks',
              ring: 'Trial',
              isNew: false,
              isMoved: true,
            },
          ],
          publication: { id: 1, version: '2026.05', date: '2026-05-25', published_by: 'bot' },
        }),
      })
    })

    await page.goto('/')
    await page.getByRole('link', { name: 'Tech Radar' }).click()

    await expect(page.getByRole('heading', { name: 'Tech Radar' })).toBeVisible()
    await expect(page.locator('svg#radar')).toBeVisible()
  })

  test('shows placeholder when no radar publication exists', async ({ page }) => {
    await page.route('**/api/radar', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documentTitle: 'Organization Tech Radar',
          quadrants: [
            { name: 'Infrastructure' },
            { name: 'Platforms' },
            { name: 'Tools' },
            { name: 'Languages & Frameworks' },
          ],
          rings: [
            { name: 'Adopt', color: '#00AA00' },
            { name: 'Trial', color: '#00FFFF' },
            { name: 'Assess', color: '#FFFF00' },
            { name: 'Hold', color: '#FF0000' },
          ],
          entries: [],
        }),
      })
    })

    await page.goto('/radar')

    await expect(page.getByText('No radar published yet.')).toBeVisible()
  })
})

test.describe('Tech Radar history page', () => {
  test('renders timeline table', async ({ page }) => {
    await page.route('**/api/radar/history', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          timeline: [
            {
              publication_date: '2026-05-25',
              package_name: 'react',
              ecosystem: 'npm',
              prior_ring: 'Assess',
              current_ring: 'Trial',
              repo_count_delta: 3,
              vulnerability_change: 0,
            },
          ],
        }),
      })
    })

    await page.goto('/radar/history')

    await expect(page.getByRole('heading', { name: 'Tech Radar History' })).toBeVisible()
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'react' })).toBeVisible()
  })
})
