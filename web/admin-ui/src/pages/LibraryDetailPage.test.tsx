import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LibraryDetailPage from './LibraryDetailPage'
import type { LibraryDetailResponse, AdoptionTimelineRow } from '../api/types'

vi.mock('../api/client', () => ({
  getLibraryDetail: vi.fn(),
  getPackageAdoption: vi.fn(),
}))

import { getLibraryDetail, getPackageAdoption } from '../api/client'

const fakeDetail: LibraryDetailResponse = {
  metadata: {
    package_name: 'requests',
    ecosystem: 'pip',
    latest_version: '2.31.0',
    is_eol: false,
    eol_date: null,
  },
  cves: [
    {
      cve_id: 'CVE-2023-1234',
      severity: 'HIGH',
      summary: 'Remote code execution via malformed URL',
      fixed_in_version: '2.31.0',
      published_date: '2023-06-01',
      exposed_repo_count: 3,
    },
  ],
  usage: [
    {
      repo_id: 'org/alpha-service',
      team_name: 'Team Alpha',
      version: '2.28.0',
      has_known_vulnerabilities: true,
    },
    {
      repo_id: 'org/beta-service',
      team_name: 'Team Beta',
      version: '2.31.0',
      has_known_vulnerabilities: false,
    },
  ],
  by_team: [
    {
      team_name: 'Team Alpha',
      repo_count: 1,
      exposed_repos: 1,
      versions_in_use: '2.28.0',
    },
    {
      team_name: 'Team Beta',
      repo_count: 1,
      exposed_repos: 0,
      versions_in_use: '2.31.0',
    },
  ],
}

const fakeAdoption: AdoptionTimelineRow[] = [
  { package_name: 'requests', ecosystem: 'pip', adoption_date: '2024-01-01', repo_count: 1 },
  { package_name: 'requests', ecosystem: 'pip', adoption_date: '2024-02-01', repo_count: 2 },
]

function renderPage(ecosystem = 'pip', name = 'requests') {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/library/${ecosystem}/${name}`]}>
        <Routes>
          <Route path="/library/:ecosystem/:name" element={<LibraryDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(getLibraryDetail).mockReset()
  vi.mocked(getPackageAdoption).mockReset()
})

describe('LibraryDetailPage', () => {
  it('shows loading state initially', () => {
    vi.mocked(getLibraryDetail).mockReturnValue(new Promise(() => {}))
    vi.mocked(getPackageAdoption).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('renders package name and ecosystem in the heading', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => expect(screen.getByText('requests')).toBeInTheDocument())
    expect(screen.getByText('pip')).toBeInTheDocument()
  })

  it('shows metadata table with latest version and EOL status', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => {
      const matches = screen.getAllByText('2.31.0')
      expect(matches.length).toBeGreaterThan(0)
    })
    // EOL = false → "No" text present somewhere
    const noMatches = screen.getAllByText('No')
    expect(noMatches.length).toBeGreaterThan(0)
  })

  it('renders CVE table with severity badge', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => expect(screen.getByText('CVE-2023-1234')).toBeInTheDocument())
    expect(screen.getByText('HIGH')).toBeInTheDocument()
    expect(screen.getByText('Remote code execution via malformed URL')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows "No known CVEs" when cves list is empty', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce({ ...fakeDetail, cves: [] })
    vi.mocked(getPackageAdoption).mockResolvedValueOnce([])
    renderPage()
    await waitFor(() => expect(screen.getByText('No known CVEs.')).toBeInTheDocument())
  })

  it('renders adoption timeline rows', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => expect(screen.getByText('2024-01-01')).toBeInTheDocument())
    expect(screen.getByText('2024-02-01')).toBeInTheDocument()
  })

  it('shows "No adoption data available" when timeline is empty', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce([])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText('No adoption data available.')).toBeInTheDocument(),
    )
  })

  it('renders per-repo usage table', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => expect(screen.getByText('org/alpha-service')).toBeInTheDocument())
    // 2.28.0 appears in usage table; use getAllByText as it may also appear in by_team
    const versionMatches = screen.getAllByText('2.28.0')
    expect(versionMatches.length).toBeGreaterThan(0)
    const alphaMatches = screen.getAllByText('Team Alpha')
    expect(alphaMatches.length).toBeGreaterThan(0)
  })

  it('renders by-team summary table', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    await waitFor(() => {
      const cells = screen.getAllByText('Team Alpha')
      expect(cells.length).toBeGreaterThan(0)
    })
    const betaCells = screen.getAllByText('Team Beta')
    expect(betaCells.length).toBeGreaterThan(0)
  })

  it('shows error message when detail query fails', async () => {
    vi.mocked(getLibraryDetail).mockRejectedValueOnce(new Error('Package not found'))
    vi.mocked(getPackageAdoption).mockResolvedValueOnce([])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Failed to load library detail/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/Package not found/)).toBeInTheDocument()
  })

  it('CVE link points to NVD', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage()
    const link = await screen.findByRole('link', { name: 'CVE-2023-1234' })
    expect(link).toHaveAttribute(
      'href',
      'https://nvd.nist.gov/vuln/detail/CVE-2023-1234',
    )
  })

  it('calls getLibraryDetail with correct name and ecosystem', async () => {
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(fakeDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce(fakeAdoption)
    renderPage('npm', 'lodash')
    await waitFor(() => expect(getLibraryDetail).toHaveBeenCalledWith('lodash', 'npm'))
    expect(getPackageAdoption).toHaveBeenCalledWith('lodash', 'npm', 90)
  })

  it('shows EOL warning when is_eol is true', async () => {
    const eolDetail: LibraryDetailResponse = {
      ...fakeDetail,
      metadata: { ...fakeDetail.metadata, is_eol: true, eol_date: '2023-01-01' },
    }
    vi.mocked(getLibraryDetail).mockResolvedValueOnce(eolDetail)
    vi.mocked(getPackageAdoption).mockResolvedValueOnce([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/Yes.*2023-01-01/)).toBeInTheDocument())
  })
})
