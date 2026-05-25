import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExtractionPage from './ExtractionPage'

vi.mock('../api/client', () => ({
  triggerGithubRescan: vi.fn(),
  triggerAzureDevOpsRescan: vi.fn(),
  triggerComputeServiceMetrics: vi.fn(),
}))

import { triggerGithubRescan, triggerAzureDevOpsRescan, triggerComputeServiceMetrics } from '../api/client'

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
  vi.mocked(triggerComputeServiceMetrics).mockReset()
})

describe('ExtractionPage', () => {
  it('renders all three buttons', () => {
    renderPage()
    expect(screen.getByText('Trigger GitHub Rescan')).toBeInTheDocument()
    expect(screen.getByText('Trigger Azure DevOps Rescan')).toBeInTheDocument()
    expect(screen.getByText('Compute Service Metrics')).toBeInTheDocument()
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
      expect(screen.getByRole('alert')).toHaveTextContent('connection refused'),
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

  it('calls triggerComputeServiceMetrics when the Compute button is clicked', async () => {
    vi.mocked(triggerComputeServiceMetrics).mockResolvedValueOnce({
      status: 'submitted',
      task_id: 'cmp-003',
      message: 'queued',
    })
    renderPage()
    await userEvent.click(screen.getByText('Compute Service Metrics'))
    expect(triggerComputeServiceMetrics).toHaveBeenCalledOnce()
  })

  it('shows success toast with task_id after computing service metrics', async () => {
    vi.mocked(triggerComputeServiceMetrics).mockResolvedValueOnce({
      status: 'submitted',
      task_id: 'cmp-003',
      message: 'queued',
    })
    renderPage()
    await userEvent.click(screen.getByText('Compute Service Metrics'))
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('cmp-003'),
    )
  })

  it('shows error toast when compute service metrics fails', async () => {
    vi.mocked(triggerComputeServiceMetrics).mockRejectedValueOnce(new Error('worker down'))
    renderPage()
    await userEvent.click(screen.getByText('Compute Service Metrics'))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('worker down'),
    )
  })
})
