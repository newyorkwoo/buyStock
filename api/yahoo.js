/**
 * Vercel Serverless Function — Yahoo Finance API Proxy
 *
 * Proxies requests to Yahoo Finance v8 chart API from the server side,
 * bypassing browser CORS restrictions.
 *
 * Usage: GET /api/yahoo?symbol=^IXIC&range=25y
 */

export default async function handler(req, res) {
  // Only allow GET
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { symbol, range = '25y' } = req.query

  if (!symbol) {
    return res.status(400).json({ error: 'Missing required parameter: symbol' })
  }

  const encoded = encodeURIComponent(symbol)
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?range=${range}&interval=1d&includePrePost=false`

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
    })

    if (!response.ok) {
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
