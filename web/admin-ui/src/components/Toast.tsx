import { useEffect } from 'react'

export type ToastVariant = 'success' | 'error'

interface ToastProps {
  message: string
  variant: ToastVariant
  onDismiss: () => void
}

export default function Toast({ message, variant, onDismiss }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 6000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  const colours =
    variant === 'success'
      ? 'bg-green-50 border-green-400 text-green-800'
      : 'bg-red-50 border-red-400 text-red-800'

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-50 flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg max-w-sm ${colours}`}
    >
      <span className="flex-1 text-sm">{message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="ml-2 text-current opacity-60 hover:opacity-100 focus:outline-none"
      >
        ✕
      </button>
    </div>
  )
}
