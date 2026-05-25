import type {
  RescanResponse,
  HealthResponse,
  ComputeMetricsResponse,
  RepositoryListResponse,
  RescanRepositoryResponse,
} from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    const body = await response.text()
    const detail = body.trim() || response.statusText
    throw new Error(`HTTP ${response.status}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export async function triggerGithubRescan(): Promise<RescanResponse> {
  return request<RescanResponse>('/api/rescan/github', { method: 'POST' })
}

export async function triggerAzureDevOpsRescan(): Promise<RescanResponse> {
  return request<RescanResponse>('/api/rescan/azure-devops', { method: 'POST' })
}

export async function triggerComputeServiceMetrics(): Promise<ComputeMetricsResponse> {
  return request<ComputeMetricsResponse>('/api/compute/service-metrics', { method: 'POST' })
}

export async function getRepositories(params?: {
  search?: string
  limit?: number
  offset?: number
}): Promise<RepositoryListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.search) searchParams.set('search', params.search)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<RepositoryListResponse>(qs ? `/api/repositories?${qs}` : '/api/repositories')
}

export async function rescanRepository(repoId: string): Promise<RescanRepositoryResponse> {
  return request<RescanRepositoryResponse>(
    `/api/rescan/repository/${encodeURIComponent(repoId)}`,
    { method: 'POST' },
  )
}

export async function removeRepository(repoId: string): Promise<RescanRepositoryResponse> {
  return request<RescanRepositoryResponse>(
    `/api/rescan/repository/${encodeURIComponent(repoId)}`,
    { method: 'DELETE' },
  )
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}
