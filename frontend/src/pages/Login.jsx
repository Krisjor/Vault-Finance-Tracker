import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Alert } from '../components/UI/Toast.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-cream-50 px-4">
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
          <h1 className="font-display text-4xl italic tracking-tight text-ink-900">Welcome back</h1>
          <p className="text-ink-500 mt-2 text-sm">Sign in to your Vault account.</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4">
          {error && <Alert type="error">{error}</Alert>}

          <div>
            <label className="label">Email</label>
            <input
              type="email" required autoFocus
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="demo@example.com"
            />
          </div>

          <div>
            <label className="label">Password</label>
            <input
              type="password" required
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-ink-500 mt-6">
          Don't have an account?{' '}
          <Link to="/register"
                className="text-ink-900 font-medium underline underline-offset-4 decoration-ember-400">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
