import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExtractionPage from './ExtractionPage'

vi.mock('../api/client', () => ({
  triggerGithubRescan: vi.fn(),
  triggerAzureDevOpsRescan: vi.fn(),
}))

import { triggerGithubRescan, triggerAzureDevOpsRescan } from '../api/client'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ExtractionPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(triggerGithubRescan).mockReset()
  vi.mocked(triggerAzureDevOpsRescan).mockReset()
})

describe('ExtractionPage', () => {
  it('renders both buttons', () => {
    renderPage()
    expect(screen.getByText('Trigger GitHub Rescan')).toBeInTheDocument()
    expect(screen.getByText('Trigger Azure DevOps Rescan')).toBeInTheDocument()
  })

  it('calls triggerGithubRescan when the GitHub button is clicked', async () => {
    vi.mocked(triggerGithubRescan).mockResolvedValueOnce({ task_id: 'gh-001' })
    renderPage()
    await userEvent.click(screen.getByText('Trigger GitHub Rescan'))
    expect(triggerGithubRescan).toHaveBeenCalledOnce()
  })

  it('shows success toast with task_id after GitHub rescan', async () => {
    vi.mocked(triggerGithubRescan).mockResolvedValueOnce({ task_id: 'gh-001' })
    renderPage()
    await userEvent.click(screen.getByText('Trigger GitHub Rescan'))
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('gh-001'),
    )
  })

  it('shows error toast when GitHub rescan fails', async () => {
    vi.mocked(triggerGithubRescan).mockRejectedValueOnce(new Error('connection refused'))
    renderPage()
    await userEvent.click(screen.getByText('Trigger GitHub Rescan'))
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('connection refused'),
    )
  })

  it('calls triggerAzureDevOpsRescan when the Azure button is clicked', async () => {
    vi.mocked(triggerAzureDevOpsRescan).mockResolvedValueOnce({ task_id: 'az-002' })
    renderPage()
    await userEvent.click(screen.getByText('Trigger Azure DevOps Rescan'))
    expect(triggerAzureDevOpsRescan).toHaveBeenCalledOnce()
  })

  it('shows success toast with task_id after Azure rescan', async () => {
    vi.mocked(triggerAzureDevOpsRescan).mockResolvedValueOnce({ task_id: 'az-002' })
    renderPage()
    await userEvent.click(screen.getByText('Trigger Azure DevOps Rescan'))
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('az-002'),
    )
  })
})
