import type {
  RescanResponse,
  HealthResponse,
  ComputeMetricsResponse,
  RepositoryListResponse,
  RescanRepositoryResponse,
  LibraryDetailResponse,
  AdoptionTimelineRow,
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
  const response = await fetch('/health')
  if (response.ok) {
    return response.json() as Promise<HealthResponse>
  }
  // The /health endpoint returns 503 with a valid JSON body when Celery is
  // degraded (status == "degraded").  Treat that as data, not a hard error,
  // so the UI can display the degraded status rather than an error banner.
  if (response.status === 503) {
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      return response.json() as Promise<HealthResponse>
    }
  }
  const body = await response.text()
  const detail = body.trim() || response.statusText
  throw new Error(`HTTP ${response.status}: ${detail}`)
}

export async function getLibraryDetail(
  name: string,
  ecosystem: string,
): Promise<LibraryDetailResponse> {
  return request<LibraryDetailResponse>(
    `/api/packages/library/${encodeURIComponent(name)}/${encodeURIComponent(ecosystem)}`,
  )
}

export async function getPackageAdoption(
  name: string,
  ecosystem: string,
  days = 90,
): Promise<AdoptionTimelineRow[]> {
  const qs = new URLSearchParams({ name, ecosystem, days: String(days) })
  return request<AdoptionTimelineRow[]>(`/api/packages/adoption?${qs}`)
}
