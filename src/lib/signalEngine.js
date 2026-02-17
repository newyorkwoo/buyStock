import { rsi, sma, vixRawScore } from './indicators'

const SIGNALS = {
  STRONG_BUY: 'STRONG_BUY',
  BUY: 'BUY',
  HOLD: 'HOLD',
  SELL: 'SELL',
  STRONG_SELL: 'STRONG_SELL'
}

export const defaultConfig = {
  rsi: { period: 14, oversold: 30, overbought: 70 },
  ma: { shortPeriod: 60, longPeriod: 200 },
  vix: { normal: 20, fear: 25, highFear: 30, extremeFear: 40 },
  weights: { rsi: 0.34, ma: 0.33, vix: 0.33 }
}

function rsiScore(value, config) {
  if (value == null || Number.isNaN(value)) return { score: 0, signal: 'HOLD', description: '資料不足' }
  if (value < 20) return { score: 2, signal: 'BUY', description: `RSI=${value.toFixed(1)} 強烈超賣` }
  if (value < config.oversold) return { score: 1, signal: 'BUY', description: `RSI=${value.toFixed(1)} 超賣` }
  if (value > 80) return { score: -2, signal: 'SELL', description: `RSI=${value.toFixed(1)} 強烈超買` }
  if (value > config.overbought) return { score: -1, signal: 'SELL', description: `RSI=${value.toFixed(1)} 超買` }
  return { score: 0, signal: 'HOLD', description: `RSI=${value.toFixed(1)} 中性` }
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
        description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 黃金交叉+站上均線`
      }
    }
    return {
      score: 1,
      signal: 'BUY',
      description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 黃金交叉`
    }
  }

  if (!aboveShort) {
    return {
      score: -2,
      signal: 'SELL',
      description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 死亡交叉+跌破均線`
    }
  }
  return {
    score: -1,
    signal: 'SELL',
    description: `SMA${maConfig.shortPeriod}-SMA${maConfig.longPeriod}=${(shortValue - longValue).toFixed(2)} 死亡交叉`
  }
}

function toSignal(totalScore, rawVixScore) {
  if (rawVixScore >= 4) return totalScore >= 0 ? SIGNALS.STRONG_BUY : SIGNALS.BUY
  if (rawVixScore <= -2) return totalScore <= 0 ? SIGNALS.STRONG_SELL : SIGNALS.SELL
  if (totalScore >= 1.5) return SIGNALS.STRONG_BUY
  if (totalScore >= 0.5) return SIGNALS.BUY
  if (totalScore <= -1.5) return SIGNALS.STRONG_SELL
  if (totalScore <= -0.5) return SIGNALS.SELL
  return SIGNALS.HOLD
}

function confidence(scores) {
  const positiveCount = scores.filter((score) => score > 0).length
  const negativeCount = scores.filter((score) => score < 0).length
  const agreement = Math.max(positiveCount, negativeCount) / scores.length
  const avgStrength = scores.reduce((acc, score) => acc + Math.abs(score), 0) / scores.length
  return Math.min(agreement * 50 + (avgStrength / 2) * 50, 100)
}

function summary(signal, score, vixValue, bullishCount) {
  if (signal === SIGNALS.STRONG_BUY) return `🔥 強力買入訊號！${bullishCount}/3 指標看多，VIX=${vixValue.toFixed(2)}。`
  if (signal === SIGNALS.BUY) return `📈 偏多格局，${bullishCount}/3 指標看多，可考慮分批布局。`
  if (signal === SIGNALS.HOLD) return `⏸️ 多空交戰，綜合分數 ${score.toFixed(2)}，等待更明確方向。`
  if (signal === SIGNALS.SELL) return `📉 偏空格局，注意風險控管。綜合分數 ${score.toFixed(2)}。`
  return `⚠️ 強力賣出訊號！綜合分數 ${score.toFixed(2)}。`
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

  const totalScore =
    rsiResult.score * mergedConfig.weights.rsi +
    maResult.score * mergedConfig.weights.ma +
    normalizedVixScore * mergedConfig.weights.vix

  const finalSignal = toSignal(totalScore, rawVixScore)
  const confidenceValue = confidence([rsiResult.score, maResult.score, normalizedVixScore])

  const bullishCount = [rsiResult.score, maResult.score, normalizedVixScore].filter((s) => s > 0).length

  return {
    signal: finalSignal,
    totalScore,
    confidence: confidenceValue,
    date: latestNasdaq.date,
    nasdaqPrice: latestNasdaq.close,
    nasdaqChange: ((latestNasdaq.close - previousNasdaq.close) / previousNasdaq.close) * 100,
    vixValue: latestVix.close,
    scores: {
      rsi: rsiResult,
      ma: maResult,
      vix: {
        score: rawVixScore,
        signal: vixSignal,
        description: `VIX=${latestVix.close.toFixed(2)} (${vixSignal})`
      }
    },
    summary: summary(finalSignal, totalScore, latestVix.close, bullishCount)
  }
}

export { SIGNALS }