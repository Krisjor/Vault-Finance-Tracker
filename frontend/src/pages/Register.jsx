import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Alert } from '../components/UI/Toast.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: '', email: '', password: '', default_currency: 'ALL',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onChange = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.message || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-cream-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2.5 mb-4">
            <div className="w-10 h-10 rounded-xl bg-ink-900 grid place-items-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                   stroke="#F59E0B" strokeWidth="2" strokeLinecap="round">
                <path d="M6 16V8h3.5a3 3 0 010 6H8m0-3h3.5a3 3 0 010 6H6" />
                <path d="M14.5 6v12M11 8.5h7M11 11.5h7" />
              </svg>
            </div>
          </div>
          <h1 className="font-display text-4xl italic tracking-tight text-ink-900">Create your account</h1>
          <p className="text-ink-500 mt-2 text-sm">Start tracking your finances in under a minute.</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4">
          {error && <Alert type="error">{error}</Alert>}

          <div>
            <label className="label">Full name</label>
            <input className="input" required value={form.full_name} onChange={onChange('full_name')} />
          </div>

          <div>
            <label className="label">Email</label>
            <input type="email" className="input" required value={form.email} onChange={onChange('email')} />
          </div>

          <div>
            <label className="label">Password</label>
            <input type="password" className="input" required minLength={8}
                   value={form.password} onChange={onChange('password')} />
            <p className="text-xs text-ink-500 mt-1">At least 8 characters and one number.</p>
          </div>

          <div>
            <label className="label">Default currency</label>
            <select className="input" value={form.default_currency} onChange={onChange('default_currency')}>
              <option value="ALL">ALL — Albanian lek</option>
              <option value="EUR">EUR — Euro</option>
              <option value="USD">USD — US Dollar</option>
              <option value="GBP">GBP — Pound Sterling</option>
              <option value="CHF">CHF — Swiss Franc</option>
            </select>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-ink-500 mt-6">
          Already have an account?{' '}
          <Link to="/login"
                className="text-ink-900 font-medium underline underline-offset-4 decoration-ember-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
