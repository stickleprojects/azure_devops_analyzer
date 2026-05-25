import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import Toast, { type ToastVariant } from '../components/Toast'
import { getRepositories, rescanRepository, removeRepository } from '../api/client'
import type { Repository } from '../api/types'

interface ToastState {
  message: string
  variant: ToastVariant
}

export default function RepositoriesPage() {
  const [search, setSearch] = useState('')
  const [toast, setToast] = useState<ToastState | null>(null)
  const dismiss = useCallback(() => setToast(null), [])

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['repositories', search],
    queryFn: () => getRepositories({ search: search || undefined }),
  })

  const rescanMutation = useMutation({
    mutationFn: rescanRepository,
    onSuccess: (resp) =>
      setToast({ message: `${resp.repository.name} marked for rescan.`, variant: 'success' }),
    onError: (err: Error) => setToast({ message: err.message, variant: 'error' }),
  })

  const removeMutation = useMutation({
    mutationFn: removeRepository,
    onSuccess: (resp) =>
      setToast({ message: `${resp.repository.name} removed.`, variant: 'success' }),
    onError: (err: Error) => setToast({ message: err.message, variant: 'error' }),
  })

  const repos: Repository[] = data?.repositories ?? []

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Repositories</h1>

      <div className="mb-4 max-w-sm">
        <input
          type="search"
          placeholder="Filter by name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Filter repositories"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading repositories…</p>}

      {isError && (
        <p className="text-sm text-red-600">
          Failed to load repositories: {(error as Error).message}
        </p>
      )}

      {!isLoading && !isError && (
        <>
          <p className="text-xs text-gray-500 mb-2">
            {data?.total ?? 0} total
            {search && `, filtered to ${repos.length}`}
          </p>
          <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 bg-white">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Analyzed
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Active
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {repos.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-400">
                      No repositories found.
                    </td>
                  </tr>
                ) : (
                  repos.map((repo) => (
                    <tr key={repo.repo_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-800">
                        {repo.url ? (
                          <a
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-blue-600 hover:underline"
                          >
                            {repo.name}
                          </a>
                        ) : (
                          repo.name
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                        {repo.last_analyzed_at
                          ? new Date(repo.last_analyzed_at).toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {repo.is_active ? 'Yes' : 'No'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => rescanMutation.mutate(repo.repo_id)}
                            disabled={
                              (rescanMutation.isPending && rescanMutation.variables === repo.repo_id) ||
                              (removeMutation.isPending && removeMutation.variables === repo.repo_id)
                            }
                            className="rounded px-2 py-1 text-xs font-medium text-blue-700 border border-blue-300 bg-blue-50 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          >
                            Rescan
                          </button>
                          <button
                            onClick={() => removeMutation.mutate(repo.repo_id)}
                            disabled={
                              (rescanMutation.isPending && rescanMutation.variables === repo.repo_id) ||
                              (removeMutation.isPending && removeMutation.variables === repo.repo_id)
                            }
                            className="rounded px-2 py-1 text-xs font-medium text-red-700 border border-red-300 bg-red-50 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onDismiss={dismiss} />
      )}
    </div>
  )
}
