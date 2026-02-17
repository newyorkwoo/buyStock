/**
 * Swing Detector — 波段下跌偵測
 * Ported from analysis/swing_analyzer.py
 *
 * Uses "50% rebound reset" strategy:
 *   When price rebounds > 50% from trough, treat as new cycle.
 */

/**
 * @typedef {Object} SwingCycle
 * @property {number} peakIdx
 * @property {string} peakDate
 * @property {number} peakPrice
 * @property {number} troughIdx
 * @property {string} troughDate
 * @property {number} troughPrice
 * @property {number|null} recoveryIdx
 * @property {string|null} recoveryDate
 * @property {number|null} recoveryPrice
 * @property {number} drawdown  – negative ratio, e.g. -0.35 means -35%
 */

/**
 * Detect swing cycles with drawdown exceeding `threshold`.
 *
 * @param {{ date: string, close: number }[]} rows – sorted ascending by date
 * @param {number} [threshold=0.15] – minimum drawdown ratio (0.15 = 15%)
 * @returns {SwingCycle[]}
 */
export function findSwingCycles(rows, threshold = 0.15) {
  const n = rows.length
  if (n < 2) return []

  const cycles = []

  let cyclePeak = rows[0].close
  let cyclePeakIdx = 0
  let cycleTrough = rows[0].close
  let cycleTroughIdx = 0
  let inDrawdown = false
  let drawdownStartIdx = 0

  function pushCycle() {
    const peakVal = rows[drawdownStartIdx].close
    const maxDd = (cycleTrough - peakVal) / peakVal
    if (maxDd > -threshold) return // not deep enough

    let recoveryIdx = null
    for (let j = cycleTroughIdx; j < n; j++) {
      if (rows[j].close >= peakVal) {
        recoveryIdx = j
        break
      }
    }

    cycles.push({
      peakIdx: drawdownStartIdx,
      peakDate: rows[drawdownStartIdx].date,
      peakPrice: peakVal,
      troughIdx: cycleTroughIdx,
      troughDate: rows[cycleTroughIdx].date,
      troughPrice: cycleTrough,
      recoveryIdx,
      recoveryDate: recoveryIdx != null ? rows[recoveryIdx].date : null,
      recoveryPrice: recoveryIdx != null ? rows[recoveryIdx].close : null,
      drawdown: maxDd
    })
  }

  for (let i = 0; i < n; i++) {
    const price = rows[i].close

    if (price > cyclePeak) {
      // New high — possibly ending drawdown
      if (inDrawdown) {
        pushCycle()
        inDrawdown = false
      }
      cyclePeak = price
      cyclePeakIdx = i
      cycleTrough = price
      cycleTroughIdx = i
    } else if (price < cycleTrough) {
      cycleTrough = price
      cycleTroughIdx = i
    }

    // Check if entering drawdown
    const currentDd = (price - cyclePeak) / cyclePeak
    if (currentDd <= -threshold && !inDrawdown) {
      inDrawdown = true
      drawdownStartIdx = cyclePeakIdx
    }

    // 50% rebound reset — start new cycle
    if (cycleTrough > 0 && inDrawdown) {
      const rebound = (price - cycleTrough) / cycleTrough
      if (rebound > 0.5) {
        pushCycle()
        inDrawdown = false
        cyclePeak = price
        cyclePeakIdx = i
        cycleTrough = price
        cycleTroughIdx = i
      }
    }
  }

  // Still in drawdown at end of data
  if (inDrawdown) {
    pushCycle()
  }

  return cycles.sort((a, b) => a.peakIdx - b.peakIdx)
}

/**
 * Build per-bar data for a background histogram series.
 * Value = 1 for bars inside a drawdown zone, 0 otherwise.
 *
 * @param {{ date: string }[]} rows
 * @param {SwingCycle[]} cycles
 * @returns {{ time: string, value: number, color: string }[]}
 */
export function buildDrawdownBackground(rows, cycles) {
  // Build a set of indices that are inside drawdown zones
  const inZone = new Uint8Array(rows.length)

  for (const c of cycles) {
    const endIdx = c.troughIdx
    for (let i = c.peakIdx; i <= endIdx; i++) {
      inZone[i] = 1
    }
  }

  return rows.map((r, i) => ({
    time: r.date.slice(0, 10),
    value: inZone[i] ? 100 : 0,
    color: inZone[i] ? 'rgba(239, 68, 68, 0.13)' : 'transparent'
  }))
}

/**
 * Build lightweight-charts markers for peaks and troughs.
 *
 * @param {SwingCycle[]} cycles
 * @returns {import('lightweight-charts').SeriesMarker[]}
 */
export function buildSwingMarkers(cycles) {
  const markers = []

  for (const c of cycles) {
    const pct = (c.drawdown * 100).toFixed(1)

    markers.push({
      time: c.peakDate.slice(0, 10),
      position: 'aboveBar',
      color: '#ef4444',
      shape: 'arrowDown',
      text: `▾ Peak`
    })

    markers.push({
      time: c.troughDate.slice(0, 10),
      position: 'belowBar',
      color: '#22c55e',
      shape: 'arrowUp',
      text: `${pct}%`
    })
  }

  // Must be sorted by time for lightweight-charts
  markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
  return markers
}
