/**
 * Dashboard — landing page after login.
 *
 * Pulls the /reports/summary aggregate payload and lays out:
 *   - top stat cards (income / expense / net / avg daily spend)
 *   - monthly trend bar chart
 *   - spending-by-category donut
 *   - account summaries + recent transactions feed
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, PieChart, Pie, Cell,
} from 'recharts'
import { ArrowUpRight, ArrowDownRight, ArrowRight, Plus } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import { reports, transactions, accounts, categories } from '../services/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { formatCurrency, formatNumber } from '../utils/format.js'

export default function Dashboard() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [recent, setRecent] = useState([])
  const [accountList, setAccountList] = useState([])
  const [categoryList, setCategoryList] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      reports.summary(),
      transactions.list({ page_size: 6 }),
      accounts.list(),
      categories.list(),
    ])
      .then(([s, t, a, c]) => {
        setSummary(s)
        setRecent(t.items || [])
        setAccountList(a)
        setCategoryList(c)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const accountById = useMemo(
    () => Object.fromEntries(accountList.map((a) => [a.id, a])),
    [accountList],
  )
  const categoryById = useMemo(
    () => Object.fromEntries(categoryList.map((c) => [c.id, c])),
    [categoryList],
  )

  if (loading || !summary) {
    return <div className="text-ink-500 text-sm">Loading dashboard…</div>
  }

  const cur = user?.default_currency || 'ALL'
  const totalIncome  = summary.totals.income_by_currency[cur]  || 0
  const totalExpense = summary.totals.expense_by_currency[cur] || 0
  const net = totalIncome - totalExpense
  const dailyAvg = summary.average_daily_spend?.average_daily_spend || 0
  const daysObserved = summary.average_daily_spend?.days_observed || 30
  const firstName = (user?.full_name || 'there').split(' ')[0]

  return (
    <div>
      <PageHeader
        title={`Hello, ${firstName}.`}
        subtitle="Your last 30 days, condensed."
        actions={
          <>
            <span className="demo-pill">
              <span className="demo-pill-dot" />
              Vault
            </span>
            <Link to="/transactions" className="btn-primary">
              <Plus size={14} /> New transaction
            </Link>
          </>
        }
      />

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Income (30d)"
          value={formatCurrency(totalIncome, cur)}
          hint={
            <span className="text-emerald-600 inline-flex items-center gap-1">
              <ArrowUpRight size={12} /> 30 day window
            </span>
          }
        />
        <StatCard
          label="Spent (30d)"
          value={formatCurrency(totalExpense, cur)}
          hint={
            <span className="text-red-600 inline-flex items-center gap-1">
              <ArrowDownRight size={12} /> 30 day window
            </span>
          }
        />
        <StatCard
          label="Net (30d)"
          value={formatCurrency(net, cur)}
          hint={
            <span className={net >= 0 ? 'text-emerald-600' : 'text-red-600'}>
              {net >= 0 ? 'In the black' : 'Running negative'}
            </span>
          }
        />
        <StatCard
          label="Daily Spend Avg."
          value={formatCurrency(dailyAvg, cur)}
          hint={<span className="text-ink-500">Past {daysObserved} days</span>}
        />
      </div>

      {/* Trend bar chart + Where it went donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="card lg:col-span-2">
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="font-display text-2xl italic">Income &amp; expenses</h2>
            <span className="stat-label">Last 12 months</span>
          </div>
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={summary.monthly_series} margin={{ top: 10, right: 8, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDE6D3" vertical={false} />
                <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={11}
                  tickFormatter={(v) => formatNumber(v, { compact: true })} />
                <Tooltip
                  formatter={(v) => formatCurrency(v, cur)}
                  contentStyle={{ borderRadius: 10, border: '1px solid #EDE6D3', background: '#fff' }}
                />
                <Bar dataKey="income"  name="Income"  fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="expense" name="Expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-display text-2xl italic">Where it went</h2>
          </div>
          {summary.spending_by_category.length === 0 ? (
            <div className="text-sm text-ink-500 py-12 text-center">
              Nothing logged this period yet.
            </div>
          ) : (
            <>
              <div className="h-44">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={summary.spending_by_category.slice(0, 6)}
                      dataKey="total" nameKey="category_name"
                      innerRadius={48} outerRadius={75} paddingAngle={2}
                    >
                      {summary.spending_by_category.slice(0, 6).map((entry, i) => (
                        <Cell key={i} fill={entry.color || '#94a3b8'} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v) => formatCurrency(v, cur)}
                      contentStyle={{ borderRadius: 10, border: '1px solid #EDE6D3', background: '#fff' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-2 space-y-1.5 text-sm">
                {summary.spending_by_category.slice(0, 5).map((c) => (
                  <li key={c.category_id} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 truncate">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: c.color }} />
                      <span className="truncate">{c.category_name}</span>
                    </span>
                    <span className="font-mono text-xs text-ink-600 tabular-nums">
                      {c.percent.toFixed(0)}%
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Accounts + Recent transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card">
          <h2 className="font-display text-2xl italic mb-4">Your accounts</h2>
          {accountList.length === 0 ? (
            <Link to="/accounts" className="btn-secondary w-full">+ Add an account</Link>
          ) : (
            <ul className="space-y-3">
              {accountList.slice(0, 5).map((a) => (
                <li key={a.id} className="flex items-center justify-between">
                  <span className="flex items-center gap-3 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: a.color }} />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium truncate">{a.name}</span>
                      <span className="block text-xs text-ink-500 capitalize">
                        {a.account_type?.replace('_', ' ')}
                      </span>
                    </span>
                  </span>
                  <span className="tabular-nums font-medium text-sm">
                    {formatCurrency(a.current_balance, a.currency)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/accounts" className="btn-ghost w-full justify-center mt-4 text-sm">
            Manage accounts <ArrowRight size={14} />
          </Link>
        </div>

        <div className="card lg:col-span-2">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-display text-2xl italic">Recent activity</h2>
            <Link to="/transactions" className="text-sm text-ink-500 hover:text-ink-900">View all →</Link>
          </div>
          {recent.length === 0 ? (
            <p className="text-sm text-ink-500 py-6 text-center">No transactions yet.</p>
          ) : (
            <ul className="divide-y divide-cream-200">
              {recent.map((t) => {
                const cat = t.category_id ? categoryById[t.category_id] : null
                const acc = accountById[t.account_id]
                const color = cat?.color || '#94a3b8'
                const isIncome = t.transaction_type === 'income'
                return (
                  <li key={t.id} className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full grid place-items-center shrink-0"
                        style={{ background: color + '20', color }}>
                        {isIncome ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">
                          {t.description || cat?.name || 'Transaction'}
                        </div>
                        <div className="text-xs text-ink-500 truncate">
                          {t.transaction_date}{acc ? ` · ${acc.name}` : ''}
                        </div>
                      </div>
                    </div>
                    <div className={`tabular-nums text-sm font-medium ${
                      isIncome ? 'text-emerald-600' : 'text-ink-900'
                    }`}>
                      {isIncome ? '+' : '−'}{formatCurrency(t.amount, t.currency)}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, hint }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value mt-3">{value}</div>
      {hint && <div className="text-xs mt-2">{hint}</div>}
    </div>
  )
}
