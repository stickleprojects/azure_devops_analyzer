export interface RescanResponse {
  task_id: string
}

export type HealthResponse = Record<string, unknown>

export interface ComputeMetricsResponse {
  status: string
  task_id: string
  message: string
}

export interface Repository {
  repo_id: string
  name: string
  url: string | null
  last_analyzed_at: string | null
  is_active: boolean
}

export interface RepositoryListResponse {
  status: string
  total: number
  count: number
  limit: number
  offset: number
  repositories: Repository[]
}

export interface RescanRepositoryResponse {
  status: string
  repository: {
    repo_id: string
    name: string
    previous_analyzed_at: string | null
  }
  message: string
}
