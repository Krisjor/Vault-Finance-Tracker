/**
 * Reports — multi-chart analytics view with date range, CSV export.
 */
import { useEffect, useState } from 'react'
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, LineChart, Line,
} from 'recharts'
import { Download } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import { reports } from '../services/api.js'
import { formatCurrency, formatNumber } from '../utils/format.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Reports() {
  const { user } = useAuth()
  const [range, setRange] = useState('30')

  const [spending, setSpending] = useState([])
  const [netWorth, setNetWorth] = useState([])
  const [daily, setDaily] = useState([])
  const [merchants, setMerchants] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10)
    const startDate = new Date(Date.now() - Number(range) * 86400000).toISOString().slice(0, 10)
    const params = { start_date: startDate, end_date: today }

    setLoading(true)
    Promise.all([
      reports.spendingByCategory(params),
      reports.netWorth({ months: 12 }),
      reports.dailySpending(params),
      reports.topMerchants(params),
    ])
      .then(([s, n, d, mer]) => {
        setSpending(s); setNetWorth(n); setDaily(d); setMerchants(mer)
      })
      .finally(() => setLoading(false))
  }, [range])

  const downloadCsv = async () => {
    const today = new Date().toISOString().slice(0, 10)
    const startDate = new Date(Date.now() - Number(range) * 86400000).toISOString().slice(0, 10)
    const res = await reports.exportCsv({ start_date: startDate, end_date: today })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url; a.download = `transactions_${startDate}_to_${today}.csv`
    a.click(); URL.revokeObjectURL(url)
  }

  const cur = user?.default_currency || 'ALL'
  const maxMerchant = merchants[0]?.total || 1

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Patterns the spreadsheet wouldn’t show you."
        actions={
          <>
            <select className="input" style={{ width: 'auto' }}
              value={range} onChange={(e) => setRange(e.target.value)}>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
              <option value="365">Last year</option>
            </select>
            <button className="btn-secondary" onClick={downloadCsv}>
              <Download size={14} /> Export CSV
            </button>
          </>
        }
      />

      {loading ? (
        <div className="text-ink-500 text-sm">Loading reports…</div>
      ) : (
        <>
          {/* Row 1: daily spending + net worth */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <div className="card">
              <h2 className="font-display text-2xl italic mb-4">Daily spending</h2>
              <div className="h-72">
                <ResponsiveContainer>
                  <AreaChart data={daily}>
                    <defs>
                      <linearGradient id="dailyGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#EDE6D3" vertical={false} />
                    <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false}
                      fontSize={10} interval="preserveStartEnd" />
                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={10}
                      tickFormatter={(v) => formatNumber(v, { compact: true })} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid #EDE6D3', background: '#fff' }}
                      formatter={(v) => formatCurrency(v, cur)} />
                    <Area type="monotone" dataKey="total" stroke="#F59E0B"
                      strokeWidth={2} fill="url(#dailyGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <h2 className="font-display text-2xl italic mb-4">Net worth trajectory</h2>
              <div className="h-72">
                <ResponsiveContainer>
                  <LineChart data={netWorth}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#EDE6D3" vertical={false} />
                    <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={10} />
                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={10}
                      tickFormatter={(v) => formatNumber(v, { compact: true })} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid #EDE6D3', background: '#fff' }}
                      formatter={(v) => formatCurrency(v, cur)} />
                    <Line type="monotone" dataKey="net_worth" stroke="#0f172a" strokeWidth={2.5}
                      dot={{ fill: '#0f172a', r: 3 }} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Row 2: by category + top merchants */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <h2 className="font-display text-2xl italic mb-4">By category</h2>
              {spending.length === 0 ? (
                <div className="text-sm text-ink-500 py-12 text-center">No data in this range.</div>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={spending.slice(0, 8)} layout="vertical" margin={{ left: 30 }}>
                      <XAxis type="number" stroke="#94a3b8" tickLine={false} axisLine={false}
                        fontSize={10} tickFormatter={(v) => formatNumber(v, { compact: true })} />
                      <YAxis type="category" dataKey="category_name" stroke="#94a3b8"
                        tickLine={false} axisLine={false} fontSize={11} width={90} />
                      <Tooltip
                        contentStyle={{ borderRadius: 10, border: '1px solid #EDE6D3', background: '#fff' }}
                        formatter={(v) => formatCurrency(v, cur)} />
                      <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                        {spending.slice(0, 8).map((c, i) => (
                          <Cell key={i} fill={c.color || '#94a3b8'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="card">
              <h2 className="font-display text-2xl italic mb-4">Top spending places</h2>
              {merchants.length === 0 ? (
                <div className="text-sm text-ink-500 py-12 text-center">No data in this range.</div>
              ) : (
                <ul className="space-y-2">
                  {merchants.slice(0, 8).map((m, i) => (
                    <li key={i} className="flex items-center gap-3">
                      <span className="font-mono text-xs text-ink-500 w-6 tabular-nums text-right">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="truncate font-medium">{m.description}</span>
                          <span className="tabular-nums shrink-0 ml-2">{formatCurrency(m.total, cur)}</span>
                        </div>
                        <div className="h-1.5 bg-cream-100 rounded-full overflow-hidden">
                          <div className="h-full bg-ink-900"
                            style={{ width: `${(m.total / maxMerchant) * 100}%` }} />
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
