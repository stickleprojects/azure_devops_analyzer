import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HealthPage from './HealthPage'
import { FLOWER_BASE, GRAFANA_BASE } from '../config'

vi.mock('../api/client', () => ({
  getHealth: vi.fn(),
}))

import { getHealth } from '../api/client'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <HealthPage />
    </QueryClientProvider>,
  )
}

describe('HealthPage', () => {
  it('renders health key/value pairs from the API response', async () => {
    vi.mocked(getHealth).mockResolvedValueOnce({ status: 'ok', db: 'connected', version: '1.2.3' })
    renderPage()
    expect(await screen.findByText('status')).toBeInTheDocument()
    expect(screen.getByText('ok')).toBeInTheDocument()
    expect(screen.getByText('db')).toBeInTheDocument()
    expect(screen.getByText('connected')).toBeInTheDocument()
    expect(screen.getByText('version')).toBeInTheDocument()
    expect(screen.getByText('1.2.3')).toBeInTheDocument()
  })

  it('has the correct href on the Open Flower link', () => {
    vi.mocked(getHealth).mockResolvedValueOnce({})
    renderPage()
    const link = screen.getByText('Open Flower ↗')
    expect(link).toHaveAttribute('href', FLOWER_BASE)
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('has the correct href on the Grafana Admin Dashboard link', () => {
    vi.mocked(getHealth).mockResolvedValueOnce({})
    renderPage()
    const link = screen.getByText('Grafana Admin Dashboard ↗')
    expect(link).toHaveAttribute('href', `${GRAFANA_BASE}/d/admin-dashboard`)
    expect(link).toHaveAttribute('target', '_blank')
  })
})
