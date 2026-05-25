import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import RadarPage from './RadarPage'
import type { RadarResponse } from '../api/radar'

vi.mock('../api/radar', () => ({
  getRadar: vi.fn(),
}))

vi.mock('../components/RadarChart', () => ({
  default: () => <svg aria-label="Technology radar chart" />,
}))

import { getRadar } from '../api/radar'

const baseResponse: RadarResponse = {
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
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <RadarPage />
    </QueryClientProvider>,
  )
}

describe('RadarPage', () => {
  it('renders placeholder when entries are empty', async () => {
    vi.mocked(getRadar).mockResolvedValueOnce(baseResponse)

    renderPage()

    expect(await screen.findByText('No radar published yet.')).toBeInTheDocument()
  })

  it('renders chart when entries are present', async () => {
    vi.mocked(getRadar).mockResolvedValueOnce({
      ...baseResponse,
      entries: [
        {
          id: 1,
          label: 'react',
          description: 'desc',
          quadrant: 'Languages & Frameworks',
          ring: 'Trial',
          isNew: false,
          isMoved: true,
        },
      ],
      publication: { id: 1, version: '2026.05', date: '2026-05-25', published_by: 'bot' },
    })

    renderPage()

    expect(await screen.findByLabelText('Technology radar chart')).toBeInTheDocument()
  })

  it('shows an error message when query fails', async () => {
    vi.mocked(getRadar).mockRejectedValueOnce(new Error('bad gateway'))

    renderPage()

    await waitFor(() => expect(screen.getByText(/Failed to load radar/)).toBeInTheDocument())
    expect(screen.getByText(/bad gateway/)).toBeInTheDocument()
  })
})
