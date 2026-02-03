"""
Report Generator Module
產生完整的 HTML 報告（可捲動、互動式）
"""
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

import pandas as pd


class ReportGenerator:
    """
    報告產生器
    產生完整的 HTML 報告，包含圖表與分析摘要
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "output"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_full_report(
        self,
        signal_result,
        nasdaq_data: pd.DataFrame,
        vix_data: pd.DataFrame,
        backtest_metrics: Optional[Any] = None,
        chart_html: str = "",
        drawdown_zones: Optional[list] = None,
        swing_analysis: Optional[Dict] = None
    ) -> Path:
        """
        產生完整 HTML 報告
        
        Args:
            signal_result: 信號結果
            nasdaq_data: NASDAQ 資料
            vix_data: VIX 資料
            backtest_metrics: 回測績效（可選）
            chart_html: Plotly 圖表 HTML
            drawdown_zones: 下跌區間列表
            swing_analysis: 波段分析資料（可選）
        
        Returns:
            報告檔案路徑
        """
        # 計算波段分析摘要
        current_price = signal_result.nasdaq_price
        recent_high = nasdaq_data['Close'].rolling(window=252).max().iloc[-1]  # 近一年高點
        drawdown_from_high = (current_price - recent_high) / recent_high * 100
        
        # 計算距離 SMA200 的偏離
        sma200 = nasdaq_data['Close'].rolling(window=200).mean().iloc[-1]
        sma200_deviation = (current_price - sma200) / sma200 * 100
        
        # 取得關鍵指標數值
        rsi_val = signal_result.rsi_score.value
        vix_val = signal_result.vix_value
        
        # 計算波段買點分數 (0-100)
        swing_score = 0
        
        # 1. 跌幅評分 (最高 40 分)
        if drawdown_from_high <= -30:
            swing_score += 40
        elif drawdown_from_high <= -20:
            swing_score += 30
        elif drawdown_from_high <= -10:
            swing_score += 20
        elif drawdown_from_high <= -5:
            swing_score += 10
        
        # 2. RSI 評分 (最高 25 分)
        if rsi_val < 25:
            swing_score += 25
        elif rsi_val < 30:
            swing_score += 20
        elif rsi_val < 35:
            swing_score += 15
        elif rsi_val < 40:
            swing_score += 10
        
        # 3. VIX 評分 (最高 25 分)
        if vix_val > 40:
            swing_score += 25
        elif vix_val > 30:
            swing_score += 20
        elif vix_val > 25:
            swing_score += 15
        elif vix_val > 20:
            swing_score += 10
        
        # 4. SMA200 偏離評分 (最高 10 分)
        if sma200_deviation < -20:
            swing_score += 10
        elif sma200_deviation < -10:
            swing_score += 7
        elif sma200_deviation < 0:
            swing_score += 3
        
        # 生成波段投資建議
        if swing_score >= 70:
            swing_action = "🔴 強力買入"
            swing_action_detail = "歷史絕佳買點！建議投入 50-80% 資金分批進場"
        elif swing_score >= 50:
            swing_action = "🟠 積極買入"
            swing_action_detail = "重大修正買點！建議投入 30-50% 資金分批進場"
        elif swing_score >= 30:
            swing_action = "🟡 開始布局"
            swing_action_detail = "修正初期，可投入 10-30% 資金試探性買入"
        elif swing_score >= 15:
            swing_action = "⚪ 觀望等待"
            swing_action_detail = "尚未達理想買點，持續觀察等待更好機會"
        else:
            swing_action = "📈 持續觀望"
            swing_action_detail = "目前接近高點，非最佳進場時機，耐心等待修正"
        
        # 生成波段分析摘要
        swing_summary_parts = []
        
        # 1. 波段下跌情況
        if drawdown_from_high <= -30:
            swing_summary_parts.append(f"🔴 大崩盤區間！目前距近一年高點下跌 {drawdown_from_high:.1f}%，歷史經驗這是絕佳買點")
        elif drawdown_from_high <= -20:
            swing_summary_parts.append(f"🟠 重大修正中！距近一年高點下跌 {drawdown_from_high:.1f}%，可考慮分批進場")
        elif drawdown_from_high <= -10:
            swing_summary_parts.append(f"🟡 中度修正中，距近一年高點下跌 {drawdown_from_high:.1f}%，可開始關注買點")
        elif drawdown_from_high <= -5:
            swing_summary_parts.append(f"⚪ 小幅回調 {drawdown_from_high:.1f}%，尚未達 10% 修正標準")
        else:
            swing_summary_parts.append(f"📈 接近高點（距高點 {drawdown_from_high:.1f}%），目前非最佳進場時機")
        
        # 2. SMA200 偏離情況
        if sma200_deviation < -20:
            swing_summary_parts.append(f"距 SMA200 偏離 {sma200_deviation:.1f}%，極度超賣")
        elif sma200_deviation < -10:
            swing_summary_parts.append(f"距 SMA200 偏離 {sma200_deviation:.1f}%，顯著低於均線")
        elif sma200_deviation < 0:
            swing_summary_parts.append(f"價格低於 SMA200（{sma200_deviation:.1f}%）")
        else:
            swing_summary_parts.append(f"價格高於 SMA200（+{sma200_deviation:.1f}%）")
        
        # 3. 關鍵指標情況
        indicator_parts = []
        
        if rsi_val < 30:
            indicator_parts.append(f"RSI={rsi_val:.0f} 超賣")
        elif rsi_val > 70:
            indicator_parts.append(f"RSI={rsi_val:.0f} 超買")
        else:
            indicator_parts.append(f"RSI={rsi_val:.0f}")
            
        if vix_val > 30:
            indicator_parts.append(f"VIX={vix_val:.0f} 恐慌")
        elif vix_val < 15:
            indicator_parts.append(f"VIX={vix_val:.0f} 過度樂觀")
        else:
            indicator_parts.append(f"VIX={vix_val:.0f}")
        
        swing_summary_parts.append("｜".join(indicator_parts))
        
        swing_summary = "。".join(swing_summary_parts) + "。"
        
        # 信號顏色與 emoji
        signal_styles = {
            "STRONG_BUY": {"color": "#00C853", "bg": "#E8F5E9", "emoji": "🚀🚀"},
            "BUY": {"color": "#4CAF50", "bg": "#E8F5E9", "emoji": "📈"},
            "HOLD": {"color": "#FF9800", "bg": "#FFF3E0", "emoji": "⏸️"},
            "SELL": {"color": "#F44336", "bg": "#FFEBEE", "emoji": "📉"},
            "STRONG_SELL": {"color": "#D50000", "bg": "#FFEBEE", "emoji": "🔻🔻"},
        }
        
        signal_name = signal_result.signal.value
        style = signal_styles.get(signal_name, signal_styles["HOLD"])
        
        # 產生 HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>那斯達克買賣建議報告 - {signal_result.date}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
            overflow-y: auto;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #333;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header .date {{
            color: #888;
            font-size: 1.2em;
        }}
        
        .signal-card {{
            background: {style['bg']};
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        
        .signal-card .signal {{
            font-size: 3em;
            font-weight: bold;
            color: {style['color']};
            margin-bottom: 10px;
        }}
        
        .signal-card .emoji {{
            font-size: 4em;
            margin-bottom: 20px;
        }}
        
        .signal-card .score {{
            font-size: 1.5em;
            color: #333;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .card h3 {{
            color: #00d2ff;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 10px;
        }}
        
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        .stat-row:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            color: #888;
        }}
        
        .stat-value {{
            font-weight: bold;
        }}
        
        .stat-value.positive {{
            color: #4CAF50;
        }}
        
        .stat-value.negative {{
            color: #F44336;
        }}
        
        .indicator-score {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 0.9em;
            margin-left: 10px;
        }}
        
        .score-positive {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }}
        
        .score-negative {{
            background: rgba(244, 67, 54, 0.2);
            color: #F44336;
        }}
        
        .score-neutral {{
            background: rgba(255, 152, 0, 0.2);
            color: #FF9800;
        }}
        
        .recommendations {{
            background: rgba(0, 210, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        
        .recommendations h3 {{
            color: #00d2ff;
            margin-bottom: 15px;
        }}
        
        .recommendations ul {{
            list-style: none;
        }}
        
        .recommendations li {{
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }}
        
        .recommendations li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #00d2ff;
        }}
        
        .chart-container {{
            background: #fff;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            overflow: hidden;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid #333;
            margin-top: 30px;
        }}
        
        .disclaimer {{
            background: rgba(255, 152, 0, 0.1);
            border: 1px solid rgba(255, 152, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            color: #FF9800;
        }}
        
        /* 捲動條樣式 */
        ::-webkit-scrollbar {{
            width: 10px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #1a1a2e;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: #3a7bd5;
            border-radius: 5px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #00d2ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📈 那斯達克買賣建議系統</h1>
            <p class="date">報告日期：{signal_result.date} | 產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <!-- 主要信號卡片 -->
        <div class="signal-card" style="background: linear-gradient(135deg, {('#1a1a2e' if swing_score < 30 else '#1a2e1a' if swing_score >= 50 else '#2e2a1a')} 0%, #16213e 100%); border: 2px solid {('#ff6b6b' if swing_score < 30 else '#2ed573' if swing_score >= 50 else '#ffa502')};">
            <div class="emoji">{('📈' if swing_score < 30 else '🟡' if swing_score < 50 else '🟢' if swing_score < 70 else '🔵')}</div>
            <div class="signal" style="color: {('#ff6b6b' if swing_score < 30 else '#2ed573' if swing_score >= 50 else '#ffa502')};">{('WAIT' if swing_score < 30 else 'WATCH' if swing_score < 50 else 'BUY' if swing_score < 70 else 'STRONG BUY')}</div>
            <div class="score">
                波段買點分數: {swing_score}/100
            </div>
        </div>
        
        <!-- 市場概況 -->
        <div class="grid">
            <div class="card">
                <h3>📊 市場概況</h3>
                <div class="stat-row">
                    <span class="stat-label">那斯達克指數</span>
                    <span class="stat-value">{signal_result.nasdaq_price:,.2f}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">日變化</span>
                    <span class="stat-value {'positive' if signal_result.nasdaq_change >= 0 else 'negative'}">
                        {signal_result.nasdaq_change:+.2f}%
                    </span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">VIX 恐慌指數</span>
                    <span class="stat-value">{signal_result.vix_value:.2f}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">市場情緒</span>
                    <span class="stat-value">{signal_result.vix_score.sentiment}</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📈 技術指標（今日數值）</h3>
                <div class="stat-row">
                    <span class="stat-label">RSI</span>
                    <span class="stat-value">{signal_result.rsi_score.value:.1f}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">VIX</span>
                    <span class="stat-value">{signal_result.vix_value:.2f}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">MACD</span>
                    <span class="stat-value">{signal_result.macd_score.description}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">移動平均線</span>
                    <span class="stat-value">{signal_result.ma_score.description}</span>
                </div>
            </div>
        </div>
        
        <!-- 建議摘要 -->
        <div class="recommendations">
            <h3>💡 波段分析摘要</h3>
            <p style="margin-bottom: 15px;">{swing_summary}</p>
            
            <!-- 波段分數分級說明 -->
            <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="font-size: 0.9em; color: #888; margin-bottom: 10px;">📊 波段買點分數分級：</div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 0.9em;">
                    <div><span style="color: #ff6b6b;">🔴 &lt;30分</span>：不適合大資金進場</div>
                    <div><span style="color: #ffa502;">🟡 30-50分</span>：可小額試探</div>
                    <div><span style="color: #2ed573;">🟢 50-70分</span>：可分批進場</div>
                    <div><span style="color: #00d2ff;">🔵 ≥70分</span>：絕佳買點，積極進場</div>
                </div>
            </div>
            
            <!-- 今日波段操作建議 -->
            <div style="background: linear-gradient(135deg, rgba(0,210,255,0.1) 0%, rgba(58,123,213,0.1) 100%); 
                        border: 2px solid rgba(0,210,255,0.3); border-radius: 12px; padding: 20px; margin: 20px 0;">
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                    <span style="font-size: 2em;">{swing_action}</span>
                    <div>
                        <div style="font-size: 0.9em; color: #888;">波段買點分數</div>
                        <div style="font-size: 1.5em; font-weight: bold; 
                                    background: linear-gradient(90deg, #00d2ff, #3a7bd5); 
                                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                            {swing_score}/100
                        </div>
                    </div>
                </div>
                <p style="font-size: 1.1em; margin: 0; color: #ccc;">{swing_action_detail}</p>
            </div>
            
            <h3 style="margin-top: 20px;">📋 操作建議</h3>
            <ul>
                {f'<li style="color: #ff6b6b;">⚠️ 波段買點分數僅 {swing_score}/100，目前不適合大資金進場</li>' if swing_score < 30 else ''}
                {f'<li style="color: #ffa502;">🟡 波段買點分數 {swing_score}/100，可小額試探性買入，但不宜重壓</li>' if 30 <= swing_score < 50 else ''}
                {f'<li style="color: #2ed573;">🟢 波段買點分數 {swing_score}/100，修正幅度已達標準，可分批進場</li>' if 50 <= swing_score < 70 else ''}
                {f'<li style="color: #00d2ff;">🔵 波段買點分數 {swing_score}/100，歷史絕佳買點！建議積極進場</li>' if swing_score >= 70 else ''}
                <li>{'短線技術指標雖顯示買入信號，但從波段角度建議耐心等待更好的進場時機' if swing_score < 30 else '可搭配短線技術指標尋找更精準的進場點位'}</li>
                <li>此為技術分析建議，投資有風險，請依個人風險承受能力做決策</li>
            </ul>
        </div>
        
        <!-- 日期範圍選擇器 -->
        <div class="card" style="margin-bottom: 20px;">
            <h3>📅 歷史資料日期範圍</h3>
            <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin-top: 15px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <label for="startDate" style="color: #888;">起始日期:</label>
                    <input type="date" id="startDate" value="{nasdaq_data.index[0].strftime('%Y-%m-%d')}" 
                           min="{nasdaq_data.index[0].strftime('%Y-%m-%d')}" 
                           max="{nasdaq_data.index[-1].strftime('%Y-%m-%d')}"
                           style="padding: 10px 15px; border-radius: 8px; border: 1px solid #333; 
                                  background: rgba(255,255,255,0.1); color: #fff; font-size: 1em;
                                  cursor: pointer;">
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <label for="endDate" style="color: #888;">結束日期:</label>
                    <input type="date" id="endDate" value="{nasdaq_data.index[-1].strftime('%Y-%m-%d')}" 
                           min="{nasdaq_data.index[0].strftime('%Y-%m-%d')}" 
                           max="{nasdaq_data.index[-1].strftime('%Y-%m-%d')}"
                           style="padding: 10px 15px; border-radius: 8px; border: 1px solid #333; 
                                  background: rgba(255,255,255,0.1); color: #fff; font-size: 1em;
                                  cursor: pointer;">
                </div>
                <button id="applyDateRange" 
                        style="padding: 10px 25px; border-radius: 8px; border: none; 
                               background: linear-gradient(90deg, #00d2ff, #3a7bd5); color: #fff; 
                               font-size: 1em; font-weight: bold; cursor: pointer;
                               transition: transform 0.2s, box-shadow 0.2s;">
                    🔍 套用
                </button>
                <button id="resetDateRange" 
                        style="padding: 10px 25px; border-radius: 8px; border: 1px solid #666; 
                               background: transparent; color: #888; 
                               font-size: 1em; cursor: pointer;
                               transition: all 0.2s;">
                    ↺ 重置
                </button>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap;">
                <button class="quick-range-btn" data-range="1m" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近1個月
                </button>
                <button class="quick-range-btn" data-range="3m" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近3個月
                </button>
                <button class="quick-range-btn" data-range="6m" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近6個月
                </button>
                <button class="quick-range-btn" data-range="1y" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近1年
                </button>
                <button class="quick-range-btn" data-range="3y" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近3年
                </button>
                <button class="quick-range-btn" data-range="5y" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近5年
                </button>
                <button class="quick-range-btn" data-range="10y" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    近10年
                </button>
                <button class="quick-range-btn" data-range="all" 
                        style="padding: 8px 15px; border-radius: 6px; border: 1px solid #444; 
                               background: rgba(255,255,255,0.05); color: #888; cursor: pointer;">
                    全部
                </button>
            </div>
            <p id="dateRangeInfo" style="color: #00d2ff; margin-top: 10px; font-size: 0.9em;"></p>
        </div>
        
        <!-- 技術分析圖表 -->
        <div class="chart-container">
            <h3 style="color: #333; margin-bottom: 15px;">📉 技術分析圖表</h3>
            <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                🔴 紅色區域：大崩盤（跌幅 &gt; 20%）｜🟡 黃色區域：小修正（跌幅 10-20%）
            </p>
            {chart_html}
        </div>
        
        <!-- 日期範圍控制 JavaScript -->
        <script>
        (function() {{
            var minDate = '{nasdaq_data.index[0].strftime('%Y-%m-%d')}';
            var maxDate = '{nasdaq_data.index[-1].strftime('%Y-%m-%d')}';
            
            function updateDateRangeInfo() {{
                var startDate = document.getElementById('startDate').value;
                var endDate = document.getElementById('endDate').value;
                var start = new Date(startDate);
                var end = new Date(endDate);
                var days = Math.round((end - start) / (1000 * 60 * 60 * 24));
                var years = (days / 365).toFixed(1);
                document.getElementById('dateRangeInfo').textContent = 
                    '📊 顯示區間: ' + startDate + ' ~ ' + endDate + ' (共 ' + days + ' 天, 約 ' + years + ' 年)';
            }}
            
            function applyDateRange() {{
                var startDate = document.getElementById('startDate').value;
                var endDate = document.getElementById('endDate').value;
                
                if (new Date(startDate) > new Date(endDate)) {{
                    alert('起始日期不能大於結束日期！');
                    return;
                }}
                
                var plotDiv = document.querySelector('.js-plotly-plot');
                if (plotDiv) {{
                    // 先設定 X 軸範圍
                    Plotly.relayout(plotDiv, {{
                        'xaxis.range': [startDate, endDate],
                        'xaxis2.range': [startDate, endDate],
                        'xaxis3.range': [startDate, endDate]
                    }}).then(function() {{
                        // 使用 _fullData 來取得完整數據（包含 Float64Array）
                        var fullData = plotDiv._fullData;
                        if (!fullData) return;
                        
                        // 找出日期範圍的索引
                        var xData = fullData[0].x;
                        var startIdx = -1, endIdx = -1;
                        for (var i = 0; i < xData.length; i++) {{
                            var dateStr = xData[i].split('T')[0];
                            if (dateStr >= startDate && startIdx === -1) startIdx = i;
                            if (dateStr <= endDate) endIdx = i;
                        }}
                        
                        if (startIdx === -1 || endIdx === -1) return;
                        
                        // 計算各 Y 軸的範圍
                        var yRanges = {{y1: [], y2: [], y3: []}};
                        
                        fullData.forEach(function(trace) {{
                            var yaxis = trace.yaxis || 'y';
                            var yKey = yaxis === 'y2' ? 'y2' : yaxis === 'y3' ? 'y3' : 'y1';
                            
                            // 處理 candlestick 類型（有 high/low）
                            if (trace.type === 'candlestick' || trace.type === 'ohlc') {{
                                if (trace.high && trace.low) {{
                                    for (var i = startIdx; i <= endIdx; i++) {{
                                        var highVal = typeof trace.high[i] === 'number' ? trace.high[i] : parseFloat(trace.high[i]);
                                        var lowVal = typeof trace.low[i] === 'number' ? trace.low[i] : parseFloat(trace.low[i]);
                                        if (!isNaN(highVal)) yRanges[yKey].push(highVal);
                                        if (!isNaN(lowVal)) yRanges[yKey].push(lowVal);
                                    }}
                                }}
                            }}
                            // 處理一般折線圖（有 y 屬性）
                            else if (trace.y) {{
                                for (var i = startIdx; i <= endIdx; i++) {{
                                    if (trace.y[i] != null && !isNaN(trace.y[i])) {{
                                        var yVal = typeof trace.y[i] === 'number' ? trace.y[i] : parseFloat(trace.y[i]);
                                        if (!isNaN(yVal)) yRanges[yKey].push(yVal);
                                    }}
                                }}
                            }}
                        }});
                        
                        // 計算每個 Y 軸的範圍（加上 5% 的邊距）
                        var layoutUpdate = {{}};
                        ['y1', 'y2', 'y3'].forEach(function(yKey, idx) {{
                            if (yRanges[yKey].length > 0) {{
                                var minY = Math.min.apply(null, yRanges[yKey]);
                                var maxY = Math.max.apply(null, yRanges[yKey]);
                                var padding = (maxY - minY) * 0.05;
                                if (padding === 0) padding = maxY * 0.05;  // 防止 padding 為 0
                                var axisName = idx === 0 ? 'yaxis' : 'yaxis' + (idx + 1);
                                layoutUpdate[axisName + '.range'] = [minY - padding, maxY + padding];
                            }}
                        }});
                        
                        if (Object.keys(layoutUpdate).length > 0) {{
                            Plotly.relayout(plotDiv, layoutUpdate);
                        }}
                    }});
                }}
                
                updateDateRangeInfo();
            }}
            
            function resetDateRange() {{
                document.getElementById('startDate').value = minDate;
                document.getElementById('endDate').value = maxDate;
                applyDateRange();
            }}
            
            function setQuickRange(range) {{
                var endDate = new Date(maxDate);
                var startDate = new Date(maxDate);
                
                switch(range) {{
                    case '1m':
                        startDate.setMonth(startDate.getMonth() - 1);
                        break;
                    case '3m':
                        startDate.setMonth(startDate.getMonth() - 3);
                        break;
                    case '6m':
                        startDate.setMonth(startDate.getMonth() - 6);
                        break;
                    case '1y':
                        startDate.setFullYear(startDate.getFullYear() - 1);
                        break;
                    case '3y':
                        startDate.setFullYear(startDate.getFullYear() - 3);
                        break;
                    case '5y':
                        startDate.setFullYear(startDate.getFullYear() - 5);
                        break;
                    case '10y':
                        startDate.setFullYear(startDate.getFullYear() - 10);
                        break;
                    case 'all':
                        startDate = new Date(minDate);
                        break;
                }}
                
                // 確保不超出資料範圍
                if (startDate < new Date(minDate)) {{
                    startDate = new Date(minDate);
                }}
                
                document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
                document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
                applyDateRange();
            }}
            
            // 綁定事件
            document.getElementById('applyDateRange').addEventListener('click', applyDateRange);
            document.getElementById('resetDateRange').addEventListener('click', resetDateRange);
            
            // 快速選擇按鈕
            document.querySelectorAll('.quick-range-btn').forEach(function(btn) {{
                btn.addEventListener('click', function() {{
                    setQuickRange(this.getAttribute('data-range'));
                    
                    // 更新按鈕樣式
                    document.querySelectorAll('.quick-range-btn').forEach(function(b) {{
                        b.style.background = 'rgba(255,255,255,0.05)';
                        b.style.color = '#888';
                        b.style.borderColor = '#444';
                    }});
                    this.style.background = 'linear-gradient(90deg, #00d2ff, #3a7bd5)';
                    this.style.color = '#fff';
                    this.style.borderColor = '#00d2ff';
                }});
                
                // hover 效果
                btn.addEventListener('mouseenter', function() {{
                    if (this.style.color !== 'rgb(255, 255, 255)') {{
                        this.style.background = 'rgba(255,255,255,0.1)';
                        this.style.color = '#fff';
                    }}
                }});
                btn.addEventListener('mouseleave', function() {{
                    if (this.style.borderColor !== 'rgb(0, 210, 255)') {{
                        this.style.background = 'rgba(255,255,255,0.05)';
                        this.style.color = '#888';
                    }}
                }});
            }});
            
            // 套用按鈕 hover 效果
            var applyBtn = document.getElementById('applyDateRange');
            applyBtn.addEventListener('mouseenter', function() {{
                this.style.transform = 'scale(1.05)';
                this.style.boxShadow = '0 5px 20px rgba(0, 210, 255, 0.4)';
            }});
            applyBtn.addEventListener('mouseleave', function() {{
                this.style.transform = 'scale(1)';
                this.style.boxShadow = 'none';
            }});
            
            // 初始化顯示
            updateDateRangeInfo();
        }})();
        </script>
        
        {self._generate_drawdown_section(drawdown_zones) if drawdown_zones else ''}
        
        {self._generate_swing_analysis_section(swing_analysis) if swing_analysis else ''}
        
        {self._generate_backtest_section(backtest_metrics) if backtest_metrics else ''}
        
        <footer class="footer">
            <div class="disclaimer">
                ⚠️ 免責聲明：本報告僅供技術分析參考，不構成任何投資建議。投資有風險，請依個人風險承受能力做決策。過去績效不代表未來表現。
            </div>
            <p style="margin-top: 20px;">那斯達克買賣建議系統 v1.0 | Powered by Python + Plotly</p>
        </footer>
    </div>
</body>
</html>
        """
        
        # 儲存報告
        report_path = self.output_dir / f"report_{signal_result.date}.html"
        report_path.write_text(html_content, encoding='utf-8')
        
        return report_path
    
    def _generate_backtest_section(self, metrics) -> str:
        """產生回測績效區塊"""
        return f"""
        <div class="card" style="margin-bottom: 30px;">
            <h3>📊 策略回測績效</h3>
            <div class="grid" style="grid-template-columns: repeat(3, 1fr);">
                <div>
                    <div class="stat-row">
                        <span class="stat-label">總報酬率</span>
                        <span class="stat-value {'positive' if metrics.total_return > 0 else 'negative'}">{metrics.total_return:+.2f}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">年化報酬率</span>
                        <span class="stat-value">{metrics.annualized_return:+.2f}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">超額報酬</span>
                        <span class="stat-value {'positive' if metrics.excess_return > 0 else 'negative'}">{metrics.excess_return:+.2f}%</span>
                    </div>
                </div>
                <div>
                    <div class="stat-row">
                        <span class="stat-label">夏普比率</span>
                        <span class="stat-value">{metrics.sharpe_ratio:.3f}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">最大回撤</span>
                        <span class="stat-value negative">{metrics.max_drawdown:.2f}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">波動率</span>
                        <span class="stat-value">{metrics.volatility:.2f}%</span>
                    </div>
                </div>
                <div>
                    <div class="stat-row">
                        <span class="stat-label">總交易次數</span>
                        <span class="stat-value">{metrics.total_trades}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">勝率</span>
                        <span class="stat-value">{metrics.win_rate:.1f}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">獲利因子</span>
                        <span class="stat-value">{metrics.profit_factor:.2f}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_drawdown_section(self, drawdown_zones: list) -> str:
        """產生下跌區間摘要區塊"""
        if not drawdown_zones:
            return ""
        
        rows_html = ""
        for i, zone in enumerate(drawdown_zones, 1):
            peak_date = zone['peak_date'].strftime('%Y-%m-%d') if hasattr(zone['peak_date'], 'strftime') else str(zone['peak_date'])[:10]
            trough_date = zone['trough_date'].strftime('%Y-%m-%d') if hasattr(zone['trough_date'], 'strftime') else str(zone['trough_date'])[:10]
            
            # 根據跌幅決定顏色：大崩盤(>20%)紅色，小修正(10-20%)黃色
            drawdown_pct = abs(zone['drawdown'])
            if drawdown_pct > 0.20:
                drawdown_color = "#F44336"  # 紅色 - 大崩盤
                drawdown_label = "🔴"
            else:
                drawdown_color = "#FFC107"  # 黃色 - 小修正
                drawdown_label = "🟡"
            
            rows_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{i}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{peak_date}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{trough_date}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{zone['duration_days']} 天</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{zone['peak_price']:,.0f}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{zone['trough_price']:,.0f}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); color: {drawdown_color}; font-weight: bold;">{drawdown_label} {zone['drawdown']:.1%}</td>
            </tr>
            """
        
        return f"""
        <div class="card" style="margin-bottom: 30px;">
            <h3>📉 下跌區間摘要（跌幅超過 10%）</h3>
            <p style="color: #888; margin-bottom: 15px;">🔴 大崩盤（跌幅 &gt; 20%）｜🟡 小修正（跌幅 10-20%）</p>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; color: #fff;">
                    <thead>
                        <tr style="background: rgba(255,255,255,0.1);">
                            <th style="padding: 12px; text-align: left;">#</th>
                            <th style="padding: 12px; text-align: left;">高點日期</th>
                            <th style="padding: 12px; text-align: left;">低點日期</th>
                            <th style="padding: 12px; text-align: left;">持續時間</th>
                            <th style="padding: 12px; text-align: left;">高點價格</th>
                            <th style="padding: 12px; text-align: left;">低點價格</th>
                            <th style="padding: 12px; text-align: left;">最大跌幅</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <p style="color: #FF9800; margin-top: 15px; font-size: 0.9em;">
                💡 提示：下跌超過 10% 通常代表市場進入調整或修正階段，可能是加碼或建立新部位的潛在時機
            </p>
        </div>
        """

    def _generate_swing_analysis_section(self, swing_analysis: Dict) -> str:
        """產生波段分析與大資金進場策略區塊"""
        if not swing_analysis:
            return ""
        
        import numpy as np
        
        indicator_analysis = swing_analysis.get('indicator_analysis', {})
        entry_signals = swing_analysis.get('entry_signals', {})
        stats = indicator_analysis.get('statistics', {})
        major = indicator_analysis.get('major_crash_indicators', {})
        minor = indicator_analysis.get('minor_correction_indicators', {})
        
        # 預先格式化大崩盤指標
        major_rsi = f"{major.get('avg_rsi'):.1f}" if major.get('avg_rsi') else "N/A"
        major_vix = f"{major.get('avg_vix'):.1f}" if major.get('avg_vix') else "N/A"
        major_sma = f"{major.get('avg_dist_sma200'):.1f}%" if major.get('avg_dist_sma200') else "N/A"
        
        # 預先格式化小修正指標
        minor_rsi = f"{minor.get('avg_rsi'):.1f}" if minor.get('avg_rsi') else "N/A"
        minor_vix = f"{minor.get('avg_vix'):.1f}" if minor.get('avg_vix') else "N/A"
        minor_sma = f"{minor.get('avg_dist_sma200'):.1f}%" if minor.get('avg_dist_sma200') else "N/A"
        
        # 歷史買點表格 (顯示全部)
        historical_rows = ""
        for point in entry_signals.get('historical_entry_points', []):
            rsi_str = f"{point['rsi']:.1f}" if point.get('rsi') and not np.isnan(point['rsi']) else "N/A"
            vix_str = f"{point['vix']:.1f}" if point.get('vix') and not np.isnan(point['vix']) else "N/A"
            # 根據跌幅決定顏色：大崩盤(>20%)紅色，小修正(10-20%)黃色
            drawdown_pct = abs(point['drawdown'])
            if drawdown_pct > 0.20:
                drawdown_color = "#F44336"  # 紅色 - 大崩盤
                drawdown_label = "🔴"
            else:
                drawdown_color = "#FFC107"  # 黃色 - 小修正
                drawdown_label = "🟡"
            historical_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{point['date']}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); color: {drawdown_color}; font-weight: bold;">{drawdown_label} {point['drawdown']*100:.1f}%</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{rsi_str}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">{vix_str}</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); color: #4CAF50;">{point['recovery']}</td>
            </tr>
            """
        
        # 進場策略卡片
        entry_cards = ""
        entry_conditions = entry_signals.get('entry_conditions', {})
        entry_prices = entry_signals.get('entry_prices', {})
        
        strategy_colors = {
            'aggressive': {'bg': 'rgba(255, 193, 7, 0.15)', 'border': '#FFC107', 'icon': '🟡'},
            'moderate': {'bg': 'rgba(255, 152, 0, 0.15)', 'border': '#FF9800', 'icon': '🟠'},
            'conservative': {'bg': 'rgba(244, 67, 54, 0.15)', 'border': '#F44336', 'icon': '🔴'},
        }
        
        for key, condition in entry_conditions.items():
            colors = strategy_colors.get(key, {'bg': 'rgba(255,255,255,0.1)', 'border': '#666', 'icon': '⚪'})
            prices = entry_prices.get(key, {})
            
            conditions_html = "".join([f"<li style='padding: 5px 0;'>✓ {c}</li>" for c in condition.get('conditions', [])])
            
            entry_cards += f"""
            <div style="background: {colors['bg']}; border: 1px solid {colors['border']}; border-radius: 15px; padding: 25px; margin-bottom: 20px;">
                <h4 style="color: {colors['border']}; margin-bottom: 15px; font-size: 1.3em;">
                    {colors['icon']} {condition.get('name', '')}
                </h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <p style="color: #888; margin-bottom: 10px;">📉 下跌區間: <strong style="color: #fff;">{condition.get('drawdown_range', '')}</strong></p>
                        <p style="color: #888; margin-bottom: 10px;">🎯 信心度: <strong style="color: #fff;">{condition.get('confidence', '')}</strong></p>
                        <p style="color: #888; margin-bottom: 10px;">⚠️ 風險: <strong style="color: #fff;">{condition.get('risk', '')}</strong></p>
                        <p style="color: #888; margin-bottom: 10px;">💰 建議資金: <strong style="color: #4CAF50;">{condition.get('position_size', '')}</strong></p>
                    </div>
                    <div>
                        <p style="color: #888; margin-bottom: 10px;">📍 觸發價位: <strong style="color: #00d2ff; font-size: 1.2em;">{prices.get('trigger_price', 0):,.0f}</strong></p>
                        <p style="color: #888; margin-bottom: 10px;">🎯 目標均價: <strong style="color: #00d2ff; font-size: 1.2em;">{prices.get('target_avg_price', 0):,.0f}</strong></p>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <p style="color: #888; margin-bottom: 8px;">進場條件:</p>
                    <ul style="list-style: none; padding-left: 10px; color: #fff;">
                        {conditions_html}
                    </ul>
                </div>
            </div>
            """
        
        # 關鍵洞察
        insights_html = ""
        for insight in entry_signals.get('key_insights', []):
            insights_html += f"<li style='padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'>{insight}</li>"
        
        return f"""
        <div style="margin-bottom: 30px;">
            <h2 style="color: #00d2ff; text-align: center; margin-bottom: 30px; font-size: 1.8em;">
                💰 波段分析與大資金進場策略
            </h2>
            
            <!-- 大崩盤 vs 小修正比較 -->
            <div class="card" style="margin-bottom: 30px;">
                <h3>🔴 大崩盤 vs 🟡 小修正 指標比較</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                    <div style="background: rgba(244, 67, 54, 0.1); border: 1px solid #F44336; border-radius: 10px; padding: 20px;">
                        <h4 style="color: #F44336; margin-bottom: 15px;">🔴 大崩盤 (跌幅 &gt; 20%)</h4>
                        <p style="color: #fff; font-size: 1.5em; margin-bottom: 10px;">{major.get('count', 0)} 次</p>
                        <p style="color: #888;">平均 RSI: <strong style="color: #fff;">{major_rsi}</strong></p>
                        <p style="color: #888;">平均 VIX: <strong style="color: #fff;">{major_vix}</strong></p>
                        <p style="color: #888;">平均距 SMA200: <strong style="color: #fff;">{major_sma}</strong></p>
                    </div>
                    <div style="background: rgba(255, 193, 7, 0.1); border: 1px solid #FFC107; border-radius: 10px; padding: 20px;">
                        <h4 style="color: #FFC107; margin-bottom: 15px;">🟡 小修正 (跌幅 10-20%)</h4>
                        <p style="color: #fff; font-size: 1.5em; margin-bottom: 10px;">{minor.get('count', 0)} 次</p>
                        <p style="color: #888;">平均 RSI: <strong style="color: #fff;">{minor_rsi}</strong></p>
                        <p style="color: #888;">平均 VIX: <strong style="color: #fff;">{minor_vix}</strong></p>
                        <p style="color: #888;">平均距 SMA200: <strong style="color: #fff;">{minor_sma}</strong></p>
                    </div>
                </div>
            </div>
            
            <!-- 指標統計 -->
            <div class="card" style="margin-bottom: 30px;">
                <h3>📊 波段低點指標統計 (2000年至今，共 {major.get('count', 0) + minor.get('count', 0)} 次波段修正)</h3>
                <p style="color: #888; margin-bottom: 20px;">分析歷史上所有跌幅超過 10% 的波段低點時，各項技術指標數值</p>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                    <!-- RSI -->
                    <div style="background: rgba(33, 150, 243, 0.1); border: 1px solid #2196F3; border-radius: 10px; padding: 20px; text-align: center;">
                        <h4 style="color: #2196F3; margin-bottom: 10px;">📈 RSI</h4>
                        <p style="font-size: 2em; font-weight: bold; color: #fff; margin: 10px 0;">
                            {stats.get('rsi', {}).get('median', 0):.1f}
                        </p>
                        <p style="color: #888; font-size: 0.9em;">中位數</p>
                        <p style="color: #666; font-size: 0.8em; margin-top: 10px;">
                            範圍: {stats.get('rsi', {}).get('min', 0):.1f} ~ {stats.get('rsi', {}).get('max', 0):.1f}
                        </p>
                        <p style="color: #4CAF50; font-size: 0.85em; margin-top: 10px;">
                            💡 RSI &lt; {stats.get('rsi', {}).get('median', 30):.0f} 是買點
                        </p>
                    </div>
                    
                    <!-- VIX -->
                    <div style="background: rgba(156, 39, 176, 0.1); border: 1px solid #9C27B0; border-radius: 10px; padding: 20px; text-align: center;">
                        <h4 style="color: #9C27B0; margin-bottom: 10px;">😱 VIX</h4>
                        <p style="font-size: 2em; font-weight: bold; color: #fff; margin: 10px 0;">
                            {stats.get('vix', {}).get('median', 0):.1f}
                        </p>
                        <p style="color: #888; font-size: 0.9em;">中位數</p>
                        <p style="color: #666; font-size: 0.8em; margin-top: 10px;">
                            範圍: {stats.get('vix', {}).get('min', 0):.1f} ~ {stats.get('vix', {}).get('max', 0):.1f}
                        </p>
                        <p style="color: #4CAF50; font-size: 0.85em; margin-top: 10px;">
                            💡 VIX &gt; {stats.get('vix', {}).get('median', 30):.0f} 是恐慌買點
                        </p>
                    </div>
                    
                    <!-- 距離 SMA200 -->
                    <div style="background: rgba(255, 152, 0, 0.1); border: 1px solid #FF9800; border-radius: 10px; padding: 20px; text-align: center;">
                        <h4 style="color: #FF9800; margin-bottom: 10px;">📉 距 SMA200</h4>
                        <p style="font-size: 2em; font-weight: bold; color: #fff; margin: 10px 0;">
                            {stats.get('distance_sma200', {}).get('median', 0):.1f}%
                        </p>
                        <p style="color: #888; font-size: 0.9em;">中位數偏離</p>
                        <p style="color: #666; font-size: 0.8em; margin-top: 10px;">
                            最大偏離: {stats.get('distance_sma200', {}).get('min', 0):.1f}%
                        </p>
                        <p style="color: #4CAF50; font-size: 0.85em; margin-top: 10px;">
                            💡 跌破 SMA200 &gt;10% 是強買點
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- 歷史絕佳買點 -->
            <div class="card" style="margin-bottom: 30px;">
                <h3>📅 歷史絕佳買點回顧 (跌幅 &gt; 10%)</h3>
                <p style="color: #888; margin-bottom: 15px;">
                    這些時刻是歷史上最好的大資金進場時機，事後都證明是絕佳買點<br>
                    <span style="color: #F44336;">🔴 紅色：大崩盤（跌幅 &gt; 20%）</span>｜
                    <span style="color: #FFC107;">🟡 黃色：小修正（跌幅 10-20%）</span>
                </p>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; color: #fff;">
                        <thead>
                            <tr style="background: rgba(255,255,255,0.1);">
                                <th style="padding: 12px; text-align: left;">日期</th>
                                <th style="padding: 12px; text-align: left;">跌幅</th>
                                <th style="padding: 12px; text-align: left;">RSI</th>
                                <th style="padding: 12px; text-align: left;">VIX</th>
                                <th style="padding: 12px; text-align: left;">結果</th>
                            </tr>
                        </thead>
                        <tbody>
                            {historical_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- 大資金進場策略 -->
            <div style="margin-bottom: 30px;">
                <h3 style="color: #00d2ff; margin-bottom: 20px; text-align: center;">🎯 大資金進場策略建議</h3>
                {entry_cards}
            </div>
            
            <!-- 關鍵投資洞察 -->
            <div class="card" style="margin-bottom: 30px; background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.3);">
                <h3>💡 關鍵投資洞察</h3>
                <ul style="list-style: none; padding: 0; margin-top: 15px;">
                    {insights_html}
                </ul>
            </div>
            
            <!-- 大資金進場原則 -->
            <div class="card" style="background: linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(33, 150, 243, 0.1)); border: 1px solid rgba(76, 175, 80, 0.3);">
                <h3 style="color: #4CAF50;">💰 大資金進場核心原則</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 20px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5em;">1️⃣</span>
                        <span>分批進場，不要一次 ALL IN</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5em;">2️⃣</span>
                        <span>越跌越買，採用定期定額 + 加碼策略</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5em;">3️⃣</span>
                        <span>設定明確的進場價位和資金配置</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5em;">4️⃣</span>
                        <span>保持長期投資心態，不因短期波動恐慌</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5em;">5️⃣</span>
                        <span>只用閒置資金投資，不影響生活</span>
                    </div>
                </div>
            </div>
        </div>
        """
