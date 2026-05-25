import { useEffect, useRef } from 'react'
import type { RadarResponse } from '../api/radar'
import { toRadarConfig } from '../lib/radarMapping'
import { radar_visualization } from '../vendor/zalando-radar/radar'

interface RadarChartProps {
  data: RadarResponse
}

export default function RadarChart({ data }: RadarChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) {
      return
    }

    const clear = () => {
      while (svg.firstChild) {
        svg.removeChild(svg.firstChild)
      }
    }

    clear()
    radar_visualization({ ...toRadarConfig(data), svg: svg.id })

    return () => {
      clear()
    }
  }, [data])

  return (
    <svg
      id="radar"
      ref={svgRef}
      viewBox="0 0 1450 1000"
      aria-label="Technology radar chart"
      className="w-full max-w-5xl bg-white rounded-lg border border-gray-200 shadow-sm"
    />
  )
}
