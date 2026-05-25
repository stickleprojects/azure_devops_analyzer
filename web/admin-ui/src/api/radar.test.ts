import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getRadar, getRadarHistory } from './radar'

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

describe('radar api client', () => {
  it('GETs /api/radar', async () => {
    mockOk({ documentTitle: 'Radar', quadrants: [], rings: [], entries: [] })
    await getRadar()
    expect(mockFetch).toHaveBeenCalledWith('/api/radar')
  })

  it('GETs /api/radar/history', async () => {
    mockOk({ timeline: [] })
    await getRadarHistory()
    expect(mockFetch).toHaveBeenCalledWith('/api/radar/history')
  })

  it('throws non-2xx with body text', async () => {
    mockError(500, 'backend failure')
    await expect(getRadar()).rejects.toThrow('HTTP 500: backend failure')
  })

  it('falls back to statusText when body is empty', async () => {
    mockError(503, '', 'Service Unavailable')
    await expect(getRadarHistory()).rejects.toThrow('HTTP 503: Service Unavailable')
  })
})
