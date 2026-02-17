# 股票買進通知系統（Vue + JavaScript + Vite）

這個專案已改寫為**純前端**版本：

- 前端技術：Vue 3 + Vite
- 指標策略：RSI + MACD + MA + VIX 加權分數
- 通知方式：瀏覽器通知（可在 iPhone 加入主畫面後使用）
- 安裝方式：PWA（Progressive Web App）

## 功能

- 讀取 CSV（NASDAQ + VIX）並計算最新買賣訊號
- 產生 `STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL`
- 可調整 RSI、MA 與各權重參數
- 可設定每日提醒時間（App 開啟時會檢查）
- 可安裝到 iPhone 主畫面

## 啟動

```bash
npm install
npm run dev
```

本機預設網址（Vite）：

```bash
http://localhost:5173
```

## 建置

```bash
npm run build
npm run preview
```

## iPhone 安裝（PWA）

1. 用 Safari 開啟網站
2. 點選分享按鈕
3. 選擇「加入主畫面」
4. 從主畫面開啟 App
5. 在 App 內按「啟用通知權限」

## 重要限制（純前端）

- 無後端推播服務時，通知提醒需在 App 開啟狀態下檢查。
- 若要背景推播（即使 App 未開啟也通知），需另外加上 Push Server。

## 資料來源

預設讀取：

- `public/data/raw/nasdaq_2000.csv`
- `public/data/raw/vix_2000.csv`

你可在 UI 直接改成其他可跨網域讀取的 CSV URL。

## 專案結構（前端）

```
buyStock/
├── index.html
├── package.json
├── vite.config.js
├── public/
│   ├── favicon.svg
│   ├── icons/
│   └── data/raw/
└── src/
    ├── App.vue
    ├── main.js
    ├── style.css
    └── lib/
        ├── dataLoader.js
        ├── indicators.js
        ├── notifier.js
        └── signalEngine.js
```

## 免責聲明

本系統僅供技術分析與學習用途，不構成投資建議。
