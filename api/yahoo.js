/**
 * Vercel Serverless Function — Yahoo Finance API Proxy
 *
 * Proxies requests to Yahoo Finance v8 chart API from the server side,
 * bypassing browser CORS restrictions.
 * Tries multiple Yahoo Finance endpoints with proper auth flow.
 *
 * Usage: GET /api/yahoo?symbol=^IXIC&range=25y
 */

const USER_AGENT =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

// In-memory crumb cache (persists across warm invocations)
let cachedCrumb = null
let cachedCookie = null
let crumbExpiry = 0

/**
 * Obtain a crumb + cookie from Yahoo Finance.
 */
async function refreshCrumb() {
  // Step 1: Visit Yahoo Finance to get consent cookies
  const pageRes = await fetch('https://finance.yahoo.com/quote/%5EGSPC/', {
    headers: {
      'User-Agent': USER_AGENT,
      Accept: 'text/html,application/xhtml+xml'
    },
    redirect: 'follow'
  })
  const rawCookies = pageRes.headers.getSetCookie?.() || []
  let cookieStr = rawCookies.map((c) => c.split(';')[0]).join('; ')

  // If no cookies from page, try fc.yahoo.com
  if (!cookieStr) {
    const fcRes = await fetch('https://fc.yahoo.com/', {
      headers: { 'User-Agent': USER_AGENT },
      redirect: 'manual'
    })
    const fcCookies = fcRes.headers.getSetCookie?.() || []
    cookieStr = fcCookies.map((c) => c.split(';')[0]).join('; ')
  }

  // Step 2: Get crumb
  if (cookieStr) {
    const crumbRes = await fetch(
      'https://query2.finance.yahoo.com/v1/test/getcrumb',
      {
        headers: { 'User-Agent': USER_AGENT, Cookie: cookieStr }
      }
    )
    if (crumbRes.ok) {
      const crumb = await crumbRes.text()
      if (crumb && crumb.length < 50) {
        cachedCrumb = crumb
        cachedCookie = cookieStr
        crumbExpiry = Date.now() + 4 * 60 * 1000
        return { crumb, cookie: cookieStr }
      }
    }
  }

  return null
}

/**
 * Try fetching chart data with a specific base URL, optional crumb/cookie.
 */
async function tryFetch(baseUrl, symbol, range, crumb, cookie) {
  const encoded = encodeURIComponent(symbol)
  let url = `${baseUrl}/${encoded}?range=${encodeURIComponent(range)}&interval=1d&includePrePost=false`
  if (crumb) url += `&crumb=${encodeURIComponent(crumb)}`

  const headers = { 'User-Agent': USER_AGENT }
  if (cookie) headers.Cookie = cookie

  const res = await fetch(url, { headers })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { symbol, range = '25y' } = req.query
  if (!symbol) {
    return res.status(400).json({ error: 'Missing required parameter: symbol' })
  }

  const errors = []

  // Strategy 1: Use cached crumb if available
  if (cachedCrumb && cachedCookie && Date.now() < crumbExpiry) {
    try {
      const data = await tryFetch(
        'https://query1.finance.yahoo.com/v8/finance/chart',
        symbol, range, cachedCrumb, cachedCookie
      )
      res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
      return res.status(200).json(data)
    } catch (e) {
      errors.push(`cached-crumb: ${e.message}`)
      cachedCrumb = null // invalidate
    }
  }

  // Strategy 2: Try query2 without crumb (sometimes works)
  try {
    const data = await tryFetch(
      'https://query2.finance.yahoo.com/v8/finance/chart',
      symbol, range, null, null
    )
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
    return res.status(200).json(data)
  } catch (e) {
    errors.push(`query2-no-crumb: ${e.message}`)
  }

  // Strategy 3: Try query1 without crumb
  try {
    const data = await tryFetch(
      'https://query1.finance.yahoo.com/v8/finance/chart',
      symbol, range, null, null
    )
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
    return res.status(200).json(data)
  } catch (e) {
    errors.push(`query1-no-crumb: ${e.message}`)
  }

  // Strategy 4: Fresh crumb auth flow
  try {
    const auth = await refreshCrumb()
    if (auth) {
      const data = await tryFetch(
        'https://query1.finance.yahoo.com/v8/finance/chart',
        symbol, range, auth.crumb, auth.cookie
      )
      res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
      return res.status(200).json(data)
    }
    errors.push('fresh-crumb: failed to obtain crumb')
  } catch (e) {
    errors.push(`fresh-crumb: ${e.message}`)
  }

  console.error('All Yahoo Finance strategies failed:', errors)
  return res.status(502).json({ error: 'All strategies failed', details: errors })
}
