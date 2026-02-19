/**
 * Swing Statistics Analyzer
 * 分析 2000 年至今所有波段的波峰/波谷對應 RSI、VIX、MA 統計資訊
 * 並據此提供最佳買賣參數建議
 */

import { rsi as calcRsi, sma as calcSma } from './indicators'
import { findSwingCycles } from './swingDetector'

function percentile(sorted, p) {
  if (!sorted.length) return null
  const idx = (p / 100) * (sorted.length - 1)
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  if (lo === hi) return sorted[lo]
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo)
}

function stats(arr) {
  if (!arr.length) return null
  const sorted = [...arr].sort((a, b) => a - b)
  const sum = sorted.reduce((s, v) => s + v, 0)
  return {
    count: sorted.length,
    mean: +(sum / sorted.length).toFixed(2),
    median: +percentile(sorted, 50).toFixed(2),
    min: +sorted[0].toFixed(2),
    max: +sorted[sorted.length - 1].toFixed(2),
    p25: +percentile(sorted, 25).toFixed(2),
    p75: +percentile(sorted, 75).toFixed(2),
    p10: +percentile(sorted, 10).toFixed(2),
    p90: +percentile(sorted, 90).toFixed(2)
  }
}

/**
 * For each swing cycle, compute RSI / VIX / MA values at peak and trough.
 *
 * @param {{ date: string, close: number }[]} nasdaqRows
 * @param {{ date: string, close: number }[]} vixRows
 * @param {object} [params]
 * @param {number} [params.rsiPeriod=60]
 * @param {number} [params.maShort=60]
 * @param {number} [params.maLong=250]
 * @param {number} [params.drawdownThreshold=0.10]
 * @returns {{ cycles: object[], peakStats: object, troughStats: object, recommendation: object }}
 */
export function analyzeSwingStatistics(nasdaqRows, vixRows, params = {}) {
  const {
    rsiPeriod = 60,
    maShort = 60,
    maLong = 250,
    drawdownThreshold = 0.10
  } = params

  // Build indicator arrays
  const closes = nasdaqRows.map((r) => r.close)
  const rsiValues = calcRsi(closes, rsiPeriod)
  const smaShortValues = calcSma(closes, maShort)
  const smaLongValues = calcSma(closes, maLong)

  // Build VIX lookup by date
  const vixMap = new Map()
  for (const row of vixRows) {
    vixMap.set(row.date.slice(0, 10), row.close)
  }

  // Find swing cycles
  const cycles = findSwingCycles(nasdaqRows, drawdownThreshold)

  // Collect indicator values at each peak and trough
  const peakData = { rsi: [], vix: [], maDiff: [], maRatio: [], drawdown: [] }
  const troughData = { rsi: [], vix: [], maDiff: [], maRatio: [], drawdown: [] }

  const enrichedCycles = cycles.map((c) => {
    const peakRsi = rsiValues[c.peakIdx]
    const troughRsi = rsiValues[c.troughIdx]
    const peakVix = vixMap.get(c.peakDate.slice(0, 10))
    const troughVix = vixMap.get(c.troughDate.slice(0, 10))

    const peakSmaShort = smaShortValues[c.peakIdx]
    const peakSmaLong = smaLongValues[c.peakIdx]
    const troughSmaShort = smaShortValues[c.troughIdx]
    const troughSmaLong = smaLongValues[c.troughIdx]

    const peakMaDiff = peakSmaShort != null && peakSmaLong != null
      ? ((peakSmaShort - peakSmaLong) / peakSmaLong) * 100 : null
    const troughMaDiff = troughSmaShort != null && troughSmaLong != null
      ? ((troughSmaShort - troughSmaLong) / troughSmaLong) * 100 : null

    // Collect for stats
    if (peakRsi != null) peakData.rsi.push(peakRsi)
    if (troughRsi != null) troughData.rsi.push(troughRsi)
    if (peakVix != null) peakData.vix.push(peakVix)
    if (troughVix != null) troughData.vix.push(troughVix)
    if (peakMaDiff != null) peakData.maDiff.push(peakMaDiff)
    if (troughMaDiff != null) troughData.maDiff.push(troughMaDiff)
    peakData.drawdown.push(c.drawdown * 100)
    troughData.drawdown.push(c.drawdown * 100)

    const declineDays = (() => {
      const p = new Date(c.peakDate)
      const t = new Date(c.troughDate)
      return Math.round((t - p) / 86400000)
    })()

    const recoveryDays = c.recoveryDate ? (() => {
      const t = new Date(c.troughDate)
      const r = new Date(c.recoveryDate)
      return Math.round((r - t) / 86400000)
    })() : null

    return {
      peakDate: c.peakDate.slice(0, 10),
      peakPrice: +c.peakPrice.toFixed(2),
      troughDate: c.troughDate.slice(0, 10),
      troughPrice: +c.troughPrice.toFixed(2),
      drawdown: +(c.drawdown * 100).toFixed(1),
      declineDays,
      recoveryDays,
      recoveryDate: c.recoveryDate?.slice(0, 10) || null,
      peak: {
        rsi: peakRsi != null ? +peakRsi.toFixed(1) : null,
        vix: peakVix != null ? +peakVix.toFixed(1) : null,
        maDiffPct: peakMaDiff != null ? +peakMaDiff.toFixed(2) : null
      },
      trough: {
        rsi: troughRsi != null ? +troughRsi.toFixed(1) : null,
        vix: troughVix != null ? +troughVix.toFixed(1) : null,
        maDiffPct: troughMaDiff != null ? +troughMaDiff.toFixed(2) : null
      }
    }
  })

  const peakStats = {
    rsi: stats(peakData.rsi),
    vix: stats(peakData.vix),
    maDiffPct: stats(peakData.maDiff),
    drawdown: stats(peakData.drawdown)
  }

  const troughStats = {
    rsi: stats(troughData.rsi),
    vix: stats(troughData.vix),
    maDiffPct: stats(troughData.maDiff),
    drawdown: stats(troughData.drawdown)
  }

  // Generate parameter recommendations based on statistics
  const recommendation = generateRecommendation(peakStats, troughStats)

  return {
    cycles: enrichedCycles,
    peakStats,
    troughStats,
    recommendation
  }
}

/**
 * Use historical peak/trough statistics to recommend buy/sell parameters.
 */
function generateRecommendation(peakStats, troughStats) {
  const rec = {
    rsi: { oversold: 30, overbought: 70 },
    vix: { normal: 20, fear: 25, highFear: 30, extremeFear: 40 },
    reasoning: []
  }

  // === RSI Recommendation ===
  // At troughs (buying opportunities), RSI tends to be low.
  // Use the median RSI at troughs as the oversold threshold.
  if (troughStats.rsi) {
    // p25 of trough RSI = most troughs have RSI at or below this → good buy zone
    const oversold = Math.round(troughStats.rsi.p25)
    // Clamp to reasonable range
    rec.rsi.oversold = Math.max(20, Math.min(45, oversold))
    rec.reasoning.push(
      `RSI 超賣建議 ${rec.rsi.oversold}：波谷 RSI 中位數 ${troughStats.rsi.median}，P25=${troughStats.rsi.p25}，P10=${troughStats.rsi.p10}`
    )
  }

  if (peakStats.rsi) {
    // p75 of peak RSI = most peaks have RSI at or above this → good sell zone
    const overbought = Math.round(peakStats.rsi.p75)
    rec.rsi.overbought = Math.max(60, Math.min(85, overbought))
    rec.reasoning.push(
      `RSI 超買建議 ${rec.rsi.overbought}：波峰 RSI 中位數 ${peakStats.rsi.median}，P75=${peakStats.rsi.p75}，P90=${peakStats.rsi.p90}`
    )
  }

  // === VIX Recommendation ===
  // At troughs, VIX tends to spike. Use trough VIX distribution.
  if (troughStats.vix) {
    // Normal threshold: median VIX at peaks (market tops are usually calm)
    if (peakStats.vix) {
      rec.vix.normal = Math.round(peakStats.vix.median)
    }
    // Fear: p25 of trough VIX (lower end of panic)
    rec.vix.fear = Math.round(troughStats.vix.p25)
    // High Fear: median trough VIX
    rec.vix.highFear = Math.round(troughStats.vix.median)
    // Extreme: p75 of trough VIX
    rec.vix.extremeFear = Math.round(troughStats.vix.p75)

    rec.reasoning.push(
      `VIX 閾值建議 — 正常 ${rec.vix.normal} / 恐慌 ${rec.vix.fear} / 高恐慌 ${rec.vix.highFear} / 極端 ${rec.vix.extremeFear}：` +
      `波谷 VIX 中位數 ${troughStats.vix.median}，P25=${troughStats.vix.p25}，P75=${troughStats.vix.p75}`
    )
  }

  // === MA Recommendation ===
  if (troughStats.maDiffPct) {
    rec.reasoning.push(
      `MA 交叉 — 波谷時 MA${maShort}-MA${maLong} 差值%：中位數 ${troughStats.maDiffPct.median}%，` +
      `P25=${troughStats.maDiffPct.p25}%，P75=${troughStats.maDiffPct.p75}%（負值=死叉）`
    )
  }
  if (peakStats.maDiffPct) {
    rec.reasoning.push(
      `MA 交叉 — 波峰時 MA${maShort}-MA${maLong} 差值%：中位數 ${peakStats.maDiffPct.median}%，` +
      `P25=${peakStats.maDiffPct.p25}%，P75=${peakStats.maDiffPct.p75}%（正值=黃金交叉）`
    )
  }

  // === Drawdown stats ===
  if (troughStats.drawdown) {
    rec.reasoning.push(
      `歷史跌幅：平均 ${troughStats.drawdown.mean}%，中位數 ${troughStats.drawdown.median}%，` +
      `最大 ${troughStats.drawdown.min}%，最小 ${troughStats.drawdown.max}%`
    )
  }

  return rec
}
