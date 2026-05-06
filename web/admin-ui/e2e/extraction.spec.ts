import { test, expect } from '@playwright/test'

test.describe('Extraction Control page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/extraction')
  })

  test('renders both rescan buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Trigger GitHub Rescan' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Trigger Azure DevOps Rescan' })).toBeVisible()
  })

  test('GitHub Rescan — success: shows toast with task_id and button re-enables', async ({ page }) => {
    await page.route('/api/rescan/github', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ task_id: 'gh-e2e-001' }) })
    })

    const button = page.getByRole('button', { name: 'Trigger GitHub Rescan' })
    await button.click()

    // Toast appears with task_id
    await expect(page.getByRole('status')).toContainText('gh-e2e-001')

    // Button is re-enabled after request completes
    await expect(button).toBeEnabled()
  })

  test('GitHub Rescan — error: shows error toast with HTTP status', async ({ page }) => {
    await page.route('/api/rescan/github', async (route) => {
      await route.fulfill({ status: 500, contentType: 'text/plain', body: 'Worker queue full' })
    })

    await page.getByRole('button', { name: 'Trigger GitHub Rescan' }).click()

    await expect(page.getByRole('alert')).toContainText('500')
    await expect(page.getByRole('alert')).toContainText('Worker queue full')
  })

  test('Azure DevOps Rescan — success: shows toast with task_id and button re-enables', async ({ page }) => {
    await page.route('/api/rescan/azure-devops', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ task_id: 'az-e2e-002' }) })
    })

    const button = page.getByRole('button', { name: 'Trigger Azure DevOps Rescan' })
    await button.click()

    await expect(page.getByRole('status')).toContainText('az-e2e-002')
    await expect(button).toBeEnabled()
  })

  test('Azure DevOps Rescan — error: shows error toast with HTTP status', async ({ page }) => {
    await page.route('/api/rescan/azure-devops', async (route) => {
      await route.fulfill({ status: 503, contentType: 'text/plain', body: 'Service unavailable' })
    })

    await page.getByRole('button', { name: 'Trigger Azure DevOps Rescan' }).click()

    await expect(page.getByRole('alert')).toContainText('503')
    await expect(page.getByRole('alert')).toContainText('Service unavailable')
  })
})
