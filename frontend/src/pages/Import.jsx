/**
 * Import — upload a bank CSV, map columns, import into a destination account.
 *
 * Visual treatment matches the offline demo: large "Drop your CSV here"
 * empty-state card, then a Step 2 mapping card with preview table on the
 * left and an "How importing works" aside on the right.
 */
import { useEffect, useState } from 'react'
import { Upload, Check } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { imports, accounts as accountsApi } from '../services/api.js'

export default function ImportPage() {
  const [content, setContent] = useState('')
  const [preview, setPreview] = useState(null)
  const [accountList, setAccountList] = useState([])
  const [mapping, setMapping] = useState({
    date_col: '', amount_col: '', description_col: '',
    amount_sign: 'negative_is_expense',
  })
  const [accountId, setAccountId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  useEffect(() => { accountsApi.list().then(setAccountList) }, [])

  // Auto-detect column mappings when preview arrives.
  useEffect(() => {
    if (!preview?.headers) return
    const guess = {}
    for (const h of preview.headers) {
      const lc = h.toLowerCase()
      if (!guess.date_col        && /date|datum/.test(lc))                        guess.date_col = h
      if (!guess.amount_col      && /amount|sum|value|debit|credit/.test(lc))     guess.amount_col = h
      if (!guess.description_col && /desc|name|memo|narration|reference/.test(lc)) guess.description_col = h
    }
    setMapping((m) => ({ ...m, ...guess }))
  }, [preview])

  const onFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setContent(text)
    setError('')
    setLoading(true)
    try {
      const p = await imports.preview(text)
      setPreview(p)
    } catch {
      setError('Could not parse the file as CSV.')
    } finally {
      setLoading(false)
    }
  }

  const onImport = async (e) => {
    e.preventDefault()
    setError('')
    if (!accountId) { setError('Pick a destination account.'); return }
    if (!mapping.date_col || !mapping.amount_col) {
      setError('Map at least the Date and Amount columns.'); return
    }
    setLoading(true)
    try {
      const res = await imports.upload({
        content, account_id: Number(accountId), mapping,
      })
      setResult(res)
      setToast({ open: true, message: `${res.inserted} transactions imported.`, type: 'success' })
    } catch (err) {
      setError(err.response?.data?.message || 'Import failed.')
    } finally {
      setLoading(false)
    }
  }

  const startOver = () => { setPreview(null); setContent(''); setResult(null) }

  const isHighlighted = (h) =>
    h === mapping.date_col || h === mapping.amount_col || h === mapping.description_col

  return (
    <div>
      <PageHeader title="Import CSV" subtitle="Bring statements in from your bank." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          {/* Step 1 — pick a file */}
          {!preview && !result && (
            <div className="card text-center py-16">
              <p className="font-display text-3xl italic text-ink-900 mb-2">Drop your CSV here</p>
              <p className="text-sm text-ink-500 mb-6 max-w-md mx-auto">
                We support most Albanian bank statement exports (BKT, Raiffeisen, Credins, Tirana Bank) and any generic CSV.
              </p>
              <label className="btn-primary inline-flex cursor-pointer">
                <Upload size={14} /> Choose file…
                <input type="file" accept=".csv,text/csv" hidden onChange={onFile} />
              </label>
              {error && <div className="mt-4 max-w-md mx-auto"><Alert type="error">{error}</Alert></div>}
            </div>
          )}

          {/* Step 2 — map columns */}
          {preview && !result && (
            <form onSubmit={onImport} className="card">
              <div className="mb-5">
                <div className="text-xs text-ink-500 mb-1">Step 2 of 2</div>
                <h2 className="font-display text-2xl italic">Map your columns</h2>
              </div>
              {error && <div className="mb-4"><Alert type="error">{error}</Alert></div>}

              <div className="grid grid-cols-3 gap-3 mb-5">
                <div>
                  <label className="label">Date column</label>
                  <select className="input" value={mapping.date_col}
                    onChange={(e) => setMapping({ ...mapping, date_col: e.target.value })}>
                    <option value="">— pick —</option>
                    {preview.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Amount column</label>
                  <select className="input" value={mapping.amount_col}
                    onChange={(e) => setMapping({ ...mapping, amount_col: e.target.value })}>
                    <option value="">— pick —</option>
                    {preview.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Description (optional)</label>
                  <select className="input" value={mapping.description_col}
                    onChange={(e) => setMapping({ ...mapping, description_col: e.target.value })}>
                    <option value="">— none —</option>
                    {preview.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
              </div>

              <div className="mb-5">
                <label className="label">Import into account</label>
                <select className="input" value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}>
                  <option value="">Select an account</option>
                  {accountList.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="text-xs uppercase tracking-wider text-ink-500 mb-2">
                Preview (first 5 rows)
              </div>
              <div className="overflow-auto rounded-lg border border-cream-200">
                <table className="text-xs w-full">
                  <thead className="bg-cream-50">
                    <tr>
                      {preview.headers.map((h) => (
                        <th key={h}
                          className={`text-left p-2 font-medium ${
                            isHighlighted(h) ? 'bg-amber-100 text-amber-900' : 'text-ink-700'
                          }`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.slice(0, 5).map((r, i) => (
                      <tr key={i} className="border-t border-cream-200">
                        {r.map((c, j) => (
                          <td key={j} className="p-2 text-ink-700 font-mono">{c}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between mt-5">
                <button type="button" className="btn-secondary" onClick={startOver}>← Start over</button>
                <button type="submit" disabled={loading} className="btn-primary">
                  {loading ? 'Importing…' : `Import ${preview.total_rows || preview.rows?.length || ''} rows →`}
                </button>
              </div>
            </form>
          )}

          {/* Step 3 — success */}
          {result && (
            <div className="card text-center py-16">
              <div className="w-16 h-16 rounded-full grid place-items-center mx-auto mb-4"
                style={{ background: 'rgba(16,185,129,0.2)' }}>
                <Check size={28} className="text-emerald-600" />
              </div>
              <p className="font-display text-3xl italic">Imported.</p>
              <p className="text-sm text-ink-500 mt-2">
                <span className="font-medium text-ink-900">{result.inserted}</span> transactions added
                {result.skipped_duplicates > 0 && <> · {result.skipped_duplicates} duplicates skipped</>}.
              </p>
              <button className="btn-primary mt-6" onClick={startOver}>Import another file</button>
            </div>
          )}
        </div>

        {/* "How importing works" aside */}
        <aside className="card">
          <h3 className="font-display text-xl italic mb-3">How importing works</h3>
          <ol className="text-sm space-y-3 text-ink-700">
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-cream-100 grid place-items-center font-medium text-xs shrink-0">1</span>
              <span>Upload a CSV exported from your bank.</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-cream-100 grid place-items-center font-medium text-xs shrink-0">2</span>
              <span>We auto-detect the date and amount columns, but you can override.</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-cream-100 grid place-items-center font-medium text-xs shrink-0">3</span>
              <span>Negative amounts become expenses, positive become income.</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-cream-100 grid place-items-center font-medium text-xs shrink-0">4</span>
              <span>Re-importing the same file is safe — duplicates are detected by content hash.</span>
            </li>
          </ol>
          <div className="mt-5 p-3 rounded-lg bg-cream-50 text-xs text-ink-600">
            <strong>Tip:</strong> EU date formats (DD/MM/YYYY) and EU number formats (1.234,56) are both supported.
          </div>
        </aside>
      </div>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
