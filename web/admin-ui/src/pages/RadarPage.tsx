import { useQuery } from '@tanstack/react-query'
import { getRadar } from '../api/radar'
import RadarChart from '../components/RadarChart'

export default function RadarPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['radar'],
    queryFn: getRadar,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Tech Radar</h1>

      {isLoading && <p className="text-sm text-gray-500">Loading radar…</p>}

      {isError && (
        <p className="text-sm text-red-600">Failed to load radar: {(error as Error).message}</p>
      )}

      {data && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {data.publication
              ? `Publication ${data.publication.version} · ${data.publication.date}`
              : 'No publication metadata available'}
          </p>

          {data.entries.length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-white p-6 text-sm text-gray-600 shadow-sm">
              No radar published yet.
            </div>
          ) : (
            <RadarChart data={data} />
          )}
        </div>
      )}
    </div>
  )
}
