import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import ApiButton from '../components/ApiButton'
import Toast, { type ToastVariant } from '../components/Toast'
import { triggerGithubRescan, triggerAzureDevOpsRescan, triggerComputeServiceMetrics } from '../api/client'

interface ToastState {
  message: string
  variant: ToastVariant
}

export default function ExtractionPage() {
  const [toast, setToast] = useState<ToastState | null>(null)
  const dismiss = useCallback(() => setToast(null), [])

  const githubMutation = useMutation({
    mutationFn: triggerGithubRescan,
    onSuccess: (data) => setToast({ message: `GitHub rescan started — task_id: ${data.task_id}`, variant: 'success' }),
    onError: (err: Error) => setToast({ message: err.message, variant: 'error' }),
  })

  const azureMutation = useMutation({
    mutationFn: triggerAzureDevOpsRescan,
    onSuccess: (data) => setToast({ message: `Azure DevOps rescan started — task_id: ${data.task_id}`, variant: 'success' }),
    onError: (err: Error) => setToast({ message: err.message, variant: 'error' }),
  })

  const computeMutation = useMutation({
    mutationFn: triggerComputeServiceMetrics,
    onSuccess: (data) => setToast({ message: `Service metrics computation started — task_id: ${data.task_id}`, variant: 'success' }),
    onError: (err: Error) => setToast({ message: err.message, variant: 'error' }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Extraction Control</h1>
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4 max-w-lg">
        <div className="flex flex-col gap-2">
          <p className="text-sm text-gray-600">
            Trigger a full re-extraction of GitHub repositories and metadata.
          </p>
          <ApiButton
            onClick={() => githubMutation.mutate()}
            loading={githubMutation.isPending}
          >
            Trigger GitHub Rescan
          </ApiButton>
        </div>
        <hr className="border-gray-100" />
        <div className="flex flex-col gap-2">
          <p className="text-sm text-gray-600">
            Trigger a full re-extraction of Azure DevOps projects and repositories.
          </p>
          <ApiButton
            onClick={() => azureMutation.mutate()}
            loading={azureMutation.isPending}
          >
            Trigger Azure DevOps Rescan
          </ApiButton>
        </div>
        <hr className="border-gray-100" />
        <div className="flex flex-col gap-2">
          <p className="text-sm text-gray-600">
            Compute and persist service-level metrics for all repositories.
          </p>
          <ApiButton
            onClick={() => computeMutation.mutate()}
            loading={computeMutation.isPending}
          >
            Compute Service Metrics
          </ApiButton>
        </div>
      </div>
      {toast && (
        <Toast message={toast.message} variant={toast.variant} onDismiss={dismiss} />
      )}
    </div>
  )
}
