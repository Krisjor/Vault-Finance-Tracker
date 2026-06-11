/**
 * Page header — large italic display title with optional subtitle and actions.
 */
export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-end justify-between mb-8 gap-4">
      <div className="min-w-0">
        <h1 className="font-display text-4xl italic text-ink-900 leading-none">{title}</h1>
        {subtitle && <p className="text-sm text-ink-500 mt-2">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}
