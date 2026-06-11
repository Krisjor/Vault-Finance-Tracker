/**
 * Date helpers - thin wrappers around date-fns formatters.
 */
import { format, parseISO, startOfMonth, endOfMonth, subDays } from 'date-fns'

export function formatDate(value, fmt = 'PP') {
  if (!value) return ''
  const date = typeof value === 'string' ? parseISO(value) : value
  return format(date, fmt)
}

export function formatShortDate(value) {
  return formatDate(value, 'MMM d')
}

export function toISODate(value) {
  if (!value) return null
  const date = typeof value === 'string' ? parseISO(value) : value
  return format(date, 'yyyy-MM-dd')
}

export function currentMonthRange() {
  const now = new Date()
  return {
    start: toISODate(startOfMonth(now)),
    end: toISODate(endOfMonth(now)),
  }
}

export function lastNDaysRange(n) {
  const now = new Date()
  return {
    start: toISODate(subDays(now, n)),
    end: toISODate(now),
  }
}
