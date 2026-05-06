import { GRAFANA_BASE, GRAFANA_DASHBOARDS } from '../config'

export default function HomePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Grafana Dashboards</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {GRAFANA_DASHBOARDS.map(({ title, uid }) => (
          <a
            key={uid}
            href={`${GRAFANA_BASE}/d/${uid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-4 shadow-sm hover:shadow-md hover:border-blue-400 transition-all group"
          >
            <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700">
              {title}
            </span>
            <svg
              className="h-4 w-4 text-gray-400 group-hover:text-blue-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        ))}
      </div>
    </div>
  )
}
