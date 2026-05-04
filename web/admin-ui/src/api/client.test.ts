import { describe, it, expect, vi, beforeEach } from 'vitest'
import { triggerGithubRescan, triggerAzureDevOpsRescan, getHealth } from './client'

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

function mockError(status: number, bodyText: string) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
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
    await expect(triggerGithubRescan()).rejects.toThrow('Internal Server Error')
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
    await expect(triggerAzureDevOpsRescan()).rejects.toThrow('Bad Request')
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
    await expect(getHealth()).rejects.toThrow('Service Unavailable')
  })
})
