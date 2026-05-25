import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RadarResponse } from '../api/radar'
import { toRadarConfig } from './radarMapping'

const apiResponse: RadarResponse = {
  documentTitle: 'Organization Tech Radar',
  quadrants: [
    { name: 'Infrastructure' },
    { name: 'Platforms' },
    { name: 'Tools' },
    { name: 'Languages & Frameworks' },
  ],
  rings: [
    { name: 'Adopt', color: '#00AA00' },
    { name: 'Trial', color: '#00FFFF' },
    { name: 'Assess', color: '#FFFF00' },
    { name: 'Hold', color: '#FF0000' },
  ],
  entries: [
    {
      id: 1,
      label: 'react',
      description: 'ui library',
      quadrant: 'Languages & Frameworks',
      ring: 'Trial',
      isNew: false,
      isMoved: true,
    },
    {
      id: 2,
      label: 'python',
      description: 'language',
      quadrant: 'Languages & Frameworks',
      ring: 'Adopt',
      isNew: true,
      isMoved: false,
    },
    {
      id: 3,
      label: 'legacy-lib',
      description: 'legacy',
      quadrant: 'Tools',
      ring: 'Hold',
      isNew: false,
      isMoved: false,
    },
  ],
  publication: {
    id: 11,
    version: '2026.05',
    date: '2026-05-25',
    published_by: 'bot',
  },
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('toRadarConfig', () => {
  it('maps quadrant and ring names to numeric indices', () => {
    const result = toRadarConfig(apiResponse)
    expect(result.entries).toEqual([
      { id: 1, label: 'react', quadrant: 3, ring: 1, moved: 1, active: true },
      { id: 2, label: 'python', quadrant: 3, ring: 0, moved: 2, active: true },
      { id: 3, label: 'legacy-lib', quadrant: 2, ring: 3, moved: 0, active: true },
    ])
  })

  it('passes ring colors through unchanged', () => {
    const result = toRadarConfig(apiResponse)
    expect(result.rings).toEqual(apiResponse.rings)
  })

  it('handles empty entries', () => {
    const result = toRadarConfig({ ...apiResponse, entries: [] })
    expect(result.entries).toEqual([])
  })

  it('drops entries with unknown quadrant/ring and warns', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const result = toRadarConfig({
      ...apiResponse,
      entries: [
        ...apiResponse.entries,
        {
          id: 99,
          label: 'bad-data',
          description: 'unknown references',
          quadrant: 'Unknown Quadrant',
          ring: 'Unknown Ring',
          isNew: false,
          isMoved: false,
        },
      ],
    })

    expect(result.entries).toHaveLength(3)
    expect(result.entries.find((entry) => entry.label === 'bad-data')).toBeUndefined()
    expect(warnSpy).toHaveBeenCalledOnce()
  })
})
