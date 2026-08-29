/**
 * Accounts page — list, create, edit, archive accounts.
 */
import { useEffect, useMemo, useState } from 'react'
import { Plus, Pencil, Archive, Trash2 } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import Modal from '../components/UI/Modal.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { accounts as accountsApi, transactions as txnsApi } from '../services/api.js'
import { formatCurrency } from '../utils/format.js'
import { useAuth } from '../context/AuthContext.jsx'

const TYPE_LABELS = {
  checking: 'Checking', savings: 'Savings', credit_card: 'Credit Card',
  cash: 'Cash', investment: 'Investment', loan: 'Loan',
}

const PRESET_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6',
  '#EC4899', '#EF4444', '#06B6D4', '#64748b',
]

const DEFAULT_FORM = {
  name: '', account_type: 'checking', currency: 'ALL',
  initial_balance: 0, color: '#3B82F6', notes: '',
}

function startOfMonth() {
  const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0)
  return d.toISOString().slice(0, 10)
}

export default function Accounts() {
  const { user } = useAuth()
  const [list, setList] = useState([])
  const [monthChanges, setMonthChanges] = useState({})
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  const load = () => {
    setLoading(true)
    accountsApi.list({ include_archived: true })
      .then(async (rows) => {
        setList(rows)
        // Pull this-month transactions to compute per-account monthly change.
        try {
          const since = startOfMonth()
          const tx = await txnsApi.list({ page_size: 500, start_date: since })
          const map = {}
          for (const t of (tx.items || [])) {
            const delta = t.transaction_type === 'income' ?  Number(t.amount)
                        : t.transaction_type === 'expense' ? -Number(t.amount) : 0
            map[t.account_id] = (map[t.account_id] || 0) + delta
          }
          setMonthChanges(map)
        } catch {/* non-fatal */}
      })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const totalsByCurrency = useMemo(() => {
    const m = {}
    for (const a of list) {
      if (a.is_archived) continue
      m[a.currency] = (m[a.currency] || 0) + Number(a.current_balance)
    }
    return m
  }, [list])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...DEFAULT_FORM, currency: user?.default_currency || 'ALL' })
    setError(''); setModalOpen(true)
  }
  const openEdit = (a) => {
    setEditing(a)
    setForm({
      name: a.name, account_type: a.account_type, currency: a.currency,
      initial_balance: a.initial_balance, color: a.color || '#3B82F6',
      notes: a.notes || '',
    })
    setError(''); setModalOpen(true)
  }

  const onSave = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (editing) {
        await accountsApi.update(editing.id, {
          name: form.name, color: form.color, notes: form.notes,
        })
        setToast({ open: true, message: 'Account updated.', type: 'success' })
      } else {
        await accountsApi.create(form)
        setToast({ open: true, message: 'Account created.', type: 'success' })
      }
      setModalOpen(false); load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save.')
    }
  }

  const toggleArchive = async (a) => {
    await accountsApi.update(a.id, { is_archived: !a.is_archived })
    load()
  }
  const onDelete = async (a) => {
    if (!confirm(`Delete "${a.name}" and ALL its transactions? This cannot be undone.`)) return
    await accountsApi.remove(a.id)
    setToast({ open: true, message: 'Account deleted.', type: 'success' })
    load()
  }

  const visibleAccounts = list.filter((a) => !a.is_archived)

  return (
    <div>
      <PageHeader
        title="Accounts"
        subtitle="Every place your money lives."
        actions={<button className="btn-primary" onClick={openCreate}><Plus size={14} /> Add account</button>}
      />

      {/* Net worth hero card */}
      <div className="card mb-6 bg-ink-900 text-cream-50 border-ink-900">
        <div className="stat-label text-cream-200">Net worth</div>
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 mt-3">
          {Object.entries(totalsByCurrency).map(([cur, total]) => (
            <div key={cur}>
              <span className="font-display text-5xl italic">{formatCurrency(total, cur)}</span>
              <span className="ml-2 text-xs text-cream-200 uppercase tracking-wider">{cur}</span>
            </div>
          ))}
          {Object.keys(totalsByCurrency).length === 0 && (
            <span className="font-display text-5xl italic text-cream-200">—</span>
          )}
        </div>
        <div className="text-xs text-cream-200 mt-3">
          Across {visibleAccounts.length} accounts · Not currency-converted (intentional design choice)
        </div>
      </div>

      {loading ? (
        <div className="text-ink-500 text-sm">Loading…</div>
      ) : list.length === 0 ? (
        <div className="card text-center py-16">
          <h3 className="font-display text-2xl italic mb-2">No accounts yet</h3>
          <p className="text-ink-500 text-sm mb-6">Create your first account to start tracking money.</p>
          <button className="btn-primary" onClick={openCreate}><Plus size={14} /> Create account</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {list.map((a) => {
            const change = monthChanges[a.id] || 0
            return (
              <div key={a.id} className={`card group relative ${a.is_archived ? 'opacity-60' : ''}`}>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-10 h-10 rounded-lg shrink-0" style={{ background: a.color }} />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{a.name}</div>
                      <div className="text-xs text-ink-500 capitalize">
                        {TYPE_LABELS[a.account_type]?.toLowerCase() || a.account_type}
                      </div>
                    </div>
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 transition flex gap-1">
                    <button onClick={() => openEdit(a)} className="btn-ghost px-2 py-1" title="Edit">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => toggleArchive(a)} className="btn-ghost px-2 py-1" title="Archive">
                      <Archive size={14} />
                    </button>
                    <button onClick={() => onDelete(a)} className="btn-ghost px-2 py-1 text-red-600" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <div className="font-display text-3xl italic tabular-nums">
                  {formatCurrency(a.current_balance, a.currency)}
                </div>
                <div className="text-xs text-ink-500 mt-1">
                  {change >= 0 ? '↑' : '↓'} {formatCurrency(Math.abs(change), a.currency)} this month
                </div>
                {a.is_archived && <div className="badge bg-cream-100 text-ink-700 mt-2">Archived</div>}
              </div>
            )
          })}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit account' : 'New account'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button form="account-form" type="submit" className="btn-primary">{editing ? 'Save' : 'Create'}</button>
          </>
        }
      >
        <form id="account-form" onSubmit={onSave} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          <div>
            <label className="label">Name</label>
            <input className="input" required value={form.name} placeholder="e.g. BKT Checking"
              onChange={(e) => setForm({ ...form, name: e.target.value })} autoFocus />
          </div>
          {!editing && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Type</label>
                  <select className="input" value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })}>
                    {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Currency</label>
                  <select className="input" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                    <option value="ALL">ALL (Albanian lek)</option>
                    <option value="EUR">EUR (Euro)</option>
                    <option value="USD">USD (US Dollar)</option>
                    <option value="GBP">GBP (British Pound)</option>
                    <option value="CHF">CHF (Swiss Franc)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Starting balance</label>
                <input type="number" step="0.01" className="input font-mono" placeholder="0.00"
                  value={form.initial_balance}
                  onChange={(e) => setForm({ ...form, initial_balance: e.target.value })} />
              </div>
            </>
          )}
          <div>
            <label className="label">Color</label>
            <div className="flex gap-2">
              {PRESET_COLORS.map((c) => (
                <button key={c} type="button"
                  className={`w-8 h-8 rounded-lg transition-all ${form.color === c ? 'ring-2 ring-offset-2 ring-ink-900' : ''}`}
                  style={{ background: c }}
                  onClick={() => setForm({ ...form, color: c })} />
              ))}
            </div>
          </div>
          <div>
            <label className="label">Notes (optional)</label>
            <textarea className="input" rows={2} value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </form>
      </Modal>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
