import Papa from 'papaparse'

function parseNumber(input) {
  const value = Number(input)
  return Number.isFinite(value) ? value : null
}

function normalizeColumns(rawRows) {
  if (!rawRows.length) return []

  const firstRow = rawRows[0]
  if (firstRow[0] === 'Date' || firstRow[0] === 'date') {
    return rawRows
  }

  // yfinance multi-header: row0=Price/col names, row1=Ticker, row2=Date header
  if (firstRow[0] === 'Price' && rawRows.length >= 3) {
    const mergedHeader = firstRow.map((value, index) => {
      if (index === 0) return 'Date'
      return value || `col_${index}`
    })
    // Skip row1 (Ticker) and row2 (Date label row)
    let dataStart = 1
    if (rawRows[1] && rawRows[1][0] === 'Ticker') dataStart = 2
    if (rawRows[dataStart] && rawRows[dataStart][0] === 'Date') dataStart += 1
    return [mergedHeader, ...rawRows.slice(dataStart)]
  }

  return rawRows
}

export async function loadCsvOHLC(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`載入失敗: ${url}`)
  }

  const text = await response.text()
  const parsed = Papa.parse(text.trim(), {
    skipEmptyLines: true
  })

  const rows = normalizeColumns(parsed.data)
  if (rows.length < 3) {
    throw new Error(`資料不足: ${url}`)
  }

  const header = rows[0].map((item) => String(item).trim())
  const indexMap = new Map(header.map((name, index) => [name, index]))

  const dateIndex = indexMap.has('Date') ? indexMap.get('Date') : 0
  const closeIndex = indexMap.has('Close') ? indexMap.get('Close') : indexMap.get('Adj Close')
  const openIndex = indexMap.has('Open') ? indexMap.get('Open') : null
  const highIndex = indexMap.has('High') ? indexMap.get('High') : null
  const lowIndex = indexMap.has('Low') ? indexMap.get('Low') : null

  if (closeIndex == null) {
    throw new Error(`找不到 Close 欄位: ${url}`)
  }

  const data = rows
    .slice(1)
    .map((row) => ({
      date: row[dateIndex],
      close: parseNumber(row[closeIndex]),
      open: openIndex != null ? parseNumber(row[openIndex]) : null,
      high: highIndex != null ? parseNumber(row[highIndex]) : null,
      low: lowIndex != null ? parseNumber(row[lowIndex]) : null
    }))
    .filter((row) => row.date && row.close != null)

  data.sort((a, b) => new Date(a.date) - new Date(b.date))
  return data
}