<script setup>
import { computed, onMounted, ref } from 'vue'
import { loadCsvOHLC } from './lib/dataLoader'
import { defaultConfig, generateSignal, SIGNALS } from './lib/signalEngine'
import { fetchNasdaq, fetchVix, mergeRows } from './lib/liveDataFetcher'
import { isTradingDay } from './lib/tradingCalendar'
import { analyzeSwingStatistics } from './lib/swingStats'
import TradingCharts from './components/TradingCharts.vue'

const storageKey = 'buystock-config'

const loading = ref(false)
const errorMessage = ref('')
const infoMessage = ref('')
const signalResult = ref(null)
const nasdaqRows = ref([])
const vixRows = ref([])
const dataStatus = ref('')  // 資料狀態
const swingAnalysis = ref(null) // 波段統計分析結果

const config = ref(structuredClone(defaultConfig))
const dataSource = ref({
  nasdaqUrl: '/data/raw/nasdaq_2000.csv',
  vixUrl: '/data/raw/vix_2000.csv'
})



const isBuySignal = computed(() => {
  if (!signalResult.value) return false
  return [SIGNALS.BUY, SIGNALS.STRONG_BUY].includes(signalResult.value.signal)
})

const signalClass = computed(() => {
  const signal = signalResult.value?.signal
  if (signal === SIGNALS.STRONG_BUY) return 'signal strong-buy'
  if (signal === SIGNALS.BUY) return 'signal buy'
  if (signal === SIGNALS.HOLD) return 'signal hold'
  if (signal === SIGNALS.SELL) return 'signal sell'
  return 'signal strong-sell'
})

function saveConfig() {
  const payload = {
    config: config.value,
    dataSource: dataSource.value,

  }
  localStorage.setItem(storageKey, JSON.stringify(payload))
}

function loadSavedConfig() {
  const raw = localStorage.getItem(storageKey)
  if (!raw) return

  try {
    const parsed = JSON.parse(raw)
    if (parsed.config) config.value = parsed.config
    if (parsed.dataSource) dataSource.value = parsed.dataSource

    // 強制使用程式碼中的 MA 週期設定（避免 localStorage 殘留舊值）
    config.value.ma.shortPeriod = defaultConfig.ma.shortPeriod
    config.value.ma.longPeriod = defaultConfig.ma.longPeriod
  } catch {
    localStorage.removeItem(storageKey)
  }
}

async function runAnalysis() {
  loading.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  dataStatus.value = '載入中…'

  try {
    // 1. Load static CSV as baseline
    const [staticNasdaq, staticVix] = await Promise.all([
      loadCsvOHLC(dataSource.value.nasdaqUrl),
      loadCsvOHLC(dataSource.value.vixUrl)
    ])

    let nRows = staticNasdaq
    let vRows = staticVix
    let liveOk = false

    // 2. If trading day, try fetching live data from Yahoo Finance
    if (isTradingDay()) {
      dataStatus.value = '正在從 Yahoo Finance 更新即時資料…'
      try {
        const [liveNasdaq, liveVix] = await Promise.all([
          fetchNasdaq(),
          fetchVix()
        ])
        if (liveNasdaq.length > 0 && liveVix.length > 0) {
          nRows = mergeRows(staticNasdaq, liveNasdaq)
          vRows = mergeRows(staticVix, liveVix)
          liveOk = true
        }
      } catch (liveErr) {
        console.warn('即時資料取得失敗，使用本地 CSV:', liveErr.message)
      }
    }

    nasdaqRows.value = nRows
    vixRows.value = vRows

    const lastDate = nRows[nRows.length - 1]?.date?.slice(0, 10) || '?'
    dataStatus.value = liveOk
      ? `✅ 即時資料已更新（至 ${lastDate}）`
      : `📁 使用本地資料（至 ${lastDate}）`

    // Run swing statistics first to get recommended parameters
    try {
      swingAnalysis.value = analyzeSwingStatistics(nRows, vRows, {
        rsiPeriod: config.value.rsi.period || 60,
        maShort: config.value.ma.shortPeriod,
        maLong: config.value.ma.longPeriod,
        drawdownThreshold: 0.10
      })

      // Auto-apply historical statistics recommendation to config
      const rec = swingAnalysis.value.recommendation
      if (rec) {
        config.value.rsi.oversold = rec.rsi.oversold
        config.value.rsi.overbought = rec.rsi.overbought
        config.value.vix.normal = rec.vix.normal
        config.value.vix.fear = rec.vix.fear
        config.value.vix.highFear = rec.vix.highFear
        config.value.vix.extremeFear = rec.vix.extremeFear
      }
    } catch (e) {
      console.warn('波段統計分析失敗:', e.message)
    }

    // Generate signal using stats-recommended parameters
    const result = generateSignal(nRows, vRows, config.value)
    signalResult.value = result

    saveConfig()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '分析失敗'
    dataStatus.value = '❌ 資料載入失敗'
  } finally {
    loading.value = false
  }
}



onMounted(() => {
  loadSavedConfig()
  runAnalysis()
})
</script>

<template>
  <main class="container">
    <header class="card">
      <h1>📈 股票買賣通知系統</h1>
    </header>

    <section v-if="signalResult" :class="['card', signalClass]">
      <h2>最新訊號：</h2>
      <p>{{ signalResult.summary }}</p>
      <p>
        日期：{{ signalResult.date }} ｜ NASDAQ：{{ signalResult.nasdaqPrice.toFixed(2) }}
        ({{ signalResult.nasdaqChange.toFixed(2) }}%) ｜ VIX：{{ signalResult.vixValue.toFixed(2) }}
      </p>
      <p v-if="signalResult.positionAdvice">
        距離波段高點：{{ signalResult.positionAdvice.drawdown.pct }}%
        （高點 {{ signalResult.positionAdvice.drawdown.peakPrice.toLocaleString() }}）
      </p>
      <p>綜合分數：{{ signalResult.totalScore.toFixed(2) }} ｜ 信心度：{{ signalResult.confidence.toFixed(1) }}%</p>

      <p class="config-note" v-if="signalResult.config">
        📊 依據歷史統計：RSI 超賣={{ signalResult.config.rsi.oversold }} / 超買={{ signalResult.config.rsi.overbought }}
        ｜ VIX 恐慌={{ signalResult.config.vix.fear }} / 高恐慌={{ signalResult.config.vix.highFear }} / 極端={{ signalResult.config.vix.extremeFear }}
      </p>

      <!-- Position-specific advice -->
      <div v-if="signalResult.positionAdvice" class="position-advice">
        <div :class="['advice-card', signalResult.positionAdvice.noPosition.color]">
          <h3>🆕 未持股票建議：<span :class="'tag-' + signalResult.positionAdvice.noPosition.color">{{ signalResult.positionAdvice.noPosition.signal }}</span></h3>
          <p>{{ signalResult.positionAdvice.noPosition.advice }}</p>
        </div>
        <div :class="['advice-card', signalResult.positionAdvice.hasPosition.color]">
          <h3>💼 已持有股票建議：<span :class="'tag-' + signalResult.positionAdvice.hasPosition.color">{{ signalResult.positionAdvice.hasPosition.signal }}</span></h3>
          <p>{{ signalResult.positionAdvice.hasPosition.advice }}</p>
        </div>
      </div>

      <div class="scores">
        <div>
          <strong>RSI ({{ config.rsi.period }})</strong>
          <p>{{ signalResult.scores.rsi.description }}</p>
        </div>
        <div>
          <strong>MA{{ config.ma.shortPeriod }}/{{ config.ma.longPeriod }}</strong>
          <p>{{ signalResult.scores.ma.description }}</p>
        </div>
        <div>
          <strong>VIX</strong>
          <p>{{ signalResult.scores.vix.description }}</p>
        </div>
      </div>

      <p v-if="isBuySignal" class="buy-tag">✅ 目前為可關注買進區間</p>
    </section>

    <TradingCharts
      v-if="nasdaqRows.length && vixRows.length"
      :nasdaq-rows="nasdaqRows"
      :vix-rows="vixRows"
      :ma-short="config.ma.shortPeriod"
      :ma-long="config.ma.longPeriod"
      :rsi-period="config.rsi.period || 60"
      :rsi-oversold="config.rsi.oversold"
      :rsi-overbought="config.rsi.overbought"
      :vix-fear="config.vix.fear"
      :vix-high-fear="config.vix.highFear"
      :vix-extreme-fear="config.vix.extremeFear"
    />

    <!-- Swing Statistics Section -->
    <section v-if="swingAnalysis" class="card swing-stats">
      <h2>📊 歷史波段統計分析（2000年至今）</h2>
      <p class="swing-subtitle">共 {{ swingAnalysis.cycles.length }} 個波段（跌幅 ≥10%），分析波峰/波谷的技術指標分佈</p>

      <div class="stats-grid">
        <div class="stat-block">
          <h3>🔴 波峰（賣出參考）</h3>
          <table v-if="swingAnalysis.peakStats.rsi">
            <thead><tr><th>指標</th><th>中位數</th><th>P25</th><th>P75</th><th>範圍</th></tr></thead>
            <tbody>
              <tr>
                <td>RSI</td>
                <td>{{ swingAnalysis.peakStats.rsi.median }}</td>
                <td>{{ swingAnalysis.peakStats.rsi.p25 }}</td>
                <td>{{ swingAnalysis.peakStats.rsi.p75 }}</td>
                <td>{{ swingAnalysis.peakStats.rsi.min }} ~ {{ swingAnalysis.peakStats.rsi.max }}</td>
              </tr>
              <tr>
                <td>VIX</td>
                <td>{{ swingAnalysis.peakStats.vix?.median ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.vix?.p25 ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.vix?.p75 ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.vix ? `${swingAnalysis.peakStats.vix.min} ~ ${swingAnalysis.peakStats.vix.max}` : '-' }}</td>
              </tr>
              <tr>
                <td>MA差值%</td>
                <td>{{ swingAnalysis.peakStats.maDiffPct?.median ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.maDiffPct?.p25 ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.maDiffPct?.p75 ?? '-' }}</td>
                <td>{{ swingAnalysis.peakStats.maDiffPct ? `${swingAnalysis.peakStats.maDiffPct.min} ~ ${swingAnalysis.peakStats.maDiffPct.max}` : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="stat-block">
          <h3>🟢 波谷（買入參考）</h3>
          <table v-if="swingAnalysis.troughStats.rsi">
            <thead><tr><th>指標</th><th>中位數</th><th>P25</th><th>P75</th><th>範圍</th></tr></thead>
            <tbody>
              <tr>
                <td>RSI</td>
                <td>{{ swingAnalysis.troughStats.rsi.median }}</td>
                <td>{{ swingAnalysis.troughStats.rsi.p25 }}</td>
                <td>{{ swingAnalysis.troughStats.rsi.p75 }}</td>
                <td>{{ swingAnalysis.troughStats.rsi.min }} ~ {{ swingAnalysis.troughStats.rsi.max }}</td>
              </tr>
              <tr>
                <td>VIX</td>
                <td>{{ swingAnalysis.troughStats.vix?.median ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.vix?.p25 ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.vix?.p75 ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.vix ? `${swingAnalysis.troughStats.vix.min} ~ ${swingAnalysis.troughStats.vix.max}` : '-' }}</td>
              </tr>
              <tr>
                <td>MA差值%</td>
                <td>{{ swingAnalysis.troughStats.maDiffPct?.median ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.maDiffPct?.p25 ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.maDiffPct?.p75 ?? '-' }}</td>
                <td>{{ swingAnalysis.troughStats.maDiffPct ? `${swingAnalysis.troughStats.maDiffPct.min} ~ ${swingAnalysis.troughStats.maDiffPct.max}` : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Recommendation -->
      <div v-if="swingAnalysis.recommendation" class="recommendation">
        <h3>💡 參數建議</h3>
        <div class="rec-params">
          <span>RSI 超賣: <strong>{{ swingAnalysis.recommendation.rsi.oversold }}</strong></span>
          <span>RSI 超買: <strong>{{ swingAnalysis.recommendation.rsi.overbought }}</strong></span>
          <span>VIX 正常: <strong>{{ swingAnalysis.recommendation.vix.normal }}</strong></span>
          <span>VIX 恐慌: <strong>{{ swingAnalysis.recommendation.vix.fear }}</strong></span>
          <span>VIX 高恐慌: <strong>{{ swingAnalysis.recommendation.vix.highFear }}</strong></span>
          <span>VIX 極端: <strong>{{ swingAnalysis.recommendation.vix.extremeFear }}</strong></span>
        </div>
        <ul class="rec-reasoning">
          <li v-for="(reason, idx) in swingAnalysis.recommendation.reasoning" :key="idx">{{ reason }}</li>
        </ul>
      </div>

      <!-- Cycle Detail Table -->
      <details class="cycle-details">
        <summary>📋 各波段明細（{{ swingAnalysis.cycles.length }} 筆）</summary>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>波峰日期</th>
                <th>波峰價</th>
                <th>波谷日期</th>
                <th>波谷價</th>
                <th>跌幅</th>
                <th>下跌天數</th>
                <th>峰RSI</th>
                <th>谷RSI</th>
                <th>峰VIX</th>
                <th>谷VIX</th>
                <th>峰MA%</th>
                <th>谷MA%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in [...swingAnalysis.cycles].reverse()" :key="i">
                <td>{{ c.peakDate }}</td>
                <td>{{ c.peakPrice.toLocaleString() }}</td>
                <td>{{ c.troughDate }}</td>
                <td>{{ c.troughPrice.toLocaleString() }}</td>
                <td class="dd">{{ c.drawdown }}%</td>
                <td>{{ c.declineDays }}天</td>
                <td>{{ c.peak.rsi ?? '-' }}</td>
                <td>{{ c.trough.rsi ?? '-' }}</td>
                <td>{{ c.peak.vix ?? '-' }}</td>
                <td>{{ c.trough.vix ?? '-' }}</td>
                <td>{{ c.peak.maDiffPct ?? '-' }}</td>
                <td>{{ c.trough.maDiffPct ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </section>

    <section v-if="dataStatus" class="card data-status">{{ dataStatus }}</section>
    <section v-if="errorMessage" class="card error">{{ errorMessage }}</section>
    <section v-if="infoMessage" class="card info">{{ infoMessage }}</section>
  </main>
</template>