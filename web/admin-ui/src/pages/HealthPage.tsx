import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/client'
import { FLOWER_BASE, GRAFANA_BASE } from '../config'

export default function HealthPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">System Health</h1>
      <div className="flex gap-4 mb-6">
        <a
          href={FLOWER_BASE}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md bg-white border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
        >
          Open Flower ↗
        </a>
        <a
          href={`${GRAFANA_BASE}/d/admin-dashboard`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md bg-white border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
        >
          Grafana Admin Dashboard ↗
        </a>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading health data…</p>}

      {isError && (
        <p className="text-sm text-red-600">
          Failed to load health data: {(error as Error).message}
        </p>
      )}

      {data && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden max-w-2xl">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/3">
                  Key
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Value
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(data).map(([key, value]) => (
                <tr key={key} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-700">{key}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 font-mono break-all">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
