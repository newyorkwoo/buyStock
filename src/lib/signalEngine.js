import { rsi, sma, vixRawScore, vixLevelDescription } from './indicators'

const SIGNALS = {
  STRONG_BUY: 'STRONG_BUY',
  BUY: 'BUY',
  HOLD: 'HOLD',
  SELL: 'SELL',
  STRONG_SELL: 'STRONG_SELL'
}

export const defaultConfig = {
  rsi: { period: 60, oversold: 43, overbought: 61 },
  ma: { shortPeriod: 60, longPeriod: 200 },
  vix: { normal: 15, fear: 20, highFear: 28, extremeFear: 41 },
  weights: { rsi: 0.34, ma: 0.33, vix: 0.33 }
}

function rsiScore(value, config) {
  if (value == null || Number.isNaN(value)) return { score: 0, signal: 'HOLD', description: '資料不足' }
  if (value < 20) return { score: 2, signal: 'BUY', description: `RSI=${value.toFixed(1)} ＜ 20 強烈超賣（歷史超賣線=${config.oversold}）` }
  if (value < config.oversold) return { score: 1, signal: 'BUY', description: `RSI=${value.toFixed(1)} ＜ 超賣線${config.oversold}（波谷P25），建議買入` }
  if (value > 80) return { score: -2, signal: 'SELL', description: `RSI=${value.toFixed(1)} ＞ 80 強烈超買（歷史超買線=${config.overbought}）` }
  if (value > config.overbought) return { score: -1, signal: 'SELL', description: `RSI=${value.toFixed(1)} ＞ 超買線${config.overbought}（波峰P75），建議賣出` }
  return { score: 0, signal: 'HOLD', description: `RSI=${value.toFixed(1)}，介於超賣${config.oversold}~超買${config.overbought}之間，中性` }
}

function maScore(closeValue, shortValue, longValue, maConfig) {
  if ([closeValue, shortValue, longValue].some((value) => value == null || Number.isNaN(value))) {
    return { score: 0, signal: 'HOLD', description: '資料不足 (需更長歷史資料)' }
  }

  const bullish = shortValue > longValue
  const aboveShort = closeValue > shortValue

  if (bullish) {
    if (aboveShort) {
      return {
        score: 2,
        signal: 'BUY',
        description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 短線在長線之上（多頭排列）+站上均線`
      }
    }
    return {
      score: 1,
      signal: 'BUY',
      description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 短線在長線之上（多頭排列）`
    }
  }

  if (!aboveShort) {
    return {
      score: -2,
      signal: 'SELL',
      description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 短線在長線之下（空頭排列）+跌破均線`
    }
  }
  return {
    score: -1,
    signal: 'SELL',
    description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 短線在長線之下（空頭排列）`
  }
}

function toSignal(totalScore, rawVixScore, currentDrawdown = 0) {
  let signal
  if (rawVixScore >= 4) signal = totalScore >= 0 ? SIGNALS.STRONG_BUY : SIGNALS.BUY
  else if (rawVixScore <= -2) signal = totalScore <= 0 ? SIGNALS.STRONG_SELL : SIGNALS.SELL
  else if (totalScore >= 1.5) signal = SIGNALS.STRONG_BUY
  else if (totalScore >= 0.5) signal = SIGNALS.BUY
  else if (totalScore <= -1.5) signal = SIGNALS.STRONG_SELL
  else if (totalScore <= -0.5) signal = SIGNALS.SELL
  else signal = SIGNALS.HOLD

  // Cap buy signals when drawdown is shallow (< 10%)
  // Market hasn't corrected enough to justify a buy
  if (currentDrawdown > -0.10) {
    if (signal === SIGNALS.STRONG_BUY || signal === SIGNALS.BUY) {
      signal = SIGNALS.HOLD
    }
  }

  return signal
}

function confidence(scores) {
  const positiveCount = scores.filter((score) => score > 0).length
  const negativeCount = scores.filter((score) => score < 0).length
  const agreement = Math.max(positiveCount, negativeCount) / scores.length
  const avgStrength = scores.reduce((acc, score) => acc + Math.abs(score), 0) / scores.length
  return Math.min(agreement * 50 + (avgStrength / 2) * 50, 100)
}

function summary(signal, score, vixValue, bullishCount, currentDrawdown) {
  if (signal === SIGNALS.STRONG_BUY) return `🔥 強力買入訊號！${bullishCount}/3 指標看多，VIX=${vixValue.toFixed(2)}。`
  if (signal === SIGNALS.BUY) return `📈 偏多格局，${bullishCount}/3 指標看多，可考慮分批布局。`
  if (signal === SIGNALS.HOLD) {
    if (currentDrawdown > -0.10 && score > 0) {
      return `⏸️ 技術面偏多（分數 ${score.toFixed(2)}），但市場距高點僅 ${(currentDrawdown * 100).toFixed(1)}%，跌幅不足 10%，建議觀望。`
    }
    return `⏸️ 多空交戰，綜合分數 ${score.toFixed(2)}，等待更明確方向。`
  }
  if (signal === SIGNALS.SELL) return `📉 偏空格局，注意風險控管。綜合分數 ${score.toFixed(2)}。`
  return `⚠️ 強力賣出訊號！綜合分數 ${score.toFixed(2)}。`
}

/**
 * Calculate current drawdown from recent peak
 */
function calcCurrentDrawdown(closes) {
  let peak = -Infinity
  let peakIdx = 0
  // Find the highest peak by scanning all data — use "50% rebound reset" logic
  let cyclePeak = closes[0]
  let cycleTrough = closes[0]

  for (let i = 1; i < closes.length; i++) {
    if (closes[i] > cyclePeak) {
      cyclePeak = closes[i]
      cycleTrough = closes[i]
    }
    if (closes[i] < cycleTrough) {
      cycleTrough = closes[i]
    }
    // 50% rebound reset
    const dd = (cycleTrough - cyclePeak) / cyclePeak
    if (dd < -0.10) {
      const rebound = (closes[i] - cycleTrough) / (cyclePeak - cycleTrough)
      if (rebound > 0.5) {
        cyclePeak = closes[i]
        cycleTrough = closes[i]
      }
    }
  }

  // Now cyclePeak is the peak of the current cycle
  const latest = closes[closes.length - 1]
  const currentDd = (latest - cyclePeak) / cyclePeak
  return { currentDrawdown: currentDd, cyclePeakPrice: cyclePeak, latestPrice: latest }
}

/**
 * Generate position-specific advice based on drawdown, RSI, VIX, MA
 */
function generatePositionAdvice(drawdownInfo, rsiValue, vixValue, maShort, maLong, config) {
  const { currentDrawdown, cyclePeakPrice } = drawdownInfo
  const ddPct = (currentDrawdown * 100).toFixed(1)
  const rsiV = rsiValue != null ? rsiValue.toFixed(1) : null

  // ── 未持股票建議 ──
  let noPositionSignal, noPositionAdvice, noPositionColor

  if (currentDrawdown <= -0.20) {
    noPositionSignal = 'STRONG_BUY'
    noPositionColor = 'strong-buy'
    noPositionAdvice = `📉 從高點回落 ${ddPct}%，已超過 20%，歷史上屬於較大跌幅區間。VIX=${vixValue.toFixed(2)}，建議積極分批買入。`
  } else if (currentDrawdown <= -0.15) {
    noPositionSignal = 'BUY'
    noPositionColor = 'buy'
    noPositionAdvice = `📉 從高點回落 ${ddPct}%，跌幅達 15%。可開始分批布局第一筆資金，但保留子彈等待更深跌幅。`
  } else if (currentDrawdown <= -0.10) {
    noPositionSignal = 'BUY'
    noPositionColor = 'buy'
    noPositionAdvice = `📉 從高點回落 ${ddPct}%，已觸及 10% 門檻。可小量試探性買入，等待更好時機加碼。`
  } else if (currentDrawdown <= -0.05) {
    noPositionSignal = 'HOLD'
    noPositionColor = 'hold'
    noPositionAdvice = `⏸️ 從高點回落 ${ddPct}%，尚未達到 10% 進場門檻。繼續觀望等待，不急於進場。`
  } else {
    noPositionSignal = 'HOLD'
    noPositionColor = 'hold'
    noPositionAdvice = `⏸️ 市場接近高點（距峰值 ${ddPct}%），不建議此時建倉。等待回落超過 10% 再進場。`
  }

  // Add RSI/VIX context for no position
  if (rsiV != null && rsiValue < config.rsi.oversold && currentDrawdown <= -0.10) {
    noPositionAdvice += ` RSI=${rsiV} 已低於超賣線 ${config.rsi.oversold}，支持買入。`
  }
  if (vixValue >= config.vix.extremeFear && currentDrawdown <= -0.10) {
    noPositionAdvice += ` VIX=${vixValue.toFixed(2)} 達極端恐慌（≥${config.vix.extremeFear}），歷史級買入機會。`
    noPositionSignal = 'STRONG_BUY'
    noPositionColor = 'strong-buy'
  }

  // ── 已持有股票建議 ──
  let hasPositionSignal, hasPositionAdvice, hasPositionColor

  if (currentDrawdown <= -0.20) {
    hasPositionSignal = 'BUY'
    hasPositionColor = 'buy'
    hasPositionAdvice = `📉 從高點回落 ${ddPct}%，跌幅已深。若持倉成本較高，可考慮逢低攤平降低成本。`
  } else if (currentDrawdown <= -0.10) {
    hasPositionSignal = 'HOLD'
    hasPositionColor = 'hold'
    hasPositionAdvice = `⏸️ 從高點回落 ${ddPct}%，目前不適合加倉。建議持有觀望，等待更明確的底部訊號再考慮加碼。`
  } else if (currentDrawdown <= -0.05) {
    hasPositionSignal = 'BUY'
    hasPositionColor = 'buy'
    hasPositionAdvice = `📉 從波段高點下跌 ${ddPct}%，已達 5% 門檻。建議買進與指數相關的股票。`
  } else {
    // Near peak
    if (rsiV != null && rsiValue > config.rsi.overbought) {
      hasPositionSignal = 'SELL'
      hasPositionColor = 'sell'
      hasPositionAdvice = `⚠️ 市場接近高點（距峰值 ${ddPct}%），RSI=${rsiV} 超過超買線 ${config.rsi.overbought}。可考慮分批減碼，鎖定部分獲利。`
    } else {
      hasPositionSignal = 'HOLD'
      hasPositionColor = 'hold'
      hasPositionAdvice = `📈 市場接近高點（距峰值 ${ddPct}%），趨勢尚佳。繼續持有，但留意 RSI 是否接近超買線 ${config.rsi.overbought}。`
    }
  }

  // Add VIX extreme for has position
  if (vixValue >= config.vix.highFear && currentDrawdown <= -0.10) {
    hasPositionAdvice += ` VIX=${vixValue.toFixed(2)} 恐慌偏高，如有閒置資金可考慮小幅加碼。`
    if (vixValue >= config.vix.extremeFear) {
      hasPositionSignal = 'BUY'
      hasPositionColor = 'buy'
    }
  }

  return {
    noPosition: { signal: noPositionSignal, advice: noPositionAdvice, color: noPositionColor },
    hasPosition: { signal: hasPositionSignal, advice: hasPositionAdvice, color: hasPositionColor },
    drawdown: { pct: ddPct, peakPrice: cyclePeakPrice }
  }
}

export function generateSignal(nasdaqRows, vixRows, customConfig = defaultConfig) {
  if (!Array.isArray(nasdaqRows) || !Array.isArray(vixRows)) {
    throw new Error('資料格式錯誤')
  }
  if (nasdaqRows.length < customConfig.ma.longPeriod + 5 || vixRows.length < 5) {
    throw new Error('資料不足，無法計算長期均線')
  }

  const mergedConfig = {
    ...defaultConfig,
    ...customConfig,
    rsi: { ...defaultConfig.rsi, ...(customConfig?.rsi || {}) },
    ma: { ...defaultConfig.ma, ...(customConfig?.ma || {}) },
    vix: { ...defaultConfig.vix, ...(customConfig?.vix || {}) },
    weights: { ...defaultConfig.weights, ...(customConfig?.weights || {}) }
  }

  const closes = nasdaqRows.map((row) => row.close)
  const rsiValues = rsi(closes, mergedConfig.rsi.period)
  const shortSma = sma(closes, mergedConfig.ma.shortPeriod)
  const longSma = sma(closes, mergedConfig.ma.longPeriod)

  const latestIndex = closes.length - 1
  const previousIndex = closes.length - 2

  const latestNasdaq = nasdaqRows[latestIndex]
  const previousNasdaq = nasdaqRows[previousIndex]
  const latestVix = vixRows[vixRows.length - 1]

  const rsiResult = rsiScore(rsiValues[latestIndex], mergedConfig.rsi)
  const maResult = maScore(closes[latestIndex], shortSma[latestIndex], longSma[latestIndex], mergedConfig.ma)

  const rawVixScore = vixRawScore(latestVix.close, mergedConfig.vix)
  const normalizedVixScore = Math.max(-2, Math.min(2, rawVixScore))
  const vixSignal = rawVixScore >= 2 ? 'BUY' : rawVixScore <= -1 ? 'SELL' : 'HOLD'
  const vixDesc = vixLevelDescription(latestVix.close, mergedConfig.vix)

  const totalScore =
    rsiResult.score * mergedConfig.weights.rsi +
    maResult.score * mergedConfig.weights.ma +
    normalizedVixScore * mergedConfig.weights.vix

  // Position-specific advice (calculated early for drawdown info)
  const drawdownInfo = calcCurrentDrawdown(closes)

  const finalSignal = toSignal(totalScore, rawVixScore, drawdownInfo.currentDrawdown)
  const confidenceValue = confidence([rsiResult.score, maResult.score, normalizedVixScore])

  const bullishCount = [rsiResult.score, maResult.score, normalizedVixScore].filter((s) => s > 0).length

  const positionAdvice = generatePositionAdvice(
    drawdownInfo,
    rsiValues[latestIndex],
    latestVix.close,
    shortSma[latestIndex],
    longSma[latestIndex],
    mergedConfig
  )

  return {
    signal: finalSignal,
    totalScore,
    confidence: confidenceValue,
    date: latestNasdaq.date,
    nasdaqPrice: latestNasdaq.close,
    nasdaqChange: ((latestNasdaq.close - previousNasdaq.close) / previousNasdaq.close) * 100,
    vixValue: latestVix.close,
    config: mergedConfig,
    positionAdvice,
    scores: {
      rsi: rsiResult,
      ma: maResult,
      vix: {
        score: rawVixScore,
        signal: vixSignal,
        description: vixDesc
      }
    },
    summary: summary(finalSignal, totalScore, latestVix.close, bullishCount, drawdownInfo.currentDrawdown)
  }
}

export { SIGNALS }