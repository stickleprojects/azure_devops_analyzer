import type { RescanResponse, HealthResponse } from './types'

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

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}
