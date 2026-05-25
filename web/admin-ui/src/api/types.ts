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

export interface LibraryCve {
  cve_id: string
  severity: string
  summary: string | null
  fixed_in_version: string | null
  published_date: string | null
  exposed_repo_count: number
}

export interface LibraryUsageRow {
  repo_id: string
  team_name: string
  version: string | null
  has_known_vulnerabilities: boolean
}

export interface LibraryByTeam {
  team_name: string
  repo_count: number
  exposed_repos: number
  versions_in_use: string | null
}

export interface LibraryDetailResponse {
  metadata: {
    package_name: string
    ecosystem: string
    latest_version: string | null
    is_eol: boolean
    eol_date: string | null
  }
  cves: LibraryCve[]
  usage: LibraryUsageRow[]
  by_team: LibraryByTeam[]
}

export interface AdoptionTimelineRow {
  package_name: string
  ecosystem: string
  adoption_date: string
  repo_count: number
}
