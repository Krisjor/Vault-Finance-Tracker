/**
 * Sidebar — fixed-width navigation rail.
 */
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Wallet, ArrowLeftRight, Target,
  PieChart, Tags, Upload, Settings, LogOut, Sparkles,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext.jsx'

const NAV = [
  { to: '/',             label: 'Dashboard',    icon: LayoutDashboard },
  { to: '/accounts',     label: 'Accounts',     icon: Wallet },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/budgets',      label: 'Budgets',      icon: PieChart },
  { to: '/goals',        label: 'Goals',        icon: Target },
  { to: '/reports',      label: 'Reports',      icon: Sparkles },
  { to: '/categories',   label: 'Categories',   icon: Tags },
  { to: '/import',       label: 'Import',       icon: Upload },
  { to: '/settings',     label: 'Settings',     icon: Settings },
]


function VaultMark() {
  return (
    <div className="w-8 h-8 rounded-lg bg-ink-900 grid place-items-center shrink-0">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
           stroke="#F59E0B" strokeWidth="2" strokeLinecap="round">
        <path d="M6 16V8h3.5a3 3 0 010 6H8m0-3h3.5a3 3 0 010 6H6" />
        <path d="M14.5 6v12M11 8.5h7M11 11.5h7" />
      </svg>
    </div>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 border-r border-cream-200 bg-cream-50 flex flex-col">
      {/* Brand */}
      <div className="px-6 py-7">
        <div className="flex items-center gap-2.5">
          <VaultMark />
          <div className="min-w-0">
            <div className="font-display text-xl italic leading-none text-ink-900">Vault</div>
            <div className="text-[10px] uppercase tracking-widest text-ink-500 mt-0.5">
              Finance Tracker
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 pt-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `navlink ${isActive ? 'active' : ''}`}
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User chip */}
      <div className="p-3">
        <div className="card-tight">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-ember-400 text-ink-900 grid place-items-center text-sm font-semibold shrink-0">
              {user?.full_name?.[0]?.toUpperCase()
                ?? user?.email?.[0]?.toUpperCase()
                ?? '?'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user?.full_name}</div>
              <div className="text-xs text-ink-500 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="btn-ghost w-full justify-center text-xs py-1.5"
            title="Log out"
          >
            <LogOut size={14} />
            <span>Log out</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
