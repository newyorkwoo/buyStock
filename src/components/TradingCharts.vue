<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { createChart, CrosshairMode, CandlestickSeries, LineSeries, AreaSeries, createSeriesMarkers } from 'lightweight-charts'
import { rsi as calcRsi, sma as calcSma } from '../lib/indicators'
import { findSwingCycles, buildDrawdownAreaData, buildSwingMarkers } from '../lib/swingDetector'

const props = defineProps({
  nasdaqRows: { type: Array, required: true },
  vixRows: { type: Array, required: true },
  maShort: { type: Number, default: 60 },
  maLong: { type: Number, default: 250 },
  rsiPeriod: { type: Number, default: 60 },
  rsiOversold: { type: Number, default: 30 },
  rsiOverbought: { type: Number, default: 70 },
  vixFear: { type: Number, default: 20 },
  vixHighFear: { type: Number, default: 28 },
  vixExtremeFear: { type: Number, default: 41 }
})

const klineRef = ref(null)
const vixRef = ref(null)
const rsiRef = ref(null)

let klineChart = null
let vixChart = null
let rsiChart = null
let resizeObserver = null

// Main series per chart — needed for setCrosshairPosition
let klineMainSeries = null
let vixMainSeries = null
let rsiMainSeries = null

const chartTheme = {
  layout: { background: { color: '#1e293b' }, textColor: '#94a3b8' },
  grid: {
    vertLines: { color: '#1e293b' },
    horzLines: { color: '#334155' }
  },
  crosshair: { mode: CrosshairMode.Normal },
  timeScale: { borderColor: '#334155', timeVisible: false },
  rightPriceScale: { borderColor: '#334155', minimumWidth: 120 }
}

function toTimeValue(dateStr) {
  return dateStr.slice(0, 10)
}

function buildCharts() {
  destroyCharts()

  const nasdaq = props.nasdaqRows
  const vix = props.vixRows
  if (!nasdaq.length || !vix.length) return

  // --- shared visible range: last 365 bars ---
  const visibleBars = 365
  const fromStr = nasdaq.length > visibleBars ? nasdaq[nasdaq.length - visibleBars].date.slice(0, 10) : nasdaq[0].date.slice(0, 10)
  const toStr = nasdaq[nasdaq.length - 1].date.slice(0, 10)

  // ============ K-line + MA chart ============
  klineChart = createChart(klineRef.value, {
    ...chartTheme,
    height: 360
  })

  const candleSeries = klineChart.addSeries(CandlestickSeries, {
    upColor: '#22c55e',
    downColor: '#ef4444',
    borderUpColor: '#22c55e',
    borderDownColor: '#ef4444',
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444'
  })

  klineMainSeries = candleSeries

  const candleData = nasdaq
    .filter((r) => r.open != null && r.high != null && r.low != null)
    .map((r) => ({
      time: toTimeValue(r.date),
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close
    }))
  candleSeries.setData(candleData)

  // SMA short
  const closes = nasdaq.map((r) => r.close)
  const smaShortValues = calcSma(closes, props.maShort)
  const smaShortSeries = klineChart.addSeries(LineSeries, {
    color: '#38bdf8',
    lineWidth: 1,
    title: `SMA${props.maShort}`
  })
  smaShortSeries.setData(
    smaShortValues
      .map((v, i) => (v != null ? { time: toTimeValue(nasdaq[i].date), value: v } : null))
      .filter(Boolean)
  )

  // SMA long
  const smaLongValues = calcSma(closes, props.maLong)
  const smaLongSeries = klineChart.addSeries(LineSeries, {
    color: '#f59e0b',
    lineWidth: 1,
    title: `SMA${props.maLong}`
  })
  smaLongSeries.setData(
    smaLongValues
      .map((v, i) => (v != null ? { time: toTimeValue(nasdaq[i].date), value: v } : null))
      .filter(Boolean)
  )

  // ============ Drawdown zones (≥10%) ============
  const cycles = findSwingCycles(nasdaq, 0.10)

  if (cycles.length) {
    // Background shading via area on hidden scale
    const bgSeries = klineChart.addSeries(AreaSeries, {
      priceScaleId: 'drawdown_bg',
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      lineVisible: false,
      topColor: 'rgba(239, 68, 68, 0.25)',
      bottomColor: 'rgba(239, 68, 68, 0.25)',
      lineColor: 'transparent'
    })
    klineChart.priceScale('drawdown_bg').applyOptions({
      visible: false,
      scaleMargins: { top: 0, bottom: 0 }
    })
    bgSeries.setData(buildDrawdownAreaData(nasdaq, cycles))

    // Peak / trough markers on candle series
    createSeriesMarkers(candleSeries, buildSwingMarkers(cycles, nasdaq))
  }

  klineChart.timeScale().setVisibleRange({ from: fromStr, to: toStr })

  // ============ VIX chart ============
  vixChart = createChart(vixRef.value, {
    ...chartTheme,
    height: 180
  })

  const vixAreaSeries = vixChart.addSeries(AreaSeries, {
    topColor: 'rgba(239,68,68,0.35)',
    bottomColor: 'rgba(239,68,68,0.02)',
    lineColor: '#ef4444',
    lineWidth: 1,
    title: 'VIX'
  })
  vixMainSeries = vixAreaSeries
  vixAreaSeries.setData(
    vix.map((r) => ({ time: toTimeValue(r.date), value: r.close }))
  )

  // VIX threshold lines
  const vixFrom = vix[0].date.slice(0, 10)
  const vixTo = vix[vix.length - 1].date.slice(0, 10)

  const addVixLevel = (level, color, title) => {
    const s = vixChart.addSeries(LineSeries, {
      color,
      lineWidth: 1,
      lineStyle: 2,
      title,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false
    })
    s.setData([
      { time: vixFrom, value: level },
      { time: vixTo, value: level }
    ])
  }

  addVixLevel(props.vixFear, '#94a3b8', `Fear(${props.vixFear})`)
  addVixLevel(props.vixHighFear, '#f59e0b', `High Fear(${props.vixHighFear})`)
  addVixLevel(props.vixExtremeFear, '#ef4444', `Extreme(${props.vixExtremeFear})`)

  // VIX drawdown zones
  if (cycles.length) {
    const vixBg = vixChart.addSeries(AreaSeries, {
      priceScaleId: 'vix_dd_bg',
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      lineVisible: false,
      topColor: 'rgba(239, 68, 68, 0.28)',
      bottomColor: 'rgba(239, 68, 68, 0.28)',
      lineColor: 'transparent'
    })
    vixChart.priceScale('vix_dd_bg').applyOptions({
      visible: false,
      scaleMargins: { top: 0, bottom: 0 }
    })
    vixBg.setData(buildDrawdownAreaData(nasdaq, cycles))
  }

  vixChart.timeScale().setVisibleRange({ from: fromStr, to: toStr })

  // ============ RSI chart ============
  rsiChart = createChart(rsiRef.value, {
    ...chartTheme,
    height: 180
  })

  const rsiValues = calcRsi(closes, props.rsiPeriod)
  const rsiSeries = rsiChart.addSeries(LineSeries, {
    color: '#a78bfa',
    lineWidth: 1.5,
    title: `RSI(${props.rsiPeriod})`
  })
  rsiMainSeries = rsiSeries
  rsiSeries.setData(
    rsiValues.map((v, i) => {
      const point = { time: toTimeValue(nasdaq[i].date) }
      if (v != null) point.value = v
      return point
    })
  )

  // RSI threshold lines — use full NASDAQ date range to align time axis
  const rsiFrom = nasdaq[0].date.slice(0, 10)
  const rsiTo = nasdaq[nasdaq.length - 1].date.slice(0, 10)

  const addRsiLevel = (level, color, title) => {
    const s = rsiChart.addSeries(LineSeries, {
      color,
      lineWidth: 1,
      lineStyle: 2,
      title,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false
    })
    s.setData([
      { time: rsiFrom, value: level },
      { time: rsiTo, value: level }
    ])
  }

  addRsiLevel(props.rsiOversold, '#22c55e', `Oversold(${props.rsiOversold})`)
  addRsiLevel(props.rsiOverbought, '#ef4444', `Overbought(${props.rsiOverbought})`)

  // RSI drawdown zones
  if (cycles.length) {
    const rsiBg = rsiChart.addSeries(AreaSeries, {
      priceScaleId: 'rsi_dd_bg',
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      lineVisible: false,
      topColor: 'rgba(239, 68, 68, 0.28)',
      bottomColor: 'rgba(239, 68, 68, 0.28)',
      lineColor: 'transparent'
    })
    rsiChart.priceScale('rsi_dd_bg').applyOptions({
      visible: false,
      scaleMargins: { top: 0, bottom: 0 }
    })
    rsiBg.setData(buildDrawdownAreaData(nasdaq, cycles))
  }

  rsiChart.timeScale().setVisibleRange({ from: fromStr, to: toStr })

  // ============ sync crosshair ============
  const chartSeriesPairs = [
    { chart: klineChart, series: klineMainSeries },
    { chart: vixChart, series: vixMainSeries },
    { chart: rsiChart, series: rsiMainSeries }
  ]
  syncCharts(chartSeriesPairs)
}

function syncCharts(pairs) {
  // Sync visible range (scroll / zoom)
  pairs.forEach(({ chart: source }) => {
    source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range) return
      pairs.forEach(({ chart: target }) => {
        if (target !== source) {
          target.timeScale().setVisibleLogicalRange(range)
        }
      })
    })
  })

  // Sync crosshair (vertical dashed line follows mouse across all charts)
  pairs.forEach(({ chart: source }) => {
    source.subscribeCrosshairMove((param) => {
      pairs.forEach(({ chart: target, series: targetSeries }) => {
        if (target === source) return
        if (param.time) {
          target.setCrosshairPosition(NaN, param.time, targetSeries)
        } else {
          target.clearCrosshairPosition()
        }
      })
    })
  })
}

function handleResize() {
  const width = klineRef.value?.clientWidth
  if (!width) return
  klineChart?.applyOptions({ width })
  vixChart?.applyOptions({ width })
  rsiChart?.applyOptions({ width })
}

function destroyCharts() {
  klineChart?.remove()
  vixChart?.remove()
  rsiChart?.remove()
  klineChart = null
  vixChart = null
  rsiChart = null
}

watch(
  () => [props.nasdaqRows, props.vixRows, props.maShort, props.maLong, props.rsiPeriod, props.rsiOversold, props.rsiOverbought, props.vixFear, props.vixHighFear, props.vixExtremeFear],
  () => {
    if (props.nasdaqRows.length && props.vixRows.length) {
      buildCharts()
    }
  }
)

onMounted(() => {
  if (props.nasdaqRows.length && props.vixRows.length) {
    buildCharts()
  }
  resizeObserver = new ResizeObserver(handleResize)
  if (klineRef.value) resizeObserver.observe(klineRef.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  destroyCharts()
})
</script>

<template>
  <section class="chart-stack">
    <div class="chart-panel">
      <h3>K 線 + MA{{ maShort }} / MA{{ maLong }}</h3>
      <div ref="klineRef" class="chart-box" />
    </div>
    <div class="chart-panel">
      <h3>VIX 恐慌指數</h3>
      <div ref="vixRef" class="chart-box" />
    </div>
    <div class="chart-panel">
      <h3>RSI ({{ rsiPeriod }})</h3>
      <div ref="rsiRef" class="chart-box" />
    </div>
  </section>
</template>
