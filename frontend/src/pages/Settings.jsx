/**
 * Settings 
 */
import { useState } from 'react'
import { Trash2 } from 'lucide-react'

import PageHeader from '../components/Layout/PageHeader.jsx'
import { Alert, Toast } from '../components/UI/Toast.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { auth } from '../services/api.js'

export default function SettingsPage() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    default_currency: user?.default_currency || 'ALL',
    locale: user?.locale || 'sq-AL',
  })
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' })

  const saveProfile = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const updated = await auth.updateMe(form)
      setUser(updated)
      setToast({ open: true, message: 'Settings saved.', type: 'success' })
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update profile.')
    } finally { setLoading(false) }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await auth.updateMe({ password })
      setPassword('')
      setToast({ open: true, message: 'Password changed.', type: 'success' })
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to change password.')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Tune the tracker to fit you." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Profile + password */}
        <div className="lg:col-span-2 space-y-4">
          <form onSubmit={saveProfile} className="card space-y-4">
            <h2 className="font-display text-2xl italic mb-2">Profile</h2>
            {error && <Alert type="error">{error}</Alert>}
            <div>
              <label className="label">Full name</label>
              <input className="input" value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" value={user?.email || ''} disabled />
              <p className="text-xs text-ink-500 mt-1">
                Email cannot be changed in this version.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Default currency</label>
                <select className="input" value={form.default_currency}
                  onChange={(e) => setForm({ ...form, default_currency: e.target.value })}>
                  <option value="ALL">ALL — Albanian lek</option>
                  <option value="EUR">EUR — Euro</option>
                  <option value="USD">USD — US Dollar</option>
                  <option value="GBP">GBP — British Pound</option>
                  <option value="CHF">CHF — Swiss Franc</option>
                </select>
              </div>
              <div>
                <label className="label">Locale</label>
                <select className="input" value={form.locale}
                  onChange={(e) => setForm({ ...form, locale: e.target.value })}>
                  <option value="sq-AL">Shqip (sq-AL)</option>
                  <option value="en-US">English (en-US)</option>
                  <option value="de-DE">Deutsch (de-DE)</option>
                </select>
              </div>
            </div>
            <div className="pt-2">
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>

          <form onSubmit={changePassword} className="card space-y-4">
            <h2 className="font-display text-2xl italic">Change password</h2>
            <div>
              <label className="label">New password</label>
              <input type="password" minLength={8} className="input"
                value={password} onChange={(e) => setPassword(e.target.value)} />
              <p className="text-xs text-ink-500 mt-1">At least 8 characters and one number.</p>
            </div>
            <div className="flex justify-end">
              <button type="submit" disabled={loading || !password} className="btn-primary">
                {loading ? 'Updating…' : 'Change password'}
              </button>
            </div>
          </form>
        </div>

        {/* About + danger zone */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-display text-xl italic mb-3">About Vault</h3>
            <p className="text-sm text-ink-600 leading-relaxed">
              Vault is a personal finance tracker built around a Flask + React + PostgreSQL stack
              with JWT authentication. This is the production version; all data lives on the server
              backing this deployment.
            </p>
            <div className="mt-3 text-xs text-ink-500">
              Created for thesis defense purposes.
            </div>
          </div>

          <div className="card border-red-200">
            <h3 className="font-display text-xl italic mb-3 text-red-700">Danger zone</h3>
            <p className="text-sm text-ink-600 mb-3">
              Account deletion is not exposed in this version — contact an administrator if you need
              to delete your account and all associated data.
            </p>
            <button
              className="btn-danger w-full justify-center"
              onClick={() => alert('Contact an administrator to delete your account.')}
            >
              <Trash2 size={14} /> Request account deletion
            </button>
          </div>
        </div>
      </div>

      <Toast {...toast} onClose={() => setToast({ ...toast, open: false })} />
    </div>
  )
}
