import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRadarHistory, type RadarHistoryRow } from '../api/radar'

type SortKey = 'publication_date' | 'package_name'
type SortDirection = 'asc' | 'desc'

export default function RadarHistoryPage() {
  const [sortKey, setSortKey] = useState<SortKey>('publication_date')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['radar-history'],
    queryFn: getRadarHistory,
  })

  const rows = useMemo(() => {
    const timeline = [...(data?.timeline ?? [])]
    timeline.sort((a, b) => compareRows(a, b, sortKey, sortDirection))
    return timeline
  }, [data?.timeline, sortDirection, sortKey])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Tech Radar History</h1>

      {isLoading && <p className="text-sm text-gray-500">Loading radar history…</p>}

      {isError && (
        <p className="text-sm text-red-600">
          Failed to load radar history: {(error as Error).message}
        </p>
      )}

      {!isLoading && !isError && rows.length === 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-sm text-gray-600 shadow-sm">
          No radar history available.
        </div>
      )}

      {!isLoading && !isError && rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 bg-white">
            <thead className="bg-gray-50">
              <tr>
                <SortableHeader
                  label="Publication Date"
                  active={sortKey === 'publication_date'}
                  direction={sortDirection}
                  onClick={() => toggleSort('publication_date')}
                />
                <SortableHeader
                  label="Package"
                  active={sortKey === 'package_name'}
                  direction={sortDirection}
                  onClick={() => toggleSort('package_name')}
                />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ecosystem
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Prior Ring
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Current Ring
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Repo Δ
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Vulnerability Δ
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => (
                <tr key={`${row.publication_date}-${row.package_name}-${row.ecosystem}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-700">{row.publication_date}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-800">{row.package_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{row.ecosystem}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{row.prior_ring ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{row.current_ring}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{row.repo_count_delta}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{row.vulnerability_change}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function compareRows(
  a: RadarHistoryRow,
  b: RadarHistoryRow,
  key: SortKey,
  direction: SortDirection,
): number {
  const left = key === 'publication_date' ? a.publication_date : a.package_name.toLowerCase()
  const right = key === 'publication_date' ? b.publication_date : b.package_name.toLowerCase()
  const comparison = left.localeCompare(right)
  return direction === 'asc' ? comparison : -comparison
}

interface SortableHeaderProps {
  label: string
  active: boolean
  direction: SortDirection
  onClick: () => void
}

function SortableHeader({ label, active, direction, onClick }: SortableHeaderProps) {
  return (
    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 hover:text-gray-700">
        {label}
        <span aria-hidden="true">{active ? (direction === 'asc' ? '↑' : '↓') : '↕'}</span>
      </button>
    </th>
  )
}
