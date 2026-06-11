import { useEffect } from 'react'
import { CheckCircle2, AlertCircle, X } from 'lucide-react'

export function Toast({ open, type = 'success', message, onClose }) {
  useEffect(() => {
    if (!open) return
    const id = setTimeout(() => onClose?.(), 2500)
    return () => clearTimeout(id)
  }, [open, onClose])

  if (!open) return null

  const Icon = type === 'success' ? CheckCircle2 : AlertCircle
  const bg =
    type === 'success' ? 'bg-emerald-700' :
    type === 'error'   ? 'bg-red-600' : 'bg-ink-900'

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lift text-white text-sm font-medium ${bg}`}>
        <Icon size={18} />
        <span>{message}</span>
        <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100">
          <X size={14} />
        </button>
      </div>
    </div>
  )
}

export function Alert({ type = 'info', children }) {
  const styles = {
    info:    'bg-blue-50    border-blue-200    text-blue-900',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    warning: 'bg-amber-50   border-amber-200   text-amber-900',
    error:   'bg-red-50     border-red-200     text-red-900',
  }[type]
  return (
    <div className={`px-4 py-3 rounded-lg border ${styles} text-sm`}>
      {children}
    </div>
  )
}
