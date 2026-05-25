import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getLibraryDetail, getPackageAdoption } from '../api/client'

const SEVERITY_COLOURS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-300',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  LOW: 'bg-blue-100 text-blue-800 border-blue-300',
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    SEVERITY_COLOURS[severity.toUpperCase()] ??
    'bg-gray-100 text-gray-700 border-gray-300'
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold uppercase ${cls}`}
    >
      {severity}
    </span>
  )
}

export default function LibraryDetailPage() {
  const { ecosystem = '', name = '' } = useParams<{
    ecosystem: string
    name: string
  }>()

  const detailQuery = useQuery({
    queryKey: ['library-detail', ecosystem, name],
    queryFn: () => getLibraryDetail(name, ecosystem),
    enabled: Boolean(name && ecosystem),
  })

  const adoptionQuery = useQuery({
    queryKey: ['library-adoption', ecosystem, name],
    queryFn: () => getPackageAdoption(name, ecosystem, 90),
    enabled: Boolean(name && ecosystem),
  })

  const detail = detailQuery.data
  const adoption = adoptionQuery.data ?? []

  return (
    <div>
      <nav className="mb-4 text-sm text-gray-500" aria-label="Breadcrumb">
        <Link to="/repositories" className="hover:text-blue-600 hover:underline">
          Repositories
        </Link>
        <span className="mx-2">›</span>
        <span className="text-gray-700">Library Detail</span>
      </nav>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {name || '—'}
        <span className="ml-2 text-sm font-normal text-gray-500">{ecosystem}</span>
      </h1>

      {(detailQuery.isLoading || adoptionQuery.isLoading) && (
        <p className="text-sm text-gray-500 mt-4">Loading…</p>
      )}

      {detailQuery.isError && (
        <p className="text-sm text-red-600 mt-4">
          Failed to load library detail:{' '}
          {(detailQuery.error as Error).message}
        </p>
      )}

      {detail && (
        <div className="space-y-8 mt-6">
          {/* Metadata */}
          <section aria-label="Package metadata">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Metadata</h2>
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden max-w-lg">
              <table className="min-w-full divide-y divide-gray-100">
                <tbody className="divide-y divide-gray-100">
                  <tr>
                    <td className="px-4 py-2 text-sm font-medium text-gray-600 w-40">Package</td>
                    <td className="px-4 py-2 text-sm text-gray-800 font-mono">
                      {detail.metadata.package_name}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 text-sm font-medium text-gray-600">Ecosystem</td>
                    <td className="px-4 py-2 text-sm text-gray-800">{detail.metadata.ecosystem}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 text-sm font-medium text-gray-600">
                      Latest Version
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-800 font-mono">
                      {detail.metadata.latest_version ?? '—'}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 text-sm font-medium text-gray-600">EOL</td>
                    <td className="px-4 py-2 text-sm">
                      {detail.metadata.is_eol ? (
                        <span className="font-semibold text-red-600">
                          Yes{detail.metadata.eol_date ? ` (${detail.metadata.eol_date})` : ''}
                        </span>
                      ) : (
                        <span className="text-green-700">No</span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* CVE list */}
          <section aria-label="Known CVEs">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              Known CVEs{' '}
              <span className="text-sm font-normal text-gray-500">
                ({detail.cves.length})
              </span>
            </h2>
            {detail.cves.length === 0 ? (
              <p className="text-sm text-gray-500">No known CVEs.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 bg-white">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        CVE ID
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Severity
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Summary
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Fixed In
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Published
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Exposed Repos
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {detail.cves.map((cve) => (
                      <tr key={cve.cve_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-700">
                          <a
                            href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-blue-600 hover:underline"
                          >
                            {cve.cve_id}
                          </a>
                        </td>
                        <td className="px-4 py-3">
                          <SeverityBadge severity={cve.severity} />
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {cve.summary ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-600">
                          {cve.fixed_in_version ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {cve.published_date ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">
                          {cve.exposed_repo_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Adoption timeline */}
          <section aria-label="Adoption timeline">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              Adoption Timeline{' '}
              <span className="text-sm font-normal text-gray-500">(last 90 days)</span>
            </h2>
            {adoptionQuery.isLoading && (
              <p className="text-sm text-gray-500">Loading timeline…</p>
            )}
            {adoptionQuery.isError && (
              <p className="text-sm text-red-600">
                Failed to load adoption timeline:{' '}
                {(adoptionQuery.error as Error).message}
              </p>
            )}
            {!adoptionQuery.isLoading && !adoptionQuery.isError && adoption.length === 0 && (
              <p className="text-sm text-gray-500">No adoption data available.</p>
            )}
            {adoption.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 bg-white">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Repo Count
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {adoption.map((row) => (
                      <tr key={row.adoption_date} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-700">
                          {row.adoption_date}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">
                          {row.repo_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Per-repo usage */}
          <section aria-label="Per-repository usage">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              Repository Usage{' '}
              <span className="text-sm font-normal text-gray-500">
                ({detail.usage.length} repos)
              </span>
            </h2>
            {detail.usage.length === 0 ? (
              <p className="text-sm text-gray-500">No repositories using this library.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 bg-white">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Repository
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Team
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Version
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Vulnerable
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {detail.usage.map((row) => (
                      <tr key={row.repo_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-700">
                          {row.repo_id}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{row.team_name}</td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-600">
                          {row.version ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {row.has_known_vulnerabilities ? (
                            <span className="text-red-600 font-semibold">Yes</span>
                          ) : (
                            <span className="text-green-700">No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* By-team summary */}
          <section aria-label="Usage by team">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              Usage by Team{' '}
              <span className="text-sm font-normal text-gray-500">
                ({detail.by_team.length} teams)
              </span>
            </h2>
            {detail.by_team.length === 0 ? (
              <p className="text-sm text-gray-500">No team data available.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 bg-white">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Team
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Repos
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Exposed
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Versions in Use
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {detail.by_team.map((row) => (
                      <tr key={row.team_name} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-700">{row.team_name}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">
                          {row.repo_count}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          {row.exposed_repos > 0 ? (
                            <span className="font-semibold text-red-600">{row.exposed_repos}</span>
                          ) : (
                            <span className="text-gray-700">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-600">
                          {row.versions_in_use ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
