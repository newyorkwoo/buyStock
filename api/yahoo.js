/**
 * Vercel Serverless Function — Yahoo Finance API Proxy
 *
 * Proxies requests to Yahoo Finance v8 chart API from the server side,
 * bypassing browser CORS restrictions.
 * Handles Yahoo's crumb/cookie authentication flow.
 *
 * Usage: GET /api/yahoo?symbol=^IXIC&range=25y
 */

// Cache crumb + cookie across warm invocations (up to ~5 min)
let cachedCrumb = null
let cachedCookie = null
let crumbExpiry = 0

const USER_AGENT =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

/**
 * Obtain a crumb token + session cookie from Yahoo Finance.
 */
async function getCrumb() {
  const now = Date.now()
  if (cachedCrumb && cachedCookie && now < crumbExpiry) {
    return { crumb: cachedCrumb, cookie: cachedCookie }
  }

  // Step 1: Hit consent page to get session cookies
  const consentRes = await fetch('https://fc.yahoo.com/', {
    headers: { 'User-Agent': USER_AGENT },
    redirect: 'manual'
  })
  // Collect Set-Cookie headers
  const rawCookies = consentRes.headers.getSetCookie?.() || []
  const cookieStr = rawCookies.map((c) => c.split(';')[0]).join('; ')

  // Step 2: Get crumb using the cookies
  const crumbRes = await fetch(
    'https://query2.finance.yahoo.com/v1/test/getcrumb',
    {
      headers: {
        'User-Agent': USER_AGENT,
        Cookie: cookieStr
      }
    }
  )
  if (!crumbRes.ok) {
    throw new Error(`Failed to get crumb: HTTP ${crumbRes.status}`)
  }
  const crumb = await crumbRes.text()

  // Cache for 4 minutes
  cachedCrumb = crumb
  cachedCookie = cookieStr
  crumbExpiry = now + 4 * 60 * 1000

  return { crumb, cookie: cookieStr }
}

export default async function handler(req, res) {
  // Only allow GET
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { symbol, range = '25y' } = req.query

  if (!symbol) {
    return res.status(400).json({ error: 'Missing required parameter: symbol' })
  }

  try {
    const { crumb, cookie } = await getCrumb()

    const encoded = encodeURIComponent(symbol)
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?range=${encodeURIComponent(range)}&interval=1d&includePrePost=false&crumb=${encodeURIComponent(crumb)}`

    const response = await fetch(url, {
      headers: {
        'User-Agent': USER_AGENT,
        Cookie: cookie
      }
    })

    if (!response.ok) {
      // If auth failed, invalidate cache and retry once
      if (response.status === 401 || response.status === 429) {
        cachedCrumb = null
        cachedCookie = null
        crumbExpiry = 0

        const fresh = await getCrumb()
        const retryUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?range=${encodeURIComponent(range)}&interval=1d&includePrePost=false&crumb=${encodeURIComponent(fresh.crumb)}`
        const retryRes = await fetch(retryUrl, {
          headers: {
            'User-Agent': USER_AGENT,
            Cookie: fresh.cookie
          }
        })
        if (!retryRes.ok) {
          return res.status(retryRes.status).json({
            error: `Yahoo Finance returned ${retryRes.status} after retry`
          })
        }
        const retryData = await retryRes.json()
        res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
        return res.status(200).json(retryData)
      }

      return res.status(response.status).json({
        error: `Yahoo Finance returned ${response.status}`
      })
    }

    const data = await response.json()

    // Cache for 5 minutes to reduce Yahoo Finance hits
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
    return res.status(200).json(data)
  } catch (err) {
    console.error('Yahoo Finance proxy error:', err)
    return res.status(502).json({ error: err.message || 'Failed to fetch from Yahoo Finance' })
  }
}
