/**
 * API client.
 *
 * Wraps axios with two concerns:
 *  1. Attach Authorization header from the stored access token.
 *  2. Transparently refresh the access token if the server returns 401 with
 *     an "expired" code — once. If the refresh also fails, tokens are cleared
 *     and the error propagates so the auth layer can redirect to login.
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// --- Token storage ---------------------------------------------------------

const TOKEN_KEY = 'finance_tracker_token'
const REFRESH_KEY = 'finance_tracker_refresh'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: ({ access_token, refresh_token }) => {
    if (access_token) localStorage.setItem(TOKEN_KEY, access_token)
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

// --- Request interceptor ---------------------------------------------------

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Response interceptor: refresh on 401 ---------------------------------

let isRefreshing = false
let refreshQueue = []

const flushQueue = (error, token = null) => {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  refreshQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (
      error.response?.status === 401 &&
      !original._retry &&
      tokenStore.getRefresh() &&
      !original.url.includes('/auth/refresh') &&
      !original.url.includes('/auth/login')
    ) {
      if (isRefreshing) {
        // Wait for the in-flight refresh to finish, then retry
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject })
        })
          .then((token) => {
            original.headers.Authorization = `Bearer ${token}`
            return api(original)
          })
      }

      original._retry = true
      isRefreshing = true
      try {
        const refresh = tokenStore.getRefresh()
        const res = await axios.post(
          `${API_BASE}/auth/refresh`,
          {},
          { headers: { Authorization: `Bearer ${refresh}` } }
        )
        tokenStore.set({ access_token: res.data.access_token })
        flushQueue(null, res.data.access_token)
        original.headers.Authorization = `Bearer ${res.data.access_token}`
        return api(original)
      } catch (err) {
        flushQueue(err, null)
        tokenStore.clear()
        // Force a hard navigation so any in-memory user state is wiped
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// --- Convenience helpers ---------------------------------------------------

export const auth = {
  register: (data) => api.post('/auth/register', data).then((r) => r.data),
  login: (data) => api.post('/auth/login', data).then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
  updateMe: (data) => api.patch('/auth/me', data).then((r) => r.data),
  logout: () => api.post('/auth/logout').then((r) => r.data),
}

export const accounts = {
  list: (params) => api.get('/accounts', { params }).then((r) => r.data),
  get: (id) => api.get(`/accounts/${id}`).then((r) => r.data),
  create: (data) => api.post('/accounts', data).then((r) => r.data),
  update: (id, data) => api.patch(`/accounts/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/accounts/${id}`).then((r) => r.data),
  summary: () => api.get('/accounts/summary').then((r) => r.data),
}

export const categories = {
  list: (params) => api.get('/categories', { params }).then((r) => r.data),
  tree: (params) => api.get('/categories/tree', { params }).then((r) => r.data),
  create: (data) => api.post('/categories', data).then((r) => r.data),
  update: (id, data) => api.patch(`/categories/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/categories/${id}`).then((r) => r.data),
}

export const transactions = {
  list: (params) => api.get('/transactions', { params }).then((r) => r.data),
  get: (id) => api.get(`/transactions/${id}`).then((r) => r.data),
  create: (data) => api.post('/transactions', data).then((r) => r.data),
  update: (id, data) => api.patch(`/transactions/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/transactions/${id}`).then((r) => r.data),
  bulkDelete: (ids) => api.post('/transactions/bulk-delete', { ids }).then((r) => r.data),
}

export const budgets = {
  list: (params) => api.get('/budgets', { params }).then((r) => r.data),
  create: (data) => api.post('/budgets', data).then((r) => r.data),
  update: (id, data) => api.patch(`/budgets/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/budgets/${id}`).then((r) => r.data),
}

export const goals = {
  list: () => api.get('/goals').then((r) => r.data),
  create: (data) => api.post('/goals', data).then((r) => r.data),
  update: (id, data) => api.patch(`/goals/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/goals/${id}`).then((r) => r.data),
  contribute: (id, amount) => api.post(`/goals/${id}/contribute`, { amount }).then((r) => r.data),
}

export const reports = {
  summary: (params) => api.get('/reports/summary', { params }).then((r) => r.data),
  spendingByCategory: (params) => api.get('/reports/spending-by-category', { params }).then((r) => r.data),
  monthlySeries: (params) => api.get('/reports/monthly-series', { params }).then((r) => r.data),
  netWorth: (params) => api.get('/reports/net-worth', { params }).then((r) => r.data),
  topMerchants: (params) => api.get('/reports/top-merchants', { params }).then((r) => r.data),
  dailySpending: (params) => api.get('/reports/daily-spending', { params }).then((r) => r.data),
  exportCsv: (params) => api.get('/reports/export.csv', { params, responseType: 'blob' }),
}

export const imports = {
  preview: (content) => api.post('/imports/csv/preview', { content }).then((r) => r.data),
  upload: (data) => api.post('/imports/csv', data).then((r) => r.data),
}
