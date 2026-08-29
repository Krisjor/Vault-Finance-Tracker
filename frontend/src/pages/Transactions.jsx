/**
 * Transactions — filterable list with create/edit/delete.
 */
import { useEffect, useMemo, useState } from 'react'
import { Plus, Pencil, Trash2, ArrowUpRight, ArrowDownRight, Check, X } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import Modal from '../components/UI/Modal.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import {
  transactions as txnsApi, accounts as accountsApi,
  categories as categoriesApi,
} from '../services/api.js'
import { formatCurrency } from '../utils/format.js'
import { useAuth } from '../context/AuthContext.jsx'

const today = () => new Date().toISOString().slice(0, 10)

const DEFAULT_FORM = () => ({
  account_id: '', category_id: '', transaction_type: 'expense',
  amount: '', transaction_date: today(), description: '',
  notes: '', tags: '', transfer_account_id: '',
})

function formatLongDate(d) {
  const date = new Date(d)
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function Transactions() {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  const [filters, setFilters] = useState({
    account_id: '', category_id: '', type: '', search: '',
  })

  const [accountList, setAccountList] = useState([])
  const [categoryList, setCategoryList] = useState([])

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM())
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  useEffect(() => {
    Promise.all([accountsApi.list(), categoriesApi.list()])
      .then(([a, c]) => { setAccountList(a); setCategoryList(c) })
  }, [])

  const load = () => {
    setLoading(true)
    const params = { page, page_size: 200 }
    Object.entries(filters).forEach(([k, v]) => v && (params[k] = v))
    txnsApi.list(params)
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() /* eslint-disable-next-line */ }, [filters, page])

  const accountById = useMemo(
    () => Object.fromEntries(accountList.map((a) => [a.id, a])),
    [accountList],
  )
  const categoryById = useMemo(
    () => Object.fromEntries(categoryList.map((c) => [c.id, c])),
    [categoryList],
  )

  // Group items by transaction_date for the demo-style day-banner layout.
  const groupedByDate = useMemo(() => {
    const groups = {}
    for (const t of items) {
      (groups[t.transaction_date] ||= []).push(t)
    }
    return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
  }, [items])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...DEFAULT_FORM(), account_id: accountList[0]?.id || '' })
    setError(''); setModalOpen(true)
  }

  const openEdit = (t) => {
    setEditing(t)
    setForm({
      account_id: t.account_id, category_id: t.category_id || '',
      transaction_type: t.transaction_type, amount: t.amount,
      transaction_date: t.transaction_date, description: t.description || '',
      notes: t.notes || '', tags: t.tags?.map((tg) => tg.name).join(', ') || '',
      transfer_account_id: t.transfer_account_id || '',
    })
    setError(''); setModalOpen(true)
  }

  const onSave = async (e) => {
    e.preventDefault()
    setError('')
    const payload = {
      ...form,
      account_id: Number(form.account_id),
      category_id: form.category_id ? Number(form.category_id) : null,
      amount: Number(form.amount),
      tags: form.tags ? form.tags.split(',').map((s) => s.trim()).filter(Boolean) : [],
    }
    if (form.transaction_type === 'transfer') {
      payload.transfer_account_id = Number(form.transfer_account_id)
      delete payload.category_id
    }
    try {
      if (editing) {
        await txnsApi.update(editing.id, {
          amount: payload.amount, category_id: payload.category_id,
          transaction_date: payload.transaction_date,
          description: payload.description, notes: payload.notes,
          tags: payload.tags,
        })
        setToast({ open: true, message: 'Transaction updated.', type: 'success' })
      } else {
        await txnsApi.create(payload)
        setToast({ open: true, message: 'Transaction added.', type: 'success' })
      }
      setModalOpen(false); load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save.')
    }
  }

  const onDelete = async (t) => {
    if (!confirm('Delete this transaction?')) return
    await txnsApi.remove(t.id)
    setToast({ open: true, message: 'Transaction deleted.', type: 'success' })
    load()
  }

  const filteredCategories = categoryList.filter(
    (c) => c.category_type === form.transaction_type && !c.is_archived,
  )

  const cur = user?.default_currency || 'ALL'

  return (
    <div>
      <PageHeader
        title="Transactions"
        subtitle={`${items.length} of ${total.toLocaleString()} entries`}
        actions={<button className="btn-primary" onClick={openCreate}><Plus size={14} /> New transaction</button>}
      />

      {/* Filters */}
      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="md:col-span-2">
            <label className="label">Search</label>
            <input className="input" placeholder="Description…"
              value={filters.search}
              onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setPage(1) }} />
          </div>
          <div>
            <label className="label">Account</label>
            <select className="input" value={filters.account_id}
              onChange={(e) => { setFilters({ ...filters, account_id: e.target.value }); setPage(1) }}>
              <option value="">All accounts</option>
              {accountList.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Category</label>
            <select className="input" value={filters.category_id}
              onChange={(e) => { setFilters({ ...filters, category_id: e.target.value }); setPage(1) }}>
              <option value="">All categories</option>
              {categoryList.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Type</label>
            <select className="input" value={filters.type}
              onChange={(e) => { setFilters({ ...filters, type: e.target.value }); setPage(1) }}>
              <option value="">All</option>
              <option value="income">Income</option>
              <option value="expense">Expense</option>
              <option value="transfer">Transfer</option>
            </select>
          </div>
        </div>
      </div>

      {/* List */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="py-24 text-center text-ink-500 text-sm">Loading…</div>
        ) : groupedByDate.length === 0 ? (
          <div className="py-24 text-center text-ink-500 text-sm">
            No transactions match your filters.
          </div>
        ) : (
          groupedByDate.map(([date, dayItems]) => {
            const dayTotal = dayItems.reduce(
              (s, t) => s + (t.transaction_type === 'income' ? Number(t.amount) : -Number(t.amount)),
              0,
            )
            return (
              <div key={date}>
                <div className="flex items-center justify-between px-6 py-3 bg-cream-50 border-y border-cream-200">
                  <div className="flex items-baseline gap-3">
                    <span className="font-display text-lg italic">{formatLongDate(date)}</span>
                    <span className="text-xs text-ink-500">
                      {dayItems.length} {dayItems.length === 1 ? 'entry' : 'entries'}
                    </span>
                  </div>
                  <span className={`tabular-nums text-sm font-medium ${
                    dayTotal >= 0 ? 'text-emerald-600' : 'text-ink-900'
                  }`}>
                    {dayTotal >= 0 ? '+' : ''}{formatCurrency(dayTotal, cur)}
                  </span>
                </div>
                <ul>
                  {dayItems.map((t) => {
                    const cat = t.category_id ? categoryById[t.category_id] : null
                    const acc = accountById[t.account_id]
                    const color = cat?.color || '#94a3b8'
                    const isIncome = t.transaction_type === 'income'
                    return (
                      <li key={t.id}
                        className="flex items-center justify-between px-6 py-3 hover:bg-cream-50 transition-colors group">
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <div className="w-9 h-9 rounded-full grid place-items-center shrink-0"
                            style={{ background: color + '20', color }}>
                            {isIncome ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-medium truncate">
                              {t.description || cat?.name || 'Transaction'}
                            </div>
                            <div className="text-xs text-ink-500 truncate">
                              {cat?.name || 'Uncategorized'}{acc ? ` · ${acc.name}` : ''}
                              {t.tags?.length > 0 && (
                                <span className="ml-2">
                                  {t.tags.map((tg) => (
                                    <span key={tg.id} className="badge bg-cream-100 text-ink-700 mr-1">#{tg.name}</span>
                                  ))}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 shrink-0">
                          <span className={`tabular-nums text-sm font-medium ${
                            isIncome ? 'text-emerald-600' : 'text-ink-900'
                          }`}>
                            {isIncome ? '+' : '−'}{formatCurrency(t.amount, t.currency)}
                          </span>
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                            <button onClick={() => openEdit(t)} className="btn-ghost px-2 py-1">
                              <Pencil size={14} />
                            </button>
                            <button onClick={() => onDelete(t)} className="btn-ghost px-2 py-1 text-red-600">
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })
        )}
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit transaction' : 'New transaction'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button form="txn-form" type="submit" className="btn-primary">
              <Check size={14} /> {editing ? 'Save changes' : 'Add transaction'}
            </button>
          </>
        }
      >
        <form id="txn-form" onSubmit={onSave} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}

          {!editing && (
            <div className="grid grid-cols-2 gap-1 p-1 bg-cream-100 rounded-lg">
              {['expense', 'income'].map((t) => (
                <button key={t} type="button"
                  onClick={() => setForm({ ...form, transaction_type: t, category_id: '' })}
                  className={`py-2 rounded-md text-sm font-medium transition-all capitalize ${
                    form.transaction_type === t
                      ? 'bg-white shadow-sm text-ink-900'
                      : 'text-ink-500'
                  }`}>
                  {t}
                </button>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Amount</label>
              <input type="number" step="0.01" required className="input font-mono"
                placeholder="0.00" value={form.amount} autoFocus
                onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Date</label>
              <input type="date" required className="input" value={form.transaction_date}
                onChange={(e) => setForm({ ...form, transaction_date: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="label">Account</label>
            <select required className="input" value={form.account_id}
              onChange={(e) => setForm({ ...form, account_id: e.target.value })}>
              <option value="">Select an account</option>
              {accountList.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
            </select>
          </div>

          <div>
            <label className="label">Category</label>
            <select className="input" value={form.category_id}
              onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
              <option value="">— Choose a category —</option>
              {filteredCategories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          <div>
            <label className="label">Description</label>
            <input className="input" placeholder="What was this for?" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>

          <div>
            <label className="label">Tags <span className="text-ink-400 font-normal">(comma-separated)</span></label>
            <input className="input" placeholder="vacation, work" value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })} />
          </div>

          <div>
            <label className="label">Notes</label>
            <textarea rows={2} className="input" value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </form>
      </Modal>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
