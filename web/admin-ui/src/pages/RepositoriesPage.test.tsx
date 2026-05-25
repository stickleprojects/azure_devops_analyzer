import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RepositoriesPage from './RepositoriesPage'
import type { RepositoryListResponse } from '../api/types'

vi.mock('../api/client', () => ({
  getRepositories: vi.fn(),
  rescanRepository: vi.fn(),
  removeRepository: vi.fn(),
}))

import { getRepositories, rescanRepository, removeRepository } from '../api/client'

const fakeRepos: RepositoryListResponse = {
  status: 'success',
  total: 2,
  count: 2,
  limit: 100,
  offset: 0,
  repositories: [
    {
      repo_id: 'r1',
      name: 'alpha-service',
      url: 'https://github.com/org/alpha-service',
      last_analyzed_at: '2026-05-01T10:00:00',
      is_active: true,
    },
    {
      repo_id: 'r2',
      name: 'beta-service',
      url: null,
      last_analyzed_at: null,
      is_active: false,
    },
  ],
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={qc}>
      <RepositoriesPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(getRepositories).mockReset()
  vi.mocked(rescanRepository).mockReset()
  vi.mocked(removeRepository).mockReset()
})

describe('RepositoriesPage', () => {
  it('shows loading state initially', () => {
    vi.mocked(getRepositories).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading repositories…')).toBeInTheDocument()
  })

  it('renders a table with repository rows after load', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    renderPage()
    await waitFor(() => expect(screen.getByText('alpha-service')).toBeInTheDocument())
    expect(screen.getByText('beta-service')).toBeInTheDocument()
  })

  it('shows an error message when the query fails', async () => {
    vi.mocked(getRepositories).mockRejectedValueOnce(new Error('DB unavailable'))
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Failed to load repositories/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/DB unavailable/)).toBeInTheDocument()
  })

  it('shows "No repositories found" when list is empty', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce({
      ...fakeRepos,
      total: 0,
      count: 0,
      repositories: [],
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText('No repositories found.')).toBeInTheDocument(),
    )
  })

  it('calls getRepositories with search param when filter changes', async () => {
    vi.mocked(getRepositories).mockResolvedValue(fakeRepos)
    renderPage()
    await waitFor(() => expect(getRepositories).toHaveBeenCalledWith({ search: undefined }))

    const input = screen.getByRole('searchbox', { name: /filter repositories/i })
    await userEvent.type(input, 'alpha')
    await waitFor(() =>
      expect(getRepositories).toHaveBeenCalledWith({ search: 'alpha' }),
    )
  })

  it('calls rescanRepository with the correct repo_id when Rescan is clicked', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(rescanRepository).mockResolvedValueOnce({
      status: 'success',
      repository: { repo_id: 'r1', name: 'alpha-service', previous_analyzed_at: null },
      message: 'marked',
    })
    renderPage()
    const rescanButtons = await screen.findAllByText('Rescan')
    await userEvent.click(rescanButtons[0])
    expect(vi.mocked(rescanRepository).mock.calls[0][0]).toBe('r1')
  })

  it('shows success toast after Rescan', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(rescanRepository).mockResolvedValueOnce({
      status: 'success',
      repository: { repo_id: 'r1', name: 'alpha-service', previous_analyzed_at: null },
      message: 'marked',
    })
    renderPage()
    const rescanButtons = await screen.findAllByText('Rescan')
    await userEvent.click(rescanButtons[0])
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('alpha-service'),
    )
  })

  it('shows error toast when Rescan fails', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(rescanRepository).mockRejectedValueOnce(new Error('not found'))
    renderPage()
    const rescanButtons = await screen.findAllByText('Rescan')
    await userEvent.click(rescanButtons[0])
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('not found'),
    )
  })

  it('calls removeRepository with the correct repo_id when Remove is clicked', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(removeRepository).mockResolvedValueOnce({
      status: 'success',
      repository: { repo_id: 'r2', name: 'beta-service', previous_analyzed_at: null },
      message: 'removed',
    })
    renderPage()
    const removeButtons = await screen.findAllByText('Remove')
    await userEvent.click(removeButtons[1])
    expect(vi.mocked(removeRepository).mock.calls[0][0]).toBe('r2')
  })

  it('shows success toast after Remove', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(removeRepository).mockResolvedValueOnce({
      status: 'success',
      repository: { repo_id: 'r2', name: 'beta-service', previous_analyzed_at: null },
      message: 'removed',
    })
    renderPage()
    const removeButtons = await screen.findAllByText('Remove')
    await userEvent.click(removeButtons[1])
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('beta-service'),
    )
  })

  it('shows error toast when Remove fails', async () => {
    vi.mocked(getRepositories).mockResolvedValueOnce(fakeRepos)
    vi.mocked(removeRepository).mockRejectedValueOnce(new Error('server error'))
    renderPage()
    const removeButtons = await screen.findAllByText('Remove')
    await userEvent.click(removeButtons[0])
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('server error'),
    )
  })
})
