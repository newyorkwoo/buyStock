"""
Chart Generator Module
產生價格走勢圖、技術指標圖表
"""
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

# 設定中文字型
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'PingFang TC', 'Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

# 嘗試匯入 plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class ChartGenerator:
    """
    圖表產生器
    產生那斯達克指數與技術指標的視覺化圖表
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化圖表產生器
        
        Args:
            output_dir: 圖表輸出目錄
        """
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "output"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_drawdown_zones(
        self,
        df: pd.DataFrame,
        threshold: float = 0.10
    ) -> list:
        """
        找出下跌超過指定閾值的區間（相對於近期高點）
        
        使用獨立週期偵測算法：
        - 當價格從低點反彈超過 50% 時，視為一個新的市場週期開始
        - 每個週期獨立計算跌幅
        
        Args:
            df: 價格資料 DataFrame
            threshold: 下跌閾值 (預設 0.15 = 15%)
            
        Returns:
            list of dict: 每個區間包含 start, end, peak_price, trough_price, drawdown
        """
        close = df['Close'].values
        dates = df.index
        
        zones = []
        n = len(close)
        
        if n < 2:
            return zones
        
        # 追蹤當前週期的高低點
        cycle_peak = close[0]
        cycle_peak_idx = 0
        cycle_trough = close[0]
        cycle_trough_idx = 0
        in_drawdown = False
        drawdown_start_idx = 0
        
        for i in range(n):
            current_price = close[i]
            
            # 更新週期內的高低點
            if current_price > cycle_peak:
                # 創新高
                if in_drawdown:
                    # 結束當前下跌區間（因為價格已經完全回復並創新高）
                    max_dd = (cycle_trough - self._get_peak_at_start(close, drawdown_start_idx, cycle_trough_idx)) / self._get_peak_at_start(close, drawdown_start_idx, cycle_trough_idx)
                    if max_dd <= -threshold:
                        peak_val = self._get_peak_at_start(close, drawdown_start_idx, cycle_trough_idx)
                        zones.append({
                            'start': dates[drawdown_start_idx],
                            'end': dates[cycle_trough_idx],
                            'peak_date': dates[drawdown_start_idx],
                            'trough_date': dates[cycle_trough_idx],
                            'peak_price': peak_val,
                            'trough_price': cycle_trough,
                            'drawdown': (cycle_trough - peak_val) / peak_val,
                            'duration_days': (dates[cycle_trough_idx] - dates[drawdown_start_idx]).days
                        })
                    in_drawdown = False
                
                cycle_peak = current_price
                cycle_peak_idx = i
                cycle_trough = current_price
                cycle_trough_idx = i
                
            elif current_price < cycle_trough:
                # 創新低
                cycle_trough = current_price
                cycle_trough_idx = i
            
            # 計算當前回撤（相對於週期高點）
            current_dd = (current_price - cycle_peak) / cycle_peak
            
            # 檢查是否進入下跌區間
            if current_dd <= -threshold and not in_drawdown:
                in_drawdown = True
                drawdown_start_idx = cycle_peak_idx
            
            # 檢查是否從低點大幅反彈（開始新週期）
            if cycle_trough > 0:
                recovery = (current_price - cycle_trough) / cycle_trough
                if recovery > 0.50 and in_drawdown:
                    # 從低點反彈超過 50%，視為新週期開始
                    # 結束當前下跌區間
                    peak_val = self._get_peak_at_start(close, drawdown_start_idx, cycle_trough_idx)
                    max_dd = (cycle_trough - peak_val) / peak_val
                    if max_dd <= -threshold:
                        zones.append({
                            'start': dates[drawdown_start_idx],
                            'end': dates[cycle_trough_idx],
                            'peak_date': dates[drawdown_start_idx],
                            'trough_date': dates[cycle_trough_idx],
                            'peak_price': peak_val,
                            'trough_price': cycle_trough,
                            'drawdown': max_dd,
                            'duration_days': (dates[cycle_trough_idx] - dates[drawdown_start_idx]).days
                        })
                    
                    # 開始新週期
                    in_drawdown = False
                    cycle_peak = current_price
                    cycle_peak_idx = i
                    cycle_trough = current_price
                    cycle_trough_idx = i
        
        # 處理結束時仍在下跌區間的情況
        if in_drawdown:
            peak_val = self._get_peak_at_start(close, drawdown_start_idx, cycle_trough_idx)
            max_dd = (cycle_trough - peak_val) / peak_val
            if max_dd <= -threshold:
                zones.append({
                    'start': dates[drawdown_start_idx],
                    'end': dates[cycle_trough_idx],
                    'peak_date': dates[drawdown_start_idx],
                    'trough_date': dates[cycle_trough_idx],
                    'peak_price': peak_val,
                    'trough_price': cycle_trough,
                    'drawdown': max_dd,
                    'duration_days': (dates[cycle_trough_idx] - dates[drawdown_start_idx]).days
                })
        
        # 按低點日期降序排列，最新的在最前面
        zones.sort(key=lambda x: x['trough_date'], reverse=True)
        
        return zones
    
    def _get_peak_at_start(self, close: np.ndarray, start_idx: int, end_idx: int) -> float:
        """取得區間起點附近的高點"""
        # 通常 start_idx 就是高點位置
        return close[start_idx]
    
    def plot_full_analysis(
        self,
        df: pd.DataFrame,
        signal_result=None,
        days: int = 120,
        save: bool = True,
        show: bool = True
    ) -> Optional[str]:
        """
        產生完整分析圖表
        
        包含：價格走勢、移動平均線、RSI、MACD、VIX
        
        Args:
            df: 包含技術指標的 DataFrame
            signal_result: 信號結果物件
            days: 顯示最近幾天
            save: 是否儲存圖片
            show: 是否顯示圖表
            
        Returns:
            儲存的檔案路徑
        """
        # 取最近 N 天資料
        df_plot = df.tail(days).copy()
        
        # 建立圖表 (4 個子圖)
        fig, axes = plt.subplots(4, 1, figsize=(14, 12), 
                                  gridspec_kw={'height_ratios': [3, 1, 1, 1]})
        fig.suptitle('那斯達克綜合指數 技術分析', fontsize=16, fontweight='bold')
        
        # 1. 價格與移動平均線
        ax1 = axes[0]
        ax1.plot(df_plot.index, df_plot['Close'], label='收盤價', color='#2196F3', linewidth=1.5)
        
        if 'SMA_Short' in df_plot.columns:
            ax1.plot(df_plot.index, df_plot['SMA_Short'], label='SMA 50', color='#FF9800', linewidth=1, alpha=0.8)
        if 'SMA_Long' in df_plot.columns:
            ax1.plot(df_plot.index, df_plot['SMA_Long'], label='SMA 200', color='#9C27B0', linewidth=1, alpha=0.8)
        
        # 布林通道
        if 'BB_Upper' in df_plot.columns:
            ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], 
                            alpha=0.1, color='gray', label='布林通道')
        
        ax1.set_ylabel('價格', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.set_title('價格走勢與移動平均線', fontsize=11)
        
        # 標記最新價格
        latest_price = df_plot['Close'].iloc[-1]
        ax1.annotate(f'{latest_price:,.0f}', 
                    xy=(df_plot.index[-1], latest_price),
                    xytext=(10, 0), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#2196F3')
        
        # 2. RSI
        ax2 = axes[1]
        if 'RSI' in df_plot.columns:
            ax2.plot(df_plot.index, df_plot['RSI'], color='#673AB7', linewidth=1)
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超買 (70)')
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超賣 (30)')
            ax2.fill_between(df_plot.index, 30, 70, alpha=0.1, color='gray')
            ax2.set_ylim(0, 100)
            
            # 標記最新 RSI
            latest_rsi = df_plot['RSI'].iloc[-1]
            ax2.annotate(f'{latest_rsi:.1f}', 
                        xy=(df_plot.index[-1], latest_rsi),
                        xytext=(10, 0), textcoords='offset points',
                        fontsize=9, fontweight='bold')
        
        ax2.set_ylabel('RSI', fontsize=10)
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.set_title('RSI 相對強弱指標', fontsize=11)
        
        # 3. MACD
        ax3 = axes[2]
        if 'MACD' in df_plot.columns:
            ax3.plot(df_plot.index, df_plot['MACD'], label='MACD', color='#2196F3', linewidth=1)
            ax3.plot(df_plot.index, df_plot['MACD_Signal'], label='Signal', color='#FF5722', linewidth=1)
            
            # 柱狀圖
            colors = ['green' if v >= 0 else 'red' for v in df_plot['MACD_Histogram']]
            ax3.bar(df_plot.index, df_plot['MACD_Histogram'], color=colors, alpha=0.5, width=0.8)
            ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        
        ax3.set_ylabel('MACD', fontsize=10)
        ax3.legend(loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.set_title('MACD 指標', fontsize=11)
        
        # 4. VIX
        ax4 = axes[3]
        if 'VIX_Close' in df_plot.columns:
            vix_col = 'VIX_Close'
        elif 'Close' in df_plot.columns:
            vix_col = None
        else:
            vix_col = None
        
        if vix_col and vix_col in df_plot.columns:
            ax4.plot(df_plot.index, df_plot[vix_col], color='#F44336', linewidth=1.5)
            ax4.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='正常/恐懼 (20)')
            ax4.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='高度恐懼 (30)')
            
            # 填充區域
            ax4.fill_between(df_plot.index, 0, 20, alpha=0.1, color='green', label='正常')
            ax4.fill_between(df_plot.index, 20, 30, alpha=0.1, color='orange')
            ax4.fill_between(df_plot.index, 30, df_plot[vix_col].max() + 5, alpha=0.1, color='red')
            
            # 標記最新 VIX
            latest_vix = df_plot[vix_col].iloc[-1]
            ax4.annotate(f'{latest_vix:.1f}', 
                        xy=(df_plot.index[-1], latest_vix),
                        xytext=(10, 0), textcoords='offset points',
                        fontsize=9, fontweight='bold', color='#F44336')
        
        ax4.set_ylabel('VIX', fontsize=10)
        ax4.set_xlabel('日期', fontsize=10)
        ax4.legend(loc='upper left', fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.set_title('VIX 恐慌指數', fontsize=11)
        
        # 格式化 X 軸日期
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # 儲存圖片
        filepath = None
        if save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.output_dir / f'analysis_{timestamp}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
            print(f"📊 圖表已儲存至: {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return str(filepath) if filepath else None
    
    def plot_signal_summary(
        self,
        signal_result,
        save: bool = True,
        show: bool = True
    ) -> Optional[str]:
        """
        產生信號摘要圖表
        
        Args:
            signal_result: SignalResult 物件
            save: 是否儲存
            show: 是否顯示
        """
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 信號儀表板
        ax1 = axes[0]
        ax1.set_xlim(0, 10)
        ax1.set_ylim(0, 10)
        ax1.axis('off')
        
        # 背景色根據信號
        signal_colors = {
            'STRONG_BUY': '#4CAF50',
            'BUY': '#8BC34A',
            'HOLD': '#FFC107',
            'SELL': '#FF9800',
            'STRONG_SELL': '#F44336'
        }
        signal_name = signal_result.signal.value
        bg_color = signal_colors.get(signal_name, '#FFC107')
        
        # 信號框
        rect = Rectangle((0.5, 5), 9, 4.5, facecolor=bg_color, alpha=0.3, edgecolor=bg_color, linewidth=3)
        ax1.add_patch(rect)
        
        # 信號文字
        signal_emoji = {'STRONG_BUY': '🚀', 'BUY': '📈', 'HOLD': '⏸️', 'SELL': '📉', 'STRONG_SELL': '🔻'}
        ax1.text(5, 8, f'{signal_emoji.get(signal_name, "")} {signal_name}', 
                fontsize=24, ha='center', va='center', fontweight='bold')
        ax1.text(5, 6.2, f'綜合評分: {signal_result.total_score:.2f}', 
                fontsize=14, ha='center', va='center')
        ax1.text(5, 5.5, f'信心度: {signal_result.confidence:.1f}%', 
                fontsize=12, ha='center', va='center', alpha=0.7)
        
        # 市場資訊
        ax1.text(5, 3.5, f'那斯達克: {signal_result.nasdaq_price:,.2f} ({signal_result.nasdaq_change:+.2f}%)', 
                fontsize=11, ha='center', va='center')
        ax1.text(5, 2.5, f'VIX: {signal_result.vix_value:.2f} - {signal_result.vix_score.sentiment}', 
                fontsize=11, ha='center', va='center')
        ax1.text(5, 1, f'日期: {signal_result.date}', 
                fontsize=10, ha='center', va='center', alpha=0.6)
        
        ax1.set_title('交易信號摘要', fontsize=14, fontweight='bold')
        
        # 2. 指標評分雷達圖
        ax2 = axes[1]
        
        categories = ['RSI', 'MACD', 'MA', 'VIX']
        scores = [
            signal_result.rsi_score.score,
            signal_result.macd_score.score,
            signal_result.ma_score.score,
            min(max(signal_result.vix_score.score, -2), 2)  # 標準化
        ]
        
        # 轉換為 0-4 範圍 (原本是 -2 到 +2)
        scores_normalized = [(s + 2) for s in scores]
        
        # 創建雷達圖
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        scores_normalized += scores_normalized[:1]  # 閉合
        angles += angles[:1]
        
        ax2 = fig.add_subplot(122, polar=True)
        ax2.plot(angles, scores_normalized, 'o-', linewidth=2, color='#2196F3')
        ax2.fill(angles, scores_normalized, alpha=0.25, color='#2196F3')
        
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels(categories, fontsize=11)
        ax2.set_ylim(0, 4)
        ax2.set_yticks([1, 2, 3])
        ax2.set_yticklabels(['-1', '0', '+1'], fontsize=8)
        ax2.set_title('指標評分', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 儲存
        filepath = None
        if save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.output_dir / f'signal_{timestamp}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
            print(f"📊 信號圖表已儲存至: {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return str(filepath) if filepath else None
    
    def create_interactive_chart(
        self,
        df: pd.DataFrame,
        vix_data: pd.DataFrame = None,
        days: int = 252,
        drawdown_threshold: float = 0.10
    ) -> str:
        """
        建立互動式 HTML 圖表 (使用 Plotly)
        可捲動、縮放、hover 查看資料
        
        Args:
            df: 包含技術指標的 DataFrame
            vix_data: VIX 資料
            days: 顯示天數
            drawdown_threshold: 下跌區間閾值 (預設 10%)
        
        Returns:
            HTML 內容字串
        """
        if not PLOTLY_AVAILABLE:
            return "<p>Plotly 未安裝，無法產生互動式圖表</p>"
        
        # 取最近 N 天資料
        df_plot = df.tail(days).copy()
        
        # 計算下跌區間 (跌幅超過 threshold)
        drawdown_zones = self._find_drawdown_zones(df_plot, threshold=drawdown_threshold)
        
        # 處理 VIX 資料
        if vix_data is not None:
            vix = vix_data.tail(days).copy()
            vix_close = vix['Close'] if 'Close' in vix.columns else None
        elif 'VIX_Close' in df_plot.columns:
            vix_close = df_plot['VIX_Close']
        else:
            vix_close = None
        
        # 建立子圖 (3 rows) - 不含 Volume 和 MACD
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.50, 0.25, 0.25],
            subplot_titles=(
                '那斯達克綜合指數 (NASDAQ Composite)',
                'RSI (相對強弱指標)',
                'VIX 恐慌指數'
            )
        )
        
        # 1. 價格 K 線圖
        fig.add_trace(
            go.Candlestick(
                x=df_plot.index,
                open=df_plot['Open'],
                high=df_plot['High'],
                low=df_plot['Low'],
                close=df_plot['Close'],
                name='NASDAQ',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        # 移動平均線
        if 'SMA_Short' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index, y=df_plot['SMA_Short'],
                    name='SMA 50', line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )
        
        if 'SMA_Long' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index, y=df_plot['SMA_Long'],
                    name='SMA 200', line=dict(color='purple', width=1)
                ),
                row=1, col=1
            )
        
        # 布林通道
        if 'BB_Upper' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index, y=df_plot['BB_Upper'],
                    name='BB Upper', line=dict(color='gray', width=1, dash='dot'),
                    showlegend=False
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index, y=df_plot['BB_Lower'],
                    name='BB Lower', line=dict(color='gray', width=1, dash='dot'),
                    fill='tonexty', fillcolor='rgba(128,128,128,0.1)',
                    showlegend=False
                ),
                row=1, col=1
            )
        
        # 2. RSI
        if 'RSI' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index, y=df_plot['RSI'],
                    name='RSI', line=dict(color='#2196F3', width=1.5)
                ),
                row=2, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, row=2, col=1)
        
        # 3. VIX
        if vix_close is not None:
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index if vix_close is df_plot.get('VIX_Close') else vix.index,
                    y=vix_close,
                    name='VIX', line=dict(color='#9C27B0', width=1.5),
                    fill='tozeroy', fillcolor='rgba(156,39,176,0.1)'
                ),
                row=3, col=1
            )
            fig.add_hline(y=20, line_dash="dash", line_color="orange", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="red", row=3, col=1)
        
        # 標示下跌區間 - 根據跌幅大小使用不同顏色
        # 大崩盤 (跌幅 > 20%): 紅色
        # 小修正 (跌幅 10-20%): 黃色
        for zone in drawdown_zones:
            # 根據跌幅決定顏色
            drawdown_pct = abs(zone['drawdown'])
            if drawdown_pct > 0.20:
                # 大崩盤 - 紅色
                fill_color = "rgba(255, 0, 0, 0.15)"
                border_color = "#d32f2f"
                label_prefix = "🔴"
            else:
                # 小修正 - 黃色
                fill_color = "rgba(255, 193, 7, 0.20)"
                border_color = "#f57c00"
                label_prefix = "🟡"
            
            # 格式化日期（使用高點到低點的日期）
            peak_str = zone['peak_date'].strftime('%Y/%m/%d') if hasattr(zone['peak_date'], 'strftime') else str(zone['peak_date'])[:10]
            trough_str = zone['trough_date'].strftime('%Y/%m/%d') if hasattr(zone['trough_date'], 'strftime') else str(zone['trough_date'])[:10]
            
            # 在價格圖上標示區域
            fig.add_vrect(
                x0=zone['peak_date'],
                x1=zone['trough_date'],
                fillcolor=fill_color,
                layer="below",
                line_width=0,
                row=1, col=1
            )
            # 在區間中間加上標註（顯示高點~低點日期和跌幅）
            mid_date = zone['peak_date'] + (zone['trough_date'] - zone['peak_date']) / 2
            fig.add_annotation(
                x=mid_date,
                y=zone['peak_price'],
                text=f"{label_prefix} {zone['drawdown']:.1%}<br>{peak_str}~{trough_str}",
                showarrow=True,
                arrowhead=2,
                arrowcolor=border_color,
                font=dict(color=border_color, size=10, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor=border_color,
                borderwidth=1,
                row=1, col=1
            )
        
        # 更新版面配置
        fig.update_layout(
            height=900,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            hoverdistance=100,
            spikedistance=-1,  # -1 表示無限距離，確保所有圖都能觸發
            margin=dict(l=60, r=60, t=80, b=60),
            # 強制設置 X 軸範圍以確保顯示完整資料
            xaxis=dict(range=[df_plot.index[0], df_plot.index[-1]]),
            xaxis2=dict(range=[df_plot.index[0], df_plot.index[-1]]),
            xaxis3=dict(range=[df_plot.index[0], df_plot.index[-1]])
        )
        
        # 更新所有 X 軸 - 啟用 spike（垂直虛線）同步顯示
        fig.update_xaxes(
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikethickness=1,
            spikecolor='gray',
            spikedash='dot'
        )
        
        # 更新 Y 軸
        fig.update_yaxes(title_text="價格", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
        fig.update_yaxes(title_text="VIX", row=3, col=1)
        
        # 產生基本 HTML
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        # 加入跨圖同步 crosshair 的 JavaScript
        crosshair_js = """
<script>
(function() {
    var originalShapes = [];  // 儲存原始的 shapes（下跌區間等）
    
    function initCrosshair() {
        var plotDiv = document.querySelector('.js-plotly-plot');
        if (!plotDiv || !plotDiv._fullLayout) {
            setTimeout(initCrosshair, 200);
            return;
        }
        
        // 保存原始 shapes（包含紅色下跌區間）
        if (plotDiv._fullLayout.shapes) {
            originalShapes = JSON.parse(JSON.stringify(plotDiv._fullLayout.shapes));
        }
        
        plotDiv.on('plotly_hover', function(data) {
            if (!data.points || data.points.length === 0) return;
            
            var xVal = data.points[0].x;
            var layout = plotDiv._fullLayout;
            
            // 複製原始 shapes
            var shapes = originalShapes.slice();
            
            // 加入 crosshair 線條到每個子圖
            var yAxes = ['yaxis', 'yaxis2', 'yaxis3'];
            
            yAxes.forEach(function(yAxisName, index) {
                var yAxis = layout[yAxisName];
                if (yAxis && yAxis.domain) {
                    shapes.push({
                        type: 'line',
                        xref: index === 0 ? 'x' : 'x' + (index + 1),
                        yref: 'paper',
                        x0: xVal,
                        x1: xVal,
                        y0: yAxis.domain[0],
                        y1: yAxis.domain[1],
                        line: {
                            color: 'rgba(100, 100, 100, 0.8)',
                            width: 1,
                            dash: 'dot'
                        }
                    });
                }
            });
            
            Plotly.relayout(plotDiv, {shapes: shapes});
        });
        
        plotDiv.on('plotly_unhover', function() {
            // 恢復原始 shapes（保留紅色下跌區間）
            Plotly.relayout(plotDiv, {shapes: originalShapes});
        });
    }
    
    if (document.readyState === 'complete') {
        setTimeout(initCrosshair, 100);
    } else {
        window.addEventListener('load', function() {
            setTimeout(initCrosshair, 100);
        });
    }
})();
</script>
"""
        
        # 返回 HTML + JS
        return chart_html + crosshair_js
    
    def save_interactive_report(
        self,
        df: pd.DataFrame,
        signal_result,
        vix_data: pd.DataFrame = None,
        days: int = 252,
        drawdown_threshold: float = 0.10,
        swing_analysis: dict = None
    ) -> Path:
        """
        儲存完整互動式 HTML 報告
        
        Args:
            df: 包含技術指標的 DataFrame
            signal_result: 信號結果
            vix_data: VIX 資料
            days: 顯示天數
            drawdown_threshold: 下跌區間閾值
            swing_analysis: 波段分析資料
        """
        from .report import ReportGenerator
        
        # 找出下跌區間
        df_plot = df.tail(days).copy()
        drawdown_zones = self._find_drawdown_zones(df_plot, threshold=drawdown_threshold)
        
        # 產生互動式圖表
        chart_html = self.create_interactive_chart(df, vix_data, days, drawdown_threshold)
        
        report_gen = ReportGenerator(str(self.output_dir))
        report_path = report_gen.generate_full_report(
            signal_result=signal_result,
            nasdaq_data=df,
            vix_data=vix_data if vix_data is not None else df,
            chart_html=chart_html,
            drawdown_zones=drawdown_zones,
            swing_analysis=swing_analysis
        )
        
        return report_path


def main():
    """測試圖表產生"""
    from data import DataFetcher
    from indicators import CombinedSignalGenerator, TechnicalIndicators
    
    print("📊 產生分析圖表...")
    
    # 下載資料
    fetcher = DataFetcher()
    nasdaq_data, vix_data = fetcher.fetch_all(start_date="2024-01-01", save_csv=False)
    
    # 計算指標
    tech = TechnicalIndicators()
    df = tech.calculate_all(nasdaq_data)
    
    # 合併 VIX
    vix_renamed = vix_data[['Close']].rename(columns={'Close': 'VIX_Close'})
    df = df.join(vix_renamed, how='inner')
    
    # 產生信號
    generator = CombinedSignalGenerator()
    signal = generator.generate_signal(nasdaq_data, vix_data)
    
    # 產生圖表
    charts = ChartGenerator()
    charts.plot_full_analysis(df, signal, days=120)
    charts.plot_signal_summary(signal)


if __name__ == "__main__":
    main()
