/**
 * Categories — view, add, edit, archive user's categories.
 *
 * Visual treatment matches the offline demo: a compact pill-style tab
 * row (expense / income), then a divided list of category items with
 * hover actions. System categories can only be archived.
 */
import { useEffect, useMemo, useState } from 'react'
import { Plus, Pencil, Archive, Trash2 } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import Modal from '../components/UI/Modal.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { categories as catsApi, transactions as txnsApi } from '../services/api.js'

const PRESET_COLORS = [
  '#EF4444', '#F59E0B', '#F97316', '#3B82F6', '#0EA5E9',
  '#EC4899', '#A855F7', '#8B5CF6', '#14B8A6', '#10B981',
  '#22C55E', '#84CC16', '#6366F1', '#06B6D4',
]

const DEFAULT_FORM = () => ({ name: '', category_type: 'expense', color: PRESET_COLORS[0] })

export default function Categories() {
  const [list, setList] = useState([])
  const [tab, setTab] = useState('expense')
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM())
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })
  const [usageById, setUsageById] = useState({})

  const load = () => {
    setLoading(true)
    Promise.all([
      catsApi.list({ include_archived: true }),
      txnsApi.list({ page_size: 1000 }),
    ])
      .then(([cats, tx]) => {
        setList(cats)
        const m = {}
        for (const t of (tx.items || [])) {
          if (t.category_id) m[t.category_id] = (m[t.category_id] || 0) + 1
        }
        setUsageById(m)
      })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const counts = useMemo(() => {
    const c = { expense: 0, income: 0 }
    for (const x of list) c[x.category_type]++
    return c
  }, [list])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...DEFAULT_FORM(), category_type: tab })
    setError(''); setModalOpen(true)
  }
  const openEdit = (c) => {
    setEditing(c)
    setForm({ name: c.name, category_type: c.category_type, color: c.color })
    setError(''); setModalOpen(true)
  }

  const onSave = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (editing) {
        await catsApi.update(editing.id, { name: form.name, color: form.color })
      } else {
        await catsApi.create(form)
      }
      setToast({ open: true, message: 'Category saved.', type: 'success' })
      setModalOpen(false); load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save.')
    }
  }

  const toggleArchive = async (c) => {
    await catsApi.update(c.id, { is_archived: !c.is_archived })
    load()
  }

  const onDelete = async (c) => {
    if (c.is_system) {
      setToast({ open: true, message: 'System categories can only be archived.', type: 'error' })
      return
    }
    const uses = usageById[c.id] || 0
    if (uses > 0) {
      setToast({
        open: true,
        message: `Cannot delete: ${uses} transaction${uses === 1 ? ' uses' : 's use'} this category.`,
        type: 'error',
      })
      return
    }
    if (!confirm(`Delete category "${c.name}"?`)) return
    await catsApi.remove(c.id)
    setToast({ open: true, message: 'Category deleted.', type: 'success' })
    load()
  }

  const visible = list.filter((c) => c.category_type === tab)

  return (
    <div>
      <PageHeader
        title="Categories"
        subtitle={`${list.length} total · ${counts.expense} expense, ${counts.income} income`}
        actions={<button className="btn-primary" onClick={openCreate}><Plus size={14} /> New category</button>}
      />

      <div className="grid grid-cols-2 gap-1 p-1 bg-cream-100 rounded-lg mb-4 max-w-xs">
        {['expense', 'income'].map((t) => (
          <button key={t}
            className={`py-2 rounded-md text-sm font-medium transition-all capitalize ${
              tab === t ? 'bg-white shadow-sm text-ink-900' : 'text-ink-500'
            }`}
            onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-ink-500 text-sm">Loading…</div>
      ) : (
        <div className="card p-0 overflow-hidden">
          {visible.length === 0 ? (
            <div className="py-16 text-center text-ink-500 text-sm">No {tab} categories yet.</div>
          ) : (
            <ul className="divide-y divide-cream-200">
              {visible.map((c) => {
                const uses = usageById[c.id] || 0
                return (
                  <li key={c.id}
                    className={`flex items-center justify-between px-6 py-3 hover:bg-cream-50 transition-colors group ${
                      c.is_archived ? 'opacity-50' : ''
                    }`}>
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-3 h-3 rounded-full shrink-0" style={{ background: c.color }} />
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{c.name}</div>
                        <div className="text-xs text-ink-500">
                          {uses === 0 ? 'Unused' : `${uses} transaction${uses === 1 ? '' : 's'}`}
                          {c.is_system && ' · system'}
                          {c.is_archived && ' · archived'}
                        </div>
                      </div>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                      <button onClick={() => openEdit(c)} className="btn-ghost px-2 py-1">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => toggleArchive(c)} className="btn-ghost px-2 py-1">
                        <Archive size={14} />
                      </button>
                      {!c.is_system && (
                        <button onClick={() => onDelete(c)} className="btn-ghost px-2 py-1 text-red-600">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit category' : 'New category'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button form="cat-form" type="submit" className="btn-primary">{editing ? 'Save' : 'Create'}</button>
          </>
        }
      >
        <form id="cat-form" onSubmit={onSave} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          {!editing && (
            <div className="grid grid-cols-2 gap-1 p-1 bg-cream-100 rounded-lg">
              {['expense', 'income'].map((t) => (
                <button key={t} type="button"
                  className={`py-2 rounded-md text-sm font-medium transition-all capitalize ${
                    form.category_type === t ? 'bg-white shadow-sm text-ink-900' : 'text-ink-500'
                  }`}
                  onClick={() => setForm({ ...form, category_type: t })}>
                  {t}
                </button>
              ))}
            </div>
          )}
          <div>
            <label className="label">Name</label>
            <input required className="input" placeholder="e.g. Subscriptions" value={form.name} autoFocus
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Color</label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map((c) => (
                <button key={c} type="button"
                  className={`w-8 h-8 rounded-lg transition-all ${form.color === c ? 'ring-2 ring-offset-2 ring-ink-900' : ''}`}
                  style={{ background: c }}
                  onClick={() => setForm({ ...form, color: c })} />
              ))}
            </div>
          </div>
        </form>
      </Modal>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
