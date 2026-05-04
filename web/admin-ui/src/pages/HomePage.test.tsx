import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import HomePage from './HomePage'

describe('HomePage', () => {
  it('renders all 13 dashboard tiles', () => {
    render(<HomePage />)
    const expectedTitles = [
      'Home',
      'Repositories',
      'Security',
      'Technology',
      'Admin',
      'Library Deep Dive',
      'Repository Deep Dive',
      'Dependency Vulnerabilities',
      'Pull Requests',
      'Teams',
      'Services',
      'Contributors',
      'Extraction Health',
    ]
    for (const title of expectedTitles) {
      expect(screen.getByText(title)).toBeInTheDocument()
    }
  })

  it('links each tile to the correct Grafana URL in a new tab', () => {
    render(<HomePage />)
    const tiles: Array<[string, string]> = [
      ['Home', 'http://localhost:3000/d/dashboard-home'],
      ['Repositories', 'http://localhost:3000/d/repo-overview'],
      ['Security', 'http://localhost:3000/d/security-dashboard'],
      ['Technology', 'http://localhost:3000/d/technology-landscape'],
      ['Admin', 'http://localhost:3000/d/admin-dashboard'],
      ['Library Deep Dive', 'http://localhost:3000/d/library-detail-deep-dive'],
      ['Repository Deep Dive', 'http://localhost:3000/d/repo-deep-dive'],
      ['Dependency Vulnerabilities', 'http://localhost:3000/d/dep-vuln-portfolio'],
      ['Pull Requests', 'http://localhost:3000/d/pull-requests'],
      ['Teams', 'http://localhost:3000/d/team-overview'],
      ['Services', 'http://localhost:3000/d/service-overview'],
      ['Contributors', 'http://localhost:3000/d/contributor-analytics'],
      ['Extraction Health', 'http://localhost:3000/d/extraction-health'],
    ]
    for (const [title, href] of tiles) {
      const link = screen.getByText(title).closest('a')!
      expect(link).toHaveAttribute('href', href)
      expect(link).toHaveAttribute('target', '_blank')
    }
  })
})
