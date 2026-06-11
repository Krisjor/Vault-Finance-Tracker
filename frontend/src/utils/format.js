/**
 * Currency formatting helpers.
 *
 * Uses the platform Intl.NumberFormat where possible; falls back to a
 * trailing-symbol format for ALL (Albanian lek) which doesn't have a
 * standard symbol position in older browsers.
 */
const SYMBOLS = {
  ALL: 'L',
  EUR: '€',
  USD: '$',
  GBP: '£',
  CHF: 'CHF',
}

const LOCALE_BY_CURRENCY = {
  ALL: 'sq-AL',
  EUR: 'de-DE',
  USD: 'en-US',
  GBP: 'en-GB',
  CHF: 'de-CH',
}

export function formatCurrency(amount, currency = 'ALL', { locale, compact = false } = {}) {
  const value = Number(amount) || 0
  const finalLocale = locale || LOCALE_BY_CURRENCY[currency] || 'en-US'
  try {
    return new Intl.NumberFormat(finalLocale, {
      style: 'currency',
      currency,
      maximumFractionDigits: compact ? 0 : 2,
      notation: compact ? 'compact' : 'standard',
    }).format(value)
  } catch (e) {
    // Fallback for older runtimes / unsupported codes
    const sign = value < 0 ? '-' : ''
    const abs = Math.abs(value).toLocaleString(finalLocale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    const sym = SYMBOLS[currency] || currency
    return `${sign}${abs} ${sym}`
  }
}

export function formatNumber(value, { compact = false, locale = 'en-US' } = {}) {
  if (value == null || isNaN(value)) return '—'
  return new Intl.NumberFormat(locale, {
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value, { decimals = 1 } = {}) {
  if (value == null || isNaN(value)) return '—'
  return `${Number(value).toFixed(decimals)}%`
}
