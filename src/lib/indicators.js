export function sma(values, period) {
  const result = Array(values.length).fill(null)
  if (period <= 0) return result

  let windowSum = 0
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index]
    windowSum += value

    if (index >= period) {
      windowSum -= values[index - period]
    }

    if (index >= period - 1) {
      result[index] = windowSum / period
    }
  }

  return result
}

export function ema(values, period) {
  const result = Array(values.length).fill(null)
  if (period <= 0 || values.length === 0) return result

  const multiplier = 2 / (period + 1)
  let emaValue = values[0]

  for (let index = 0; index < values.length; index += 1) {
    if (index === 0) {
      emaValue = values[index]
    } else {
      emaValue = (values[index] - emaValue) * multiplier + emaValue
    }
    result[index] = emaValue
  }

  return result
}

export function rsi(values, period = 60) {
  const result = Array(values.length).fill(null)
  if (values.length <= period) return result

  let gains = 0
  let losses = 0

  for (let index = 1; index <= period; index += 1) {
    const delta = values[index] - values[index - 1]
    if (delta >= 0) gains += delta
    else losses -= delta
  }

  let avgGain = gains / period
  let avgLoss = losses / period
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)

  for (let index = period + 1; index < values.length; index += 1) {
    const delta = values[index] - values[index - 1]
    const gain = delta > 0 ? delta : 0
    const loss = delta < 0 ? -delta : 0

    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period

    if (avgLoss === 0) {
      result[index] = 100
    } else {
      const rs = avgGain / avgLoss
      result[index] = 100 - 100 / (1 + rs)
    }
  }

  return result
}

export function vixRawScore(vixValue, thresholds) {
  if (vixValue < 12) return -2
  if (vixValue < thresholds.normal) return 0
  if (vixValue < thresholds.fear) return 1
  if (vixValue < thresholds.highFear) return 2
  if (vixValue < thresholds.extremeFear) return 3
  return 4
}

export function vixLevelDescription(vixValue, thresholds) {
  if (vixValue < 12) return `VIX=${vixValue.toFixed(2)} ＜ 12 極低恐慌，市場過度樂觀，注意風險`
  if (vixValue < thresholds.normal) return `VIX=${vixValue.toFixed(2)} ＜ 正常線${thresholds.normal}，市場平靜`
  if (vixValue < thresholds.fear) return `VIX=${vixValue.toFixed(2)}，正常${thresholds.normal}~恐慌${thresholds.fear}之間，略有恐慌`
  if (vixValue < thresholds.highFear) return `VIX=${vixValue.toFixed(2)} ≥ 恐慌線${thresholds.fear}（波谷P25），恐慌升溫，可留意買點`
  if (vixValue < thresholds.extremeFear) return `VIX=${vixValue.toFixed(2)} ≥ 高恐慌線${thresholds.highFear}（波谷中位數），買入機會浮現`
  return `VIX=${vixValue.toFixed(2)} ≥ 極端恐慌線${thresholds.extremeFear}（波谷P75），歷史級買入機會`
}