import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import HomePage from './HomePage'
import { GRAFANA_BASE, GRAFANA_DASHBOARDS } from '../config'

describe('HomePage', () => {
  it('renders all 13 dashboard tiles', () => {
    render(<HomePage />)
    for (const { title } of GRAFANA_DASHBOARDS) {
      expect(screen.getByText(title)).toBeInTheDocument()
    }
  })

  it('links each tile to the correct Grafana URL in a new tab', () => {
    render(<HomePage />)
    for (const { title, uid } of GRAFANA_DASHBOARDS) {
      const link = screen.getByText(title).closest('a')!
      expect(link).toHaveAttribute('href', `${GRAFANA_BASE}/d/${uid}`)
      expect(link).toHaveAttribute('target', '_blank')
    }
  })
})
