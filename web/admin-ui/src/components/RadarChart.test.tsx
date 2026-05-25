import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RadarChart from './RadarChart'
import type { RadarResponse } from '../api/radar'

vi.mock('../vendor/zalando-radar/radar', () => ({
  radar_visualization: vi.fn(),
}))

import { radar_visualization } from '../vendor/zalando-radar/radar'

const radarData: RadarResponse = {
  documentTitle: 'Organization Tech Radar',
  quadrants: [{ name: 'Infrastructure' }, { name: 'Platforms' }, { name: 'Tools' }, { name: 'Languages' }],
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
      description: 'desc',
      quadrant: 'Languages',
      ring: 'Trial',
      isNew: false,
      isMoved: true,
    },
  ],
}

describe('RadarChart', () => {
  it('renders an svg and initializes the radar renderer', () => {
    render(<RadarChart data={radarData} />)

    expect(screen.getByLabelText('Technology radar chart')).toBeInTheDocument()
    expect(radar_visualization).toHaveBeenCalledTimes(1)
  })
})
