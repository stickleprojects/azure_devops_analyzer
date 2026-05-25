import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import RadarHistoryPage from './RadarHistoryPage'

vi.mock('../api/radar', () => ({
  getRadarHistory: vi.fn(),
}))

import { getRadarHistory } from '../api/radar'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <RadarHistoryPage />
    </QueryClientProvider>,
  )
}

function packageNamesFromTable(): string[] {
  const table = screen.getByRole('table')
  const rows = within(table).getAllByRole('row').slice(1)
  return rows.map((row) => within(row).getAllByRole('cell')[1].textContent ?? '')
}

describe('RadarHistoryPage', () => {
  it('renders timeline rows', async () => {
    vi.mocked(getRadarHistory).mockResolvedValueOnce({
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
    })

    renderPage()

    expect(await screen.findByRole('cell', { name: 'react' })).toBeInTheDocument()
  })

  it('sorts by package name when sortable header is clicked', async () => {
    vi.mocked(getRadarHistory).mockResolvedValueOnce({
      timeline: [
        {
          publication_date: '2026-05-25',
          package_name: 'zod',
          ecosystem: 'npm',
          prior_ring: 'Assess',
          current_ring: 'Trial',
          repo_count_delta: 1,
          vulnerability_change: 0,
        },
        {
          publication_date: '2026-05-20',
          package_name: 'axios',
          ecosystem: 'npm',
          prior_ring: 'Hold',
          current_ring: 'Assess',
          repo_count_delta: 2,
          vulnerability_change: -1,
        },
      ],
    })

    renderPage()

    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: /package/i }))
    await waitFor(() => expect(packageNamesFromTable()).toEqual(['axios', 'zod']))

    await userEvent.click(screen.getByRole('button', { name: /package/i }))
    await waitFor(() => expect(packageNamesFromTable()).toEqual(['zod', 'axios']))
  })

  it('shows error message when query fails', async () => {
    vi.mocked(getRadarHistory).mockRejectedValueOnce(new Error('request failed'))

    renderPage()

    await waitFor(() =>
      expect(screen.getByText(/Failed to load radar history/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/request failed/)).toBeInTheDocument()
  })
})
