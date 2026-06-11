/**
 * Goals — savings goals with progress bars and contribute action.
 *
 * Visual treatment matches the offline demo: each goal is a card with a
 * faint colored "halo" disc in the top-right, large italic display of
 * current amount, and a prominent amber "Add contribution" button.
 */
import { useEffect, useState } from 'react'
import { Plus, Trash2, Pencil, Target } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import Modal from '../components/UI/Modal.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { goals as goalsApi } from '../services/api.js'
import { formatCurrency } from '../utils/format.js'
import { useAuth } from '../context/AuthContext.jsx'

const COLOR_PRESETS = ['#10B981', '#F59E0B', '#3B82F6', '#8B5CF6', '#EC4899', '#06B6D4']

const DEFAULT_FORM = () => ({
  name: '', description: '', target_amount: '',
  current_amount: 0, currency: 'ALL', target_date: '', color: '#10B981',
})

export default function Goals() {
  const { user } = useAuth()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM())
  const [contributing, setContributing] = useState(null)
  const [contribAmount, setContribAmount] = useState('')
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  const load = () => {
    setLoading(true)
    goalsApi.list().then(setList).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...DEFAULT_FORM(), currency: user?.default_currency || 'ALL' })
    setError(''); setModalOpen(true)
  }
  const openEdit = (g) => {
    setEditing(g)
    setForm({
      name: g.name, description: g.description || '',
      target_amount: g.target_amount, current_amount: g.current_amount,
      currency: g.currency, target_date: g.target_date || '', color: g.color,
    })
    setError(''); setModalOpen(true)
  }

  const onSave = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (editing) {
        await goalsApi.update(editing.id, form)
      } else {
        await goalsApi.create({
          ...form,
          target_amount: Number(form.target_amount),
          current_amount: Number(form.current_amount),
          target_date: form.target_date || null,
        })
      }
      setToast({ open: true, message: 'Goal saved.', type: 'success' })
      setModalOpen(false); load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save.')
    }
  }

  const onContribute = async () => {
    if (!contribAmount) return
    await goalsApi.contribute(contributing.id, Number(contribAmount))
    setToast({
      open: true,
      message: `Added ${formatCurrency(contribAmount, contributing.currency)} to ${contributing.name}.`,
      type: 'success',
    })
    setContributing(null); setContribAmount(''); load()
  }

  const onDelete = async (g) => {
    if (!confirm(`Delete goal "${g.name}"?`)) return
    await goalsApi.remove(g.id)
    setToast({ open: true, message: 'Goal deleted.', type: 'success' })
    load()
  }

  return (
    <div>
      <PageHeader
        title="Goals"
        subtitle="What you’re saving toward."
        actions={<button className="btn-primary" onClick={openCreate}><Plus size={14} /> New goal</button>}
      />

      {loading ? (
        <div className="text-ink-500 text-sm">Loading…</div>
      ) : list.length === 0 ? (
        <div className="card text-center py-16">
          <Target size={32} className="mx-auto text-ink-400 mb-3" />
          <p className="font-display text-2xl italic mb-2">No goals yet</p>
          <p className="text-ink-500 text-sm mb-6">What are you saving for?</p>
          <button className="btn-primary" onClick={openCreate}><Plus size={14} /> Create goal</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {list.map((g) => {
            const pct = Math.min(100, g.percent_complete)
            const remaining = Math.max(0, g.target_amount - g.current_amount)
            return (
              <div key={g.id} className="card relative overflow-hidden">
                {/* Color halo disc */}
                <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10 pointer-events-none"
                  style={{ background: g.color, transform: 'translate(50%, -50%)' }} />

                <div className="relative">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
                        style={{ background: g.color + '20', color: g.color }}>
                        <Target size={18} />
                      </div>
                      <div className="min-w-0">
                        <div className="font-medium truncate">{g.name}</div>
                        {g.description && (
                          <div className="text-xs text-ink-500 truncate">{g.description}</div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(g)} className="btn-ghost px-2 py-1">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => onDelete(g)} className="btn-ghost px-2 py-1 text-red-600">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-3">
                    <span className="font-display text-3xl italic">
                      {formatCurrency(g.current_amount, g.currency)}
                    </span>
                    <span className="text-sm text-ink-500">
                      of {formatCurrency(g.target_amount, g.currency)}
                    </span>
                  </div>

                  <div className="progress-track mb-3">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: g.color }} />
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-ink-500">
                      <span className="font-medium tabular-nums">{pct.toFixed(0)}%</span> complete
                      {' · '}{formatCurrency(remaining, g.currency)} to go
                    </span>
                    {g.days_remaining != null && (
                      <span className={`font-medium ${
                        g.days_remaining < 30 ? 'text-amber-600' : 'text-ink-500'
                      }`}>
                        {g.days_remaining > 0
                          ? `${g.days_remaining} days left`
                          : g.days_remaining === 0 ? 'Due today' : `${-g.days_remaining} days overdue`}
                      </span>
                    )}
                  </div>

                  {!g.is_completed && (
                    <button
                      className="btn-amber w-full justify-center mt-4"
                      onClick={() => { setContributing(g); setContribAmount('') }}
                    >
                      <Plus size={14} /> Add contribution
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create / edit goal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit goal' : 'New goal'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button form="goal-form" type="submit" className="btn-primary">{editing ? 'Save' : 'Create'}</button>
          </>
        }
      >
        <form id="goal-form" onSubmit={onSave} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          <div>
            <label className="label">Name</label>
            <input required className="input" placeholder="Emergency fund" value={form.name} autoFocus
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" placeholder="(optional)" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Target amount</label>
              <input type="number" step="0.01" required className="input font-mono"
                placeholder="0" value={form.target_amount}
                onChange={(e) => setForm({ ...form, target_amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Currency</label>
              <select className="input" value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option value="ALL">ALL</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Already saved</label>
              <input type="number" step="0.01" className="input font-mono" placeholder="0"
                value={form.current_amount}
                onChange={(e) => setForm({ ...form, current_amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Target date</label>
              <input type="date" className="input" value={form.target_date}
                onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label">Color</label>
            <div className="flex gap-2">
              {COLOR_PRESETS.map((c) => (
                <button key={c} type="button"
                  className={`w-8 h-8 rounded-lg transition-all ${form.color === c ? 'ring-2 ring-offset-2 ring-ink-900' : ''}`}
                  style={{ background: c }}
                  onClick={() => setForm({ ...form, color: c })} />
              ))}
            </div>
          </div>
        </form>
      </Modal>

      {/* Contribute */}
      <Modal
        open={!!contributing}
        onClose={() => setContributing(null)}
        title={contributing ? `Contribute to "${contributing.name}"` : ''}
        footer={
          <>
            <button onClick={() => setContributing(null)} className="btn-secondary">Cancel</button>
            <button onClick={onContribute} className="btn-amber">Add</button>
          </>
        }
      >
        <div className="space-y-4">
          {contributing && (
            <div className="text-sm text-ink-500">
              Currently at{' '}
              <span className="font-medium text-ink-900 tabular-nums">
                {formatCurrency(contributing.current_amount, contributing.currency)}
              </span>{' '}of{' '}
              <span className="font-medium text-ink-900 tabular-nums">
                {formatCurrency(contributing.target_amount, contributing.currency)}
              </span>
            </div>
          )}
          <div>
            <label className="label">Amount</label>
            <input type="number" step="0.01" className="input font-mono" placeholder="0.00"
              value={contribAmount} autoFocus
              onChange={(e) => setContribAmount(e.target.value)} />
          </div>
        </div>
      </Modal>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
