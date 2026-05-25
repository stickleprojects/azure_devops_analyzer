import type { RadarResponse, RadarQuadrant, RadarRing } from '../api/radar'

export interface RadarConfigEntry {
  label: string
  quadrant: number
  ring: number
  moved: number
  active: boolean
}

export interface RadarVisualizationConfig {
  title: string
  quadrants: RadarQuadrant[]
  rings: RadarRing[]
  entries: RadarConfigEntry[]
  date?: string
}

export function toRadarConfig(api: RadarResponse): RadarVisualizationConfig {
  const quadrantIndex = new Map(api.quadrants.map((quadrant, index) => [quadrant.name, index]))
  const ringIndex = new Map(api.rings.map((ring, index) => [ring.name, index]))

  const entries: RadarConfigEntry[] = []

  for (const entry of api.entries) {
    const quadrant = quadrantIndex.get(entry.quadrant)
    const ring = ringIndex.get(entry.ring)

    if (quadrant === undefined || ring === undefined) {
      console.warn(
        `Dropping radar entry "${entry.label}" because quadrant/ring was not found: quadrant=${entry.quadrant}, ring=${entry.ring}`,
      )
      continue
    }

    entries.push({
      label: entry.label,
      quadrant,
      ring,
      moved: entry.isNew ? 2 : entry.isMoved ? 1 : 0,
      active: true,
    })
  }

  return {
    title: api.documentTitle,
    date: api.publication?.date,
    quadrants: api.quadrants.map((quadrant) => ({ name: quadrant.name })),
    rings: api.rings.map((ring) => ({ name: ring.name, color: ring.color })),
    entries,
  }
}
