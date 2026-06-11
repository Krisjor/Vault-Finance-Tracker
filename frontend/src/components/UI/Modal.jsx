import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function Modal({ open, onClose, title, children, footer, size = 'md' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  const sizeClass = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' }[size]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-ink-900/45" />
      <div
        onClick={(e) => e.stopPropagation()}
        className={`relative bg-white rounded-2xl shadow-lift border border-cream-200 w-full ${sizeClass} animate-slide-up max-h-[90vh] flex flex-col`}
      >
        <div className="flex items-start justify-between px-7 pt-7 pb-3">
          <h2 className="font-display text-2xl italic text-ink-900">{title}</h2>
          <button onClick={onClose} className="btn-ghost px-2 py-1.5" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="px-7 pb-2 overflow-y-auto">{children}</div>
        {footer && (
          <div className="px-7 py-5 mt-3 border-t border-cream-200 flex justify-end gap-2 rounded-b-2xl">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
