# 那斯達克買賣建議系統 (NASDAQ Trading Advisor)

一個整合 VIX 恐慌指數、RSI、MACD 和移動平均線的多指標交易建議系統。

## 功能特色

- 📊 **多指標整合**：結合 RSI、MACD、移動平均線與 VIX 恐慌指數
- 🎯 **智慧信號**：產生 STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL 五級建議
- 📈 **策略回測**：驗證歷史績效，計算 Sharpe Ratio、最大回撤等指標
- 📱 **互動式報告**：支援縮放、捲動的 HTML 報告，完整 2000 年至今數據
- 💰 **波段分析**：大資金進場策略與指標相關性分析
- ⏰ **定時排程**：每日自動執行分析並發送提醒

## 快速開始

### 1. 安裝依賴

```bash
cd buyStock
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的設定
```

### 3. 執行分析

```bash
# 產生互動式 HTML 報告（預設）
python main.py

# 下載最新資料
python main.py --download

# 執行策略回測
python main.py --backtest

# 執行波段分析
python main.py --analyze

# 顯示系統狀態
python main.py --status
```

## 專案結構

```
buyStock/
├── config/                 # 設定模組
│   ├── __init__.py
│   └── settings.py         # 系統設定
│
├── data/                   # 資料模組
│   ├── __init__.py
│   ├── fetcher.py          # 資料下載 (yfinance)
│   └── raw/                # 儲存下載的 CSV
│
├── indicators/             # 技術指標模組
│   ├── __init__.py
│   ├── technical.py        # RSI, MACD, MA 計算
│   ├── vix_indicator.py    # VIX 恐慌指數分析
│   └── combined_signals.py # 多指標評分系統
│
├── analysis/               # 波段分析模組
│   ├── __init__.py
│   └── swing_analyzer.py   # 歷史波段分析與進場策略
│
├── visualization/          # 視覺化模組
│   ├── __init__.py
│   ├── charts.py           # 圖表生成
│   └── report.py           # HTML 報告生成
│
├── backtesting/            # 回測模組
│   ├── __init__.py
│   ├── runner.py           # 回測執行器
│   └── metrics.py          # 績效指標計算
│
├── notifications/          # 通知模組（可選）
│   ├── __init__.py
│   ├── base.py             # 通知器介面
│   ├── line_notifier.py    # LINE Messaging API
│   ├── email_notifier.py   # Email (Gmail SMTP)
│   └── notification_manager.py
│
├── output/                 # 輸出目錄
│   └── report_*.html       # 互動式 HTML 報告
│
├── main.py                 # 主程式入口
├── scheduler.py            # 排程器
├── requirements.txt
├── .env.example            # 環境變數範本
└── .gitignore
```

## 技術指標說明

### RSI (相對強弱指標)

- RSI < 30：超賣，買入信號
- RSI > 70：超買，賣出信號

### MACD (移動平均收斂發散)

- 金叉 (MACD > Signal)：買入信號
- 死叉 (MACD < Signal)：賣出信號

### 移動平均線

- 黃金交叉 (SMA50 > SMA200)：多頭趨勢
- 死亡交叉 (SMA50 < SMA200)：空頭趨勢

### VIX 恐慌指數 (逆向指標)

| VIX 範圍 | 市場情緒 | 信號           |
| -------- | -------- | -------------- |
| < 12     | 極度樂觀 | 謹慎 (SELL)    |
| 12-20    | 正常     | 中性 (HOLD)    |
| 20-25    | 輕度恐懼 | 觀望           |
| 25-30    | 恐懼     | 買入機會 (BUY) |
| 30-40    | 高度恐懼 | 強烈買入       |
| > 40     | 極度恐慌 | 歷史級買點     |

## 通知設定

### LINE Messaging API

1. 到 [LINE Developers Console](https://developers.line.biz/console/) 建立 Messaging API Channel
2. 取得 Channel Access Token
3. 設定 Webhook 取得用戶的 LINE User ID
4. 在 `.env` 設定：
   ```
   LINE_CHANNEL_ACCESS_TOKEN=xxx
   LINE_USER_ID=xxx
   ```

### Email (Gmail)

1. 啟用 Google 帳戶的兩步驟驗證
2. 到 Google 帳戶 → 安全性 → 應用程式密碼
3. 建立應用程式密碼
4. 在 `.env` 設定：
   ```
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_APP_PASSWORD=your-app-password
   EMAIL_RECIPIENT=recipient@example.com
   ```

## 排程執行

### 使用內建排程器

```bash
# 啟動排程器 (預設使用 schedule)
python scheduler.py

# 立即執行一次
python scheduler.py --run-now

# 使用 APScheduler
python scheduler.py --scheduler apscheduler
```

### 使用系統 Cron (Linux/macOS)

```bash
# 編輯 crontab
crontab -e

# 每日早上 6:00 執行 (美股收盤後)
0 6 * * * cd /path/to/buyStock && /path/to/python main.py --notify >> /path/to/cron.log 2>&1
```

## 回測績效指標

| 指標          | 良好標準 | 說明             |
| ------------- | -------- | ---------------- |
| Sharpe Ratio  | > 1.0    | 風險調整後報酬   |
| Sortino Ratio | > 1.5    | 下行風險調整報酬 |
| Max Drawdown  | < 20%    | 最大回撤         |
| Win Rate      | > 40%    | 勝率             |
| Profit Factor | > 1.5    | 獲利因子         |

## 免責聲明

⚠️ **本系統僅供技術分析參考，不構成任何投資建議。**

- 過去績效不代表未來表現
- 投資有風險，請依個人風險承受能力做決策
- 建議搭配基本面分析與個人研究

## License

MIT License
