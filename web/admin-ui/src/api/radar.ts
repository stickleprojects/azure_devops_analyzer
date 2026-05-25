export interface RadarQuadrant {
  name: string
}

export interface RadarRing {
  name: string
  color: string
}

export interface RadarEntry {
  id: number
  label: string
  description: string
  quadrant: string
  ring: string
  isNew: boolean
  isMoved: boolean
}

export interface RadarPublication {
  id: number
  version: string
  date: string
  published_by: string
}

export interface RadarResponse {
  documentTitle: string
  quadrants: RadarQuadrant[]
  rings: RadarRing[]
  entries: RadarEntry[]
  publication?: RadarPublication
}

export interface RadarHistoryRow {
  publication_date: string
  package_name: string
  ecosystem: string
  prior_ring: string | null
  current_ring: string
  repo_count_delta: number
  vulnerability_change: number
}

export interface RadarHistoryResponse {
  timeline: RadarHistoryRow[]
}

async function request<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    const body = await response.text()
    const detail = body.trim() || response.statusText
    throw new Error(`HTTP ${response.status}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export async function getRadar(): Promise<RadarResponse> {
  return request<RadarResponse>('/api/radar')
}

export async function getRadarHistory(): Promise<RadarHistoryResponse> {
  return request<RadarHistoryResponse>('/api/radar/history')
}
