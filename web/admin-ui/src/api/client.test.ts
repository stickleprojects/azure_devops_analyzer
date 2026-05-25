import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  triggerGithubRescan,
  triggerAzureDevOpsRescan,
  getHealth,
  triggerComputeServiceMetrics,
  getRepositories,
  rescanRepository,
  removeRepository,
} from './client'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
})

function mockOk(body: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(body),
  })
}

function mockError(status: number, bodyText: string, statusText = '') {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText,
    text: () => Promise.resolve(bodyText),
  })
}

describe('triggerGithubRescan', () => {
  it('POSTs to /api/rescan/github and returns the parsed response', async () => {
    mockOk({ task_id: 'abc-123' })
    const result = await triggerGithubRescan()
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/github', { method: 'POST' })
    expect(result).toEqual({ task_id: 'abc-123' })
  })

  it('throws an Error with the response body on non-2xx', async () => {
    mockError(500, 'Internal Server Error')
    await expect(triggerGithubRescan()).rejects.toThrow('HTTP 500: Internal Server Error')
  })
})

describe('triggerAzureDevOpsRescan', () => {
  it('POSTs to /api/rescan/azure-devops and returns the parsed response', async () => {
    mockOk({ task_id: 'xyz-789' })
    const result = await triggerAzureDevOpsRescan()
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/azure-devops', { method: 'POST' })
    expect(result).toEqual({ task_id: 'xyz-789' })
  })

  it('throws an Error with the response body on non-2xx', async () => {
    mockError(400, 'Bad Request')
    await expect(triggerAzureDevOpsRescan()).rejects.toThrow('HTTP 400: Bad Request')
  })
})

describe('getHealth', () => {
  it('GETs /health and returns the parsed response', async () => {
    mockOk({ status: 'ok', db: 'connected' })
    const result = await getHealth()
    expect(mockFetch).toHaveBeenCalledWith('/health', undefined)
    expect(result).toEqual({ status: 'ok', db: 'connected' })
  })

  it('throws an Error with the response body on non-2xx', async () => {
    mockError(503, 'Service Unavailable')
    await expect(getHealth()).rejects.toThrow('HTTP 503: Service Unavailable')
  })

  it('falls back to statusText when body is empty', async () => {
    mockError(502, '', 'Bad Gateway')
    await expect(getHealth()).rejects.toThrow('HTTP 502: Bad Gateway')
  })
})

describe('triggerComputeServiceMetrics', () => {
  it('POSTs to /api/compute/service-metrics and returns the parsed response', async () => {
    mockOk({ status: 'submitted', task_id: 'cmp-001', message: 'queued' })
    const result = await triggerComputeServiceMetrics()
    expect(mockFetch).toHaveBeenCalledWith('/api/compute/service-metrics', { method: 'POST' })
    expect(result).toEqual({ status: 'submitted', task_id: 'cmp-001', message: 'queued' })
  })

  it('throws on non-2xx response', async () => {
    mockError(500, 'Worker unavailable')
    await expect(triggerComputeServiceMetrics()).rejects.toThrow('HTTP 500: Worker unavailable')
  })
})

describe('getRepositories', () => {
  it('GETs /api/repositories with no params', async () => {
    mockOk({ status: 'success', total: 0, count: 0, limit: 100, offset: 0, repositories: [] })
    await getRepositories()
    expect(mockFetch).toHaveBeenCalledWith('/api/repositories', undefined)
  })

  it('appends search param when provided', async () => {
    mockOk({ status: 'success', total: 1, count: 1, limit: 100, offset: 0, repositories: [] })
    await getRepositories({ search: 'my-repo' })
    expect(mockFetch).toHaveBeenCalledWith('/api/repositories?search=my-repo', undefined)
  })

  it('appends limit and offset params when provided', async () => {
    mockOk({ status: 'success', total: 5, count: 2, limit: 2, offset: 2, repositories: [] })
    await getRepositories({ limit: 2, offset: 2 })
    expect(mockFetch).toHaveBeenCalledWith('/api/repositories?limit=2&offset=2', undefined)
  })

  it('throws on non-2xx response', async () => {
    mockError(500, 'DB error')
    await expect(getRepositories()).rejects.toThrow('HTTP 500: DB error')
  })
})

describe('rescanRepository', () => {
  it('POSTs to /api/rescan/repository/<repo_id>', async () => {
    mockOk({ status: 'success', repository: { repo_id: 'r1', name: 'my-repo', previous_analyzed_at: null }, message: 'marked' })
    const result = await rescanRepository('r1')
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/repository/r1', { method: 'POST' })
    expect(result.repository.name).toBe('my-repo')
  })

  it('URL-encodes the repo_id', async () => {
    mockOk({ status: 'success', repository: { repo_id: 'org/repo', name: 'repo', previous_analyzed_at: null }, message: 'ok' })
    await rescanRepository('org/repo')
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/repository/org%2Frepo', { method: 'POST' })
  })

  it('throws on 404', async () => {
    mockError(404, 'Repository not found')
    await expect(rescanRepository('missing')).rejects.toThrow('HTTP 404: Repository not found')
  })
})

describe('removeRepository', () => {
  it('DELETEs /api/rescan/repository/<repo_id>', async () => {
    mockOk({ status: 'success', repository: { repo_id: 'r2', name: 'old-repo', previous_analyzed_at: null }, message: 'removed' })
    const result = await removeRepository('r2')
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/repository/r2', { method: 'DELETE' })
    expect(result.repository.name).toBe('old-repo')
  })

  it('URL-encodes the repo_id', async () => {
    mockOk({ status: 'success', repository: { repo_id: 'org/repo', name: 'repo', previous_analyzed_at: null }, message: 'ok' })
    await removeRepository('org/repo')
    expect(mockFetch).toHaveBeenCalledWith('/api/rescan/repository/org%2Frepo', { method: 'DELETE' })
  })

  it('throws on non-2xx', async () => {
    mockError(500, 'Server error')
    await expect(removeRepository('r2')).rejects.toThrow('HTTP 500: Server error')
  })
})
