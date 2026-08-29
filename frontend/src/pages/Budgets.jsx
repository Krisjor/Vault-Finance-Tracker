/**
 * Budgets — list + create + edit + delete budgets.
 */
import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Sliders } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import Modal from '../components/UI/Modal.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { budgets as budgetsApi, categories as categoriesApi } from '../services/api.js'
import { formatCurrency } from '../utils/format.js'
import { useAuth } from '../context/AuthContext.jsx'

const DEFAULT_FORM = () => ({
  category_id: '', name: '', amount: '', period: 'monthly',
  currency: 'ALL', warn_threshold: 80,
})

export default function Budgets() {
  const { user } = useAuth()
  const [list, setList] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM())
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  const load = () => {
    setLoading(true)
    Promise.all([
      budgetsApi.list(),
      categoriesApi.list({ type: 'expense' }),
    ]).then(([b, c]) => {
      setList(b); setCategories(c)
    }).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...DEFAULT_FORM(), currency: user?.default_currency || 'ALL', category_id: categories[0]?.id || '' })
    setError(''); setModalOpen(true)
  }
  const openEdit = (b) => {
    setEditing(b)
    setForm({
      category_id: b.category_id, name: b.name || '', amount: b.amount, period: b.period,
      currency: b.currency, warn_threshold: b.warn_threshold,
    })
    setError(''); setModalOpen(true)
  }

  const onSave = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (editing) {
        await budgetsApi.update(editing.id, {
          amount: Number(form.amount), warn_threshold: Number(form.warn_threshold),
          name: form.name,
        })
      } else {
        await budgetsApi.create({
          ...form,
          category_id: Number(form.category_id),
          amount: Number(form.amount),
          warn_threshold: Number(form.warn_threshold),
        })
      }
      setToast({ open: true, message: 'Budget saved.', type: 'success' })
      setModalOpen(false); load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save.')
    }
  }

  const onDelete = async (b) => {
    if (!confirm('Delete this budget?')) return
    await budgetsApi.remove(b.id)
    setToast({ open: true, message: 'Budget deleted.', type: 'success' })
    load()
  }

  return (
    <div>
      <PageHeader
        title="Budgets"
        subtitle={`${list.length} active for this month`}
        actions={<button className="btn-primary" onClick={openCreate}><Plus size={14} /> New budget</button>}
      />

      {loading ? (
        <div className="text-ink-500 text-sm">Loading…</div>
      ) : list.length === 0 ? (
        <div className="card text-center py-16">
          <p className="font-display text-2xl italic text-ink-700 mb-1">No budgets yet</p>
          <p className="text-sm text-ink-500 mb-6">Set a monthly cap for any expense category.</p>
          <button className="btn-primary" onClick={openCreate}><Plus size={14} /> Create your first budget</button>
        </div>
      ) : (
        <div className="space-y-3">
          {list.map((b) => {
            const cat = categories.find((c) => c.id === b.category_id)
            const pct = Math.min(100, b.progress.percent)
            const status = b.progress.status
            const fillColor =
              status === 'over' ? '#DC2626' :
              status === 'warning' ? '#F59E0B' : '#10B981'
            const remaining = b.amount - b.progress.spent
            return (
              <div key={b.id} className="card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
                      style={{ background: (cat?.color || '#94a3b8') + '20', color: cat?.color || '#94a3b8' }}>
                      <Sliders size={16} />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium truncate">{b.name || cat?.name || 'Budget'}</div>
                      <div className="text-xs text-ink-500 capitalize">
                        {b.period} budget · {b.currency}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div className="tabular-nums text-sm">
                        <span className="font-medium">{formatCurrency(b.progress.spent, b.currency)}</span>
                        <span className="text-ink-500"> / {formatCurrency(b.amount, b.currency)}</span>
                      </div>
                      <div className={`text-xs font-medium ${
                        status === 'over' ? 'text-red-600' :
                        status === 'warning' ? 'text-amber-600' : 'text-emerald-600'
                      }`}>
                        {status === 'over'
                          ? `Over by ${formatCurrency(b.progress.spent - b.amount, b.currency)}`
                          : status === 'warning'
                          ? `${(100 - pct).toFixed(0)}% left, careful`
                          : `${formatCurrency(remaining, b.currency)} remaining`}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(b)} className="btn-ghost px-2 py-1">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => onDelete(b)} className="btn-ghost px-2 py-1 text-red-600">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${pct}%`, background: fillColor }} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit budget' : 'New budget'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button form="budget-form" type="submit" className="btn-primary">{editing ? 'Save' : 'Create'}</button>
          </>
        }
      >
        <form id="budget-form" onSubmit={onSave} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          {!editing && (
            <div>
              <label className="label">Category</label>
              <select required className="input" value={form.category_id}
                onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="label">Label (optional)</label>
            <input className="input" placeholder="e.g. Eating out"
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Amount</label>
              <input type="number" step="0.01" required className="input font-mono"
                placeholder="0.00" value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Currency</label>
              <select className="input" value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })} disabled={!!editing}>
                <option value="ALL">ALL</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          {!editing && (
            <div>
              <label className="label">Period</label>
              <select className="input" value={form.period}
                onChange={(e) => setForm({ ...form, period: e.target.value })}>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
          )}
          <div>
            <label className="label">Warn me at {form.warn_threshold}% of budget</label>
            <input type="range" min={50} max={100} step={5} value={form.warn_threshold}
              onChange={(e) => setForm({ ...form, warn_threshold: e.target.value })}
              className="w-full" />
          </div>
        </form>
      </Modal>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
