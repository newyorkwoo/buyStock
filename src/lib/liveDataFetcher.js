/**
 * Live Data Fetcher — fetch latest NASDAQ / VIX data from Yahoo Finance
 * Uses the v8 chart JSON API with CORS proxy fallback.
 *
 * Returns data in the same format as loadCsvOHLC:
 *   [{ date, close, open, high, low }, ...]
 */

const YAHOO_CHART_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart'

const CORS_PROXIES = [
  (url) => url, // try direct first
  (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
  (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`
]

/**
 * Build Yahoo Finance v8 chart URL.
 * @param {string} symbol — e.g. '^IXIC' or '^VIX'
 * @param {string} range — e.g. '25y', '10y', '5y', 'max'
 */
function buildYahooUrl(symbol, range = '25y') {
  const encoded = encodeURIComponent(symbol)
  return `${YAHOO_CHART_BASE}/${encoded}?range=${range}&interval=1d&includePrePost=false`
}

/**
 * Fetch with timeout.
 */
async function fetchWithTimeout(url, timeoutMs = 15000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { signal: controller.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Parse Yahoo Finance v8 chart JSON response into rows.
 * @returns {{ date: string, close: number, open: number|null, high: number|null, low: number|null }[]}
 */
function parseChartResponse(json) {
  const result = json?.chart?.result?.[0]
  if (!result) throw new Error('Yahoo Finance: 無效回應')

  const timestamps = result.timestamp
  const quote = result.indicators?.quote?.[0]
  if (!timestamps || !quote) throw new Error('Yahoo Finance: 缺少資料')

  const rows = []
  for (let i = 0; i < timestamps.length; i++) {
    const close = quote.close?.[i]
    if (close == null || !Number.isFinite(close)) continue

    const d = new Date(timestamps[i] * 1000)
    const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

    rows.push({
      date,
      close,
      open: Number.isFinite(quote.open?.[i]) ? quote.open[i] : null,
      high: Number.isFinite(quote.high?.[i]) ? quote.high[i] : null,
      low: Number.isFinite(quote.low?.[i]) ? quote.low[i] : null
    })
  }

  rows.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
  return rows
}

/**
 * Fetch live data for a symbol, trying multiple CORS strategies.
 * @param {string} symbol
 * @param {string} [range='25y']
 * @returns {Promise<{date:string,close:number,open:number|null,high:number|null,low:number|null}[]>}
 */
async function fetchSymbol(symbol, range = '25y') {
  const baseUrl = buildYahooUrl(symbol, range)
  let lastError = null

  for (const proxyFn of CORS_PROXIES) {
    try {
      const url = proxyFn(baseUrl)
      const json = await fetchWithTimeout(url)
      return parseChartResponse(json)
    } catch (err) {
      lastError = err
    }
  }

  throw new Error(`無法取得 ${symbol} 即時資料: ${lastError?.message || '未知錯誤'}`)
}

/**
 * Fetch latest NASDAQ Composite data.
 * @returns {Promise<Array>}
 */
export async function fetchNasdaq() {
  return fetchSymbol('^IXIC', '25y')
}

/**
 * Fetch latest VIX data.
 * @returns {Promise<Array>}
 */
export async function fetchVix() {
  return fetchSymbol('^VIX', '25y')
}

/**
 * Merge live data on top of existing static CSV data.
 * Live data takes priority for overlapping dates.
 *
 * @param {Array} staticRows — existing rows from CSV
 * @param {Array} liveRows — rows from Yahoo Finance API
 * @returns {Array} merged and sorted
 */
export function mergeRows(staticRows, liveRows) {
  const map = new Map()
  for (const row of staticRows) {
    map.set(row.date.slice(0, 10), row)
  }
  for (const row of liveRows) {
    map.set(row.date.slice(0, 10), row)
  }
  return Array.from(map.values()).sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
}
