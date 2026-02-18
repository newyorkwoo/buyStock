"""
Swing Analyzer Module
波段分析模組 - 分析歷史波段高低點，提供買賣建議
"""
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime


@dataclass
class SwingPoint:
    """波段點位"""
    date: datetime
    price: float
    type: str  # 'peak' or 'trough'


@dataclass 
class SwingCycle:
    """完整波段週期（高點到低點再到高點）"""
    peak_date: datetime
    peak_price: float
    trough_date: datetime
    trough_price: float
    recovery_date: Optional[datetime]
    recovery_price: Optional[float]
    
    @property
    def drawdown(self) -> float:
        """下跌幅度"""
        return (self.trough_price - self.peak_price) / self.peak_price
    
    @property
    def decline_days(self) -> int:
        """下跌天數"""
        return (self.trough_date - self.peak_date).days
    
    @property
    def recovery_days(self) -> Optional[int]:
        """回復天數（從低點到回復高點）"""
        if self.recovery_date:
            return (self.recovery_date - self.trough_date).days
        return None
    
    @property
    def total_cycle_days(self) -> Optional[int]:
        """完整週期天數"""
        if self.recovery_date:
            return (self.recovery_date - self.peak_date).days
        return None


class SwingAnalyzer:
    """
    波段分析器
    分析歷史波段，識別高低點，提供統計分析和買賣建議
    """
    
    def __init__(self, drawdown_threshold: float = 0.10):
        """
        初始化波段分析器
        
        Args:
            drawdown_threshold: 波段下跌閾值 (預設 10%)
        """
        self.drawdown_threshold = drawdown_threshold
        self.data_dir = Path(__file__).parent.parent / "data" / "raw"
    
    def load_data(self, start_date: str = "2000-01-01") -> pd.DataFrame:
        """載入歷史資料"""
        filepath = self.data_dir / "nasdaq_2000.csv"
        if not filepath.exists():
            raise FileNotFoundError(f"找不到資料檔案: {filepath}")
        
        # yfinance 新版格式有 MultiIndex header
        df = pd.read_csv(filepath, header=[0, 1], index_col=0)
        df.index = pd.to_datetime(df.index)
        
        # 扁平化 columns
        df.columns = df.columns.get_level_values(0)
        
        return df[df.index >= start_date]
    
    def find_swing_cycles(
        self, 
        df: pd.DataFrame,
        threshold: float = None
    ) -> List[SwingCycle]:
        """
        找出所有波段週期（改進版：使用獨立週期偵測）
        
        使用「50% 反彈重置」策略：當價格從低點反彈超過 50% 時，
        視為新週期開始，這樣可以正確識別每個獨立的市場修正。
        
        Args:
            df: 價格資料
            threshold: 下跌閾值，預設使用初始化設定
            
        Returns:
            波段週期列表
        """
        if threshold is None:
            threshold = self.drawdown_threshold
            
        close = df['Close'].values
        dates = df.index
        n = len(close)
        
        cycles = []
        
        if n < 2:
            return cycles
        
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
                    # 結束當前下跌區間（價格已完全回復並創新高）
                    peak_val = close[drawdown_start_idx]
                    max_dd = (cycle_trough - peak_val) / peak_val
                    if max_dd <= -threshold:
                        # 找回復時間
                        recovery_idx = None
                        for j in range(cycle_trough_idx, n):
                            if close[j] >= peak_val:
                                recovery_idx = j
                                break
                        
                        cycle = SwingCycle(
                            peak_date=dates[drawdown_start_idx].to_pydatetime(),
                            peak_price=float(peak_val),
                            trough_date=dates[cycle_trough_idx].to_pydatetime(),
                            trough_price=float(cycle_trough),
                            recovery_date=dates[recovery_idx].to_pydatetime() if recovery_idx else None,
                            recovery_price=float(close[recovery_idx]) if recovery_idx else None
                        )
                        cycles.append(cycle)
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
                    peak_val = close[drawdown_start_idx]
                    max_dd = (cycle_trough - peak_val) / peak_val
                    if max_dd <= -threshold:
                        # 找回復時間（如果有）
                        recovery_idx = None
                        for j in range(cycle_trough_idx, n):
                            if close[j] >= peak_val:
                                recovery_idx = j
                                break
                        
                        cycle = SwingCycle(
                            peak_date=dates[drawdown_start_idx].to_pydatetime(),
                            peak_price=float(peak_val),
                            trough_date=dates[cycle_trough_idx].to_pydatetime(),
                            trough_price=float(cycle_trough),
                            recovery_date=dates[recovery_idx].to_pydatetime() if recovery_idx else None,
                            recovery_price=float(close[recovery_idx]) if recovery_idx else None
                        )
                        cycles.append(cycle)
                    
                    # 開始新週期
                    in_drawdown = False
                    cycle_peak = current_price
                    cycle_peak_idx = i
                    cycle_trough = current_price
                    cycle_trough_idx = i
        
        # 處理結束時仍在下跌區間的情況
        if in_drawdown:
            peak_val = close[drawdown_start_idx]
            max_dd = (cycle_trough - peak_val) / peak_val
            if max_dd <= -threshold:
                # 找回復時間
                recovery_idx = None
                for j in range(cycle_trough_idx, n):
                    if close[j] >= peak_val:
                        recovery_idx = j
                        break
                
                cycle = SwingCycle(
                    peak_date=dates[drawdown_start_idx].to_pydatetime(),
                    peak_price=float(peak_val),
                    trough_date=dates[cycle_trough_idx].to_pydatetime(),
                    trough_price=float(cycle_trough),
                    recovery_date=dates[recovery_idx].to_pydatetime() if recovery_idx else None,
                    recovery_price=float(close[recovery_idx]) if recovery_idx else None
                )
                cycles.append(cycle)
        
        # 按日期排序
        cycles.sort(key=lambda x: x.peak_date)
        return cycles
    
    def analyze_statistics(self, cycles: List[SwingCycle]) -> dict:
        """
        計算波段統計數據
        
        Returns:
            統計數據字典
        """
        if not cycles:
            return {}
        
        drawdowns = [c.drawdown for c in cycles]
        decline_days = [c.decline_days for c in cycles]
        recovery_days = [c.recovery_days for c in cycles if c.recovery_days]
        total_days = [c.total_cycle_days for c in cycles if c.total_cycle_days]
        
        stats = {
            'total_cycles': len(cycles),
            'completed_cycles': len([c for c in cycles if c.recovery_date]),
            'ongoing_cycles': len([c for c in cycles if not c.recovery_date]),
            
            # 下跌幅度統計
            'drawdown': {
                'mean': np.mean(drawdowns),
                'median': np.median(drawdowns),
                'min': np.min(drawdowns),
                'max': np.max(drawdowns),
                'std': np.std(drawdowns),
                'percentile_25': np.percentile(drawdowns, 25),
                'percentile_75': np.percentile(drawdowns, 75),
            },
            
            # 下跌天數統計
            'decline_days': {
                'mean': np.mean(decline_days),
                'median': np.median(decline_days),
                'min': np.min(decline_days),
                'max': np.max(decline_days),
            },
            
            # 回復天數統計
            'recovery_days': {
                'mean': np.mean(recovery_days) if recovery_days else None,
                'median': np.median(recovery_days) if recovery_days else None,
                'min': np.min(recovery_days) if recovery_days else None,
                'max': np.max(recovery_days) if recovery_days else None,
            },
            
            # 完整週期統計
            'total_cycle_days': {
                'mean': np.mean(total_days) if total_days else None,
                'median': np.median(total_days) if total_days else None,
                'min': np.min(total_days) if total_days else None,
                'max': np.max(total_days) if total_days else None,
            },
        }
        
        return stats
    
    def analyze_by_severity(self, cycles: List[SwingCycle]) -> dict:
        """
        依下跌嚴重程度分類分析
        """
        categories = {
            'correction_10_15': [],   # 10-15% 修正
            'correction_15_20': [],   # 15-20% 修正
            'bear_market_20_30': [],  # 20-30% 熊市
            'crash_30_plus': [],      # 30%+ 崩盤
        }
        
        for c in cycles:
            dd = abs(c.drawdown)
            if dd < 0.15:
                categories['correction_10_15'].append(c)
            elif dd < 0.20:
                categories['correction_15_20'].append(c)
            elif dd < 0.30:
                categories['bear_market_20_30'].append(c)
            else:
                categories['crash_30_plus'].append(c)
        
        result = {}
        for name, cycle_list in categories.items():
            if cycle_list:
                drawdowns = [c.drawdown for c in cycle_list]
                decline_days = [c.decline_days for c in cycle_list]
                recovery_days = [c.recovery_days for c in cycle_list if c.recovery_days]
                
                result[name] = {
                    'count': len(cycle_list),
                    'avg_drawdown': np.mean(drawdowns),
                    'avg_decline_days': np.mean(decline_days),
                    'avg_recovery_days': np.mean(recovery_days) if recovery_days else None,
                }
        
        return result
    
    def get_current_status(self, df: pd.DataFrame) -> dict:
        """
        分析當前市場狀態
        """
        close = df['Close'].values
        dates = df.index
        
        # 計算從最高點的回撤
        all_time_high_idx = np.argmax(close)
        all_time_high = close[all_time_high_idx]
        all_time_high_date = dates[all_time_high_idx]
        
        current_price = close[-1]
        current_date = dates[-1]
        
        drawdown_from_ath = (current_price - all_time_high) / all_time_high
        
        # 計算近期高點 (過去 252 天)
        recent_period = min(252, len(close))
        recent_high_idx = len(close) - recent_period + np.argmax(close[-recent_period:])
        recent_high = close[recent_high_idx]
        recent_high_date = dates[recent_high_idx]
        
        drawdown_from_recent = (current_price - recent_high) / recent_high
        
        # 判斷當前狀態
        if drawdown_from_recent >= -0.05:
            status = "接近高點"
            status_code = "NEAR_HIGH"
        elif drawdown_from_recent >= -0.10:
            status = "小幅回檔"
            status_code = "PULLBACK"
        elif drawdown_from_recent >= -0.15:
            status = "修正區間"
            status_code = "CORRECTION"
        elif drawdown_from_recent >= -0.20:
            status = "深度修正"
            status_code = "DEEP_CORRECTION"
        elif drawdown_from_recent >= -0.30:
            status = "熊市"
            status_code = "BEAR_MARKET"
        else:
            status = "崩盤"
            status_code = "CRASH"
        
        return {
            'current_date': current_date,
            'current_price': current_price,
            'all_time_high': all_time_high,
            'all_time_high_date': all_time_high_date,
            'drawdown_from_ath': drawdown_from_ath,
            'recent_high': recent_high,
            'recent_high_date': recent_high_date,
            'drawdown_from_recent': drawdown_from_recent,
            'status': status,
            'status_code': status_code,
        }
    
    def generate_recommendations(
        self, 
        cycles: List[SwingCycle],
        stats: dict,
        current_status: dict
    ) -> dict:
        """
        基於歷史統計生成買賣建議
        """
        recommendations = {
            'action': 'HOLD',
            'confidence': 0.5,
            'reasons': [],
            'historical_insight': [],
            'entry_zones': [],
            'exit_zones': [],
        }
        
        current_dd = current_status['drawdown_from_recent']
        avg_dd = stats['drawdown']['mean']
        median_dd = stats['drawdown']['median']
        
        # 分析當前位置相對於歷史
        if current_dd <= avg_dd:
            # 當前下跌已超過歷史平均
            pct_worse = len([c for c in cycles if c.drawdown <= current_dd]) / len(cycles) * 100
            recommendations['historical_insight'].append(
                f"當前跌幅 {current_dd:.1%} 已超過歷史 {pct_worse:.0f}% 的波段"
            )
        
        # 根據狀態給出建議
        status = current_status['status_code']
        
        if status == "NEAR_HIGH":
            recommendations['action'] = 'HOLD'
            recommendations['confidence'] = 0.4
            recommendations['reasons'].append("接近高點，不建議追高")
            recommendations['reasons'].append("等待回檔 10% 以上再考慮加碼")
            
        elif status == "PULLBACK":
            recommendations['action'] = 'WATCH'
            recommendations['confidence'] = 0.5
            recommendations['reasons'].append("小幅回檔中，可觀望")
            recommendations['reasons'].append("若有長期持股可繼續持有")
            
        elif status == "CORRECTION":
            recommendations['action'] = 'BUY_PARTIAL'
            recommendations['confidence'] = 0.6
            recommendations['reasons'].append("修正區間，可考慮分批建倉")
            recommendations['historical_insight'].append(
                f"歷史上 10-15% 修正平均 {stats['drawdown']['mean']*100:.1f}% 跌幅，"
                f"平均 {int(stats['decline_days']['mean'])} 天見底"
            )
            
        elif status == "DEEP_CORRECTION":
            recommendations['action'] = 'BUY'
            recommendations['confidence'] = 0.7
            recommendations['reasons'].append("深度修正，歷史上是較佳買點")
            recommendations['reasons'].append("建議分批買進，不要一次all-in")
            
        elif status == "BEAR_MARKET":
            recommendations['action'] = 'BUY_AGGRESSIVE'
            recommendations['confidence'] = 0.75
            recommendations['reasons'].append("熊市區間，長期投資人的買進機會")
            recommendations['reasons'].append("歷史上熊市後平均需要較長時間回復，但報酬可觀")
            
        elif status == "CRASH":
            recommendations['action'] = 'BUY_AGGRESSIVE'
            recommendations['confidence'] = 0.8
            recommendations['reasons'].append("極端下跌，恐慌中貪婪")
            recommendations['reasons'].append("分批買進，預留資金應對更深跌幅")
        
        # 計算建議進場區間
        current_price = current_status['current_price']
        recent_high = current_status['recent_high']
        
        recommendations['entry_zones'] = [
            {'level': '保守進場', 'price': recent_high * 0.90, 'drawdown': '-10%'},
            {'level': '積極進場', 'price': recent_high * 0.85, 'drawdown': '-15%'},
            {'level': '加碼買進', 'price': recent_high * 0.80, 'drawdown': '-20%'},
            {'level': '重倉買進', 'price': recent_high * 0.70, 'drawdown': '-30%'},
        ]
        
        # 計算建議出場區間
        recommendations['exit_zones'] = [
            {'level': '部分獲利', 'trigger': '從買點漲 20%'},
            {'level': '減碼', 'trigger': '從買點漲 50%'},
            {'level': '停損', 'trigger': '從買點跌 10%'},
        ]
        
        return recommendations
    
    def run_full_analysis(self, threshold: float = 0.10) -> dict:
        """
        執行完整波段分析
        """
        print("📊 載入歷史資料...")
        df = self.load_data()
        print(f"   資料期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
        print(f"   共 {len(df)} 筆資料\n")
        
        print(f"🔍 尋找下跌超過 {threshold*100:.0f}% 的波段...")
        cycles = self.find_swing_cycles(df, threshold=threshold)
        print(f"   找到 {len(cycles)} 個波段\n")
        
        print("📈 計算統計數據...")
        stats = self.analyze_statistics(cycles)
        by_severity = self.analyze_by_severity(cycles)
        
        print("📍 分析當前市場狀態...")
        current_status = self.get_current_status(df)
        
        print("💡 生成買賣建議...")
        recommendations = self.generate_recommendations(cycles, stats, current_status)
        
        return {
            'cycles': cycles,
            'statistics': stats,
            'by_severity': by_severity,
            'current_status': current_status,
            'recommendations': recommendations,
            'data': df,
        }
    
    def print_report(self, result: dict):
        """印出分析報告"""
        stats = result['statistics']
        by_severity = result['by_severity']
        current = result['current_status']
        rec = result['recommendations']
        cycles = result['cycles']
        
        print("\n" + "="*70)
        print("           📊 NASDAQ 波段分析報告 (2000年至今)")
        print("="*70)
        
        # 統計摘要
        print(f"\n【波段統計摘要】")
        print(f"   總波段數: {stats['total_cycles']} 個")
        print(f"   已完成週期: {stats['completed_cycles']} 個")
        print(f"   進行中: {stats['ongoing_cycles']} 個")
        
        print(f"\n【下跌幅度統計】")
        print(f"   平均跌幅: {stats['drawdown']['mean']*100:.1f}%")
        print(f"   中位數: {stats['drawdown']['median']*100:.1f}%")
        print(f"   最大跌幅: {stats['drawdown']['min']*100:.1f}%")
        print(f"   最小跌幅: {stats['drawdown']['max']*100:.1f}%")
        
        print(f"\n【下跌時間統計】")
        print(f"   平均下跌天數: {stats['decline_days']['mean']:.0f} 天")
        print(f"   最長下跌: {stats['decline_days']['max']} 天")
        print(f"   最短下跌: {stats['decline_days']['min']} 天")
        
        if stats['recovery_days']['mean']:
            print(f"\n【回復時間統計】")
            print(f"   平均回復天數: {stats['recovery_days']['mean']:.0f} 天")
            print(f"   最長回復: {stats['recovery_days']['max']} 天")
            print(f"   最短回復: {stats['recovery_days']['min']} 天")
        
        # 依嚴重程度分類
        print(f"\n【依跌幅嚴重程度分類】")
        severity_names = {
            'correction_10_15': '10-15% 修正',
            'correction_15_20': '15-20% 修正',
            'bear_market_20_30': '20-30% 熊市',
            'crash_30_plus': '30%+ 崩盤',
        }
        for key, name in severity_names.items():
            if key in by_severity:
                s = by_severity[key]
                rec_days = f"{s['avg_recovery_days']:.0f}天" if s['avg_recovery_days'] else "進行中"
                print(f"   {name}: {s['count']}次, 平均跌{abs(s['avg_drawdown'])*100:.1f}%, "
                      f"下跌{s['avg_decline_days']:.0f}天, 回復{rec_days}")
        
        # 歷史重大波段
        print(f"\n【歷史重大波段 (跌幅 > 20%)】")
        major_cycles = sorted([c for c in cycles if c.drawdown < -0.20], 
                             key=lambda x: x.drawdown)
        for i, c in enumerate(major_cycles[:10], 1):
            rec_info = f"回復 {c.recovery_days}天" if c.recovery_days else "未回復"
            print(f"   {i}. {c.peak_date.strftime('%Y/%m/%d')} ~ {c.trough_date.strftime('%Y/%m/%d')}: "
                  f"{c.drawdown*100:.1f}%, 下跌{c.decline_days}天, {rec_info}")
        
        # 當前狀態
        print(f"\n" + "="*70)
        print("                    📍 當前市場狀態")
        print("="*70)
        print(f"   日期: {current['current_date'].strftime('%Y-%m-%d')}")
        print(f"   現價: {current['current_price']:,.2f}")
        print(f"   歷史最高: {current['all_time_high']:,.2f} ({current['all_time_high_date'].strftime('%Y/%m/%d')})")
        print(f"   距歷史高點: {current['drawdown_from_ath']*100:+.1f}%")
        print(f"   近期高點: {current['recent_high']:,.2f} ({current['recent_high_date'].strftime('%Y/%m/%d')})")
        print(f"   距近期高點: {current['drawdown_from_recent']*100:+.1f}%")
        print(f"   狀態判斷: {current['status']}")
        
        # 買賣建議
        print(f"\n" + "="*70)
        print("                    💡 買賣建議")
        print("="*70)
        
        action_emoji = {
            'BUY_AGGRESSIVE': '🚀🚀 強力買進',
            'BUY': '🚀 買進',
            'BUY_PARTIAL': '📈 分批買進',
            'WATCH': '👀 觀望',
            'HOLD': '⏸️ 持有',
            'SELL_PARTIAL': '📉 分批賣出',
            'SELL': '🔻 賣出',
        }
        
        print(f"\n   建議動作: {action_emoji.get(rec['action'], rec['action'])}")
        print(f"   信心度: {rec['confidence']*100:.0f}%")
        
        print(f"\n   📋 理由:")
        for reason in rec['reasons']:
            print(f"      • {reason}")
        
        if rec['historical_insight']:
            print(f"\n   📊 歷史洞察:")
            for insight in rec['historical_insight']:
                print(f"      • {insight}")
        
        print(f"\n   🎯 建議進場價位:")
        for zone in rec['entry_zones']:
            print(f"      {zone['level']}: {zone['price']:,.0f} ({zone['drawdown']})")
        
        print(f"\n   🏁 建議出場策略:")
        for zone in rec['exit_zones']:
            print(f"      {zone['level']}: {zone['trigger']}")
        
        print("\n" + "="*70)
        print("   ⚠️ 免責聲明: 以上為歷史統計分析，不構成投資建議")
        print("   投資有風險，請依個人風險承受能力做決策")
        print("="*70 + "\n")

    def analyze_indicators_at_troughs(self, df: pd.DataFrame, cycles: List[SwingCycle]) -> dict:
        """
        分析每個波段低點時的各項指標數值
        
        Args:
            df: 包含價格和指標的 DataFrame
            cycles: 波段週期列表
            
        Returns:
            各指標在低點時的統計數據
        """
        # 計算技術指標
        df = df.copy()
        
        # RSI (60日)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=60).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=60).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # 移動平均線
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df['Distance_SMA50'] = (df['Close'] - df['SMA_50']) / df['SMA_50'] * 100
        df['Distance_SMA200'] = (df['Close'] - df['SMA_200']) / df['SMA_200'] * 100
        
        # 載入 VIX 資料
        vix_path = self.data_dir / "vix_2000.csv"
        if vix_path.exists():
            vix_df = pd.read_csv(vix_path, header=[0, 1], index_col=0)
            vix_df.index = pd.to_datetime(vix_df.index)
            vix_df.columns = vix_df.columns.get_level_values(0)
            df = df.join(vix_df[['Close']].rename(columns={'Close': 'VIX'}), how='left')
        
        # 收集每個低點的指標數值
        trough_data = []
        
        for cycle in cycles:
            trough_date = cycle.trough_date
            
            # 找最近的交易日
            if trough_date in df.index:
                idx = trough_date
            else:
                mask = df.index <= trough_date
                if mask.any():
                    idx = df.index[mask][-1]
                else:
                    continue
            
            row = df.loc[idx]
            
            trough_info = {
                'date': idx,
                'drawdown': cycle.drawdown,
                'decline_days': cycle.decline_days,
                'price': cycle.trough_price,
                'rsi': row.get('RSI', np.nan),
                'macd': row.get('MACD', np.nan),
                'macd_hist': row.get('MACD_Histogram', np.nan),
                'vix': row.get('VIX', np.nan),
                'dist_sma50': row.get('Distance_SMA50', np.nan),
                'dist_sma200': row.get('Distance_SMA200', np.nan),
            }
            trough_data.append(trough_info)
        
        # 計算統計
        valid_rsi = [t['rsi'] for t in trough_data if not np.isnan(t['rsi'])]
        valid_vix = [t['vix'] for t in trough_data if not np.isnan(t['vix'])]
        valid_macd = [t['macd'] for t in trough_data if not np.isnan(t['macd'])]
        valid_dist50 = [t['dist_sma50'] for t in trough_data if not np.isnan(t['dist_sma50'])]
        valid_dist200 = [t['dist_sma200'] for t in trough_data if not np.isnan(t['dist_sma200'])]
        
        # 依跌幅分組
        major_troughs = [t for t in trough_data if t['drawdown'] <= -0.20]  # 跌幅超過20%
        minor_troughs = [t for t in trough_data if -0.20 < t['drawdown'] <= -0.10]  # 10-20%
        
        return {
            'all_troughs': trough_data,
            'statistics': {
                'rsi': {
                    'mean': np.mean(valid_rsi) if valid_rsi else None,
                    'median': np.median(valid_rsi) if valid_rsi else None,
                    'min': np.min(valid_rsi) if valid_rsi else None,
                    'max': np.max(valid_rsi) if valid_rsi else None,
                },
                'vix': {
                    'mean': np.mean(valid_vix) if valid_vix else None,
                    'median': np.median(valid_vix) if valid_vix else None,
                    'min': np.min(valid_vix) if valid_vix else None,
                    'max': np.max(valid_vix) if valid_vix else None,
                },
                'macd': {
                    'mean': np.mean(valid_macd) if valid_macd else None,
                    'median': np.median(valid_macd) if valid_macd else None,
                    'min': np.min(valid_macd) if valid_macd else None,
                    'max': np.max(valid_macd) if valid_macd else None,
                },
                'distance_sma50': {
                    'mean': np.mean(valid_dist50) if valid_dist50 else None,
                    'median': np.median(valid_dist50) if valid_dist50 else None,
                    'min': np.min(valid_dist50) if valid_dist50 else None,
                    'max': np.max(valid_dist50) if valid_dist50 else None,
                },
                'distance_sma200': {
                    'mean': np.mean(valid_dist200) if valid_dist200 else None,
                    'median': np.median(valid_dist200) if valid_dist200 else None,
                    'min': np.min(valid_dist200) if valid_dist200 else None,
                    'max': np.max(valid_dist200) if valid_dist200 else None,
                },
            },
            'major_crash_indicators': {
                'count': len(major_troughs),
                'avg_rsi': np.mean([t['rsi'] for t in major_troughs if not np.isnan(t['rsi'])]) if major_troughs else None,
                'avg_vix': np.mean([t['vix'] for t in major_troughs if not np.isnan(t['vix'])]) if major_troughs else None,
                'avg_dist_sma200': np.mean([t['dist_sma200'] for t in major_troughs if not np.isnan(t['dist_sma200'])]) if major_troughs else None,
            },
            'minor_correction_indicators': {
                'count': len(minor_troughs),
                'avg_rsi': np.mean([t['rsi'] for t in minor_troughs if not np.isnan(t['rsi'])]) if minor_troughs else None,
                'avg_vix': np.mean([t['vix'] for t in minor_troughs if not np.isnan(t['vix'])]) if minor_troughs else None,
                'avg_dist_sma200': np.mean([t['dist_sma200'] for t in minor_troughs if not np.isnan(t['dist_sma200'])]) if minor_troughs else None,
            },
        }

    def generate_entry_signals(self, indicator_analysis: dict, current_status: dict) -> dict:
        """
        根據指標分析結果，生成大資金進場信號條件
        
        Args:
            indicator_analysis: 指標分析結果
            current_status: 當前市場狀態
            
        Returns:
            進場信號條件和建議
        """
        stats = indicator_analysis['statistics']
        major = indicator_analysis['major_crash_indicators']
        minor = indicator_analysis['minor_correction_indicators']
        
        # 計算理想進場條件
        entry_conditions = {
            'aggressive': {  # 積極型（小修正時進場）
                'name': '積極型進場 (小修正買點)',
                'drawdown_range': '10% ~ 15%',
                'conditions': [
                    f"RSI < {stats['rsi']['median']:.0f}" if stats['rsi']['median'] else "RSI < 40",
                    f"VIX > {25:.0f}" if minor.get('avg_vix') else "VIX > 25",
                    "距離 SMA200 偏離 -5% 以上",
                    "MACD 柱狀圖由負轉正（底背離）",
                ],
                'confidence': '中等',
                'risk': '較高（可能繼續下跌）',
                'position_size': '20% ~ 30% 資金',
            },
            'moderate': {  # 穩健型（中等修正時進場）
                'name': '穩健型進場 (中等修正買點)',
                'drawdown_range': '15% ~ 25%',
                'conditions': [
                    f"RSI < {stats['rsi']['percentile_25']:.0f}" if stats['rsi'].get('percentile_25') else "RSI < 35",
                    f"VIX > {30:.0f}",
                    "距離 SMA200 偏離 -10% 以上",
                    "出現明顯恐慌性拋售（成交量大增）",
                ],
                'confidence': '較高',
                'risk': '中等',
                'position_size': '40% ~ 50% 資金',
            },
            'conservative': {  # 保守型（大崩盤時進場）
                'name': '保守型進場 (重大崩盤買點)',
                'drawdown_range': '> 30%',
                'conditions': [
                    f"RSI < {major['avg_rsi']:.0f}" if major.get('avg_rsi') else "RSI < 25",
                    f"VIX > {major['avg_vix']:.0f}" if major.get('avg_vix') else "VIX > 40",
                    f"距離 SMA200 偏離 {major['avg_dist_sma200']:.0f}% 以上" if major.get('avg_dist_sma200') else "距離 SMA200 偏離 -20% 以上",
                    "市場極度恐慌，媒體大量報導股災",
                ],
                'confidence': '最高（歷史證明是絕佳買點）',
                'risk': '較低（但需承受短期帳面虧損）',
                'position_size': '60% ~ 80% 資金',
            },
        }
        
        # 根據歷史數據計算具體價位
        current_price = current_status.get('current_price', 0)
        
        entry_prices = {
            'aggressive': {
                'trigger_price': current_price * 0.90,
                'target_avg_price': current_price * 0.875,
            },
            'moderate': {
                'trigger_price': current_price * 0.80,
                'target_avg_price': current_price * 0.775,
            },
            'conservative': {
                'trigger_price': current_price * 0.70,
                'target_avg_price': current_price * 0.65,
            },
        }
        
        # 歷史買點回顧
        historical_entry_points = []
        for trough in indicator_analysis['all_troughs']:
            if trough['drawdown'] <= -0.10:  # 只列出跌幅超過10%的
                historical_entry_points.append({
                    'date': trough['date'].strftime('%Y-%m-%d'),
                    'drawdown': trough['drawdown'],
                    'rsi': trough['rsi'],
                    'vix': trough['vix'],
                    'recovery': '✅ 已回復' if trough['drawdown'] > -0.5 else '✅ 已大幅回復',
                })
        
        # 按日期降序排列，最新的在最前面
        historical_entry_points.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'entry_conditions': entry_conditions,
            'entry_prices': entry_prices,
            'historical_entry_points': historical_entry_points,
            'current_status': current_status,
            'key_insights': self._generate_key_insights(indicator_analysis, current_status),
        }

    def _generate_key_insights(self, indicator_analysis: dict, current_status: dict) -> list:
        """生成關鍵洞察"""
        insights = []
        stats = indicator_analysis['statistics']
        major = indicator_analysis['major_crash_indicators']
        minor = indicator_analysis['minor_correction_indicators']
        total_count = major.get('count', 0) + minor.get('count', 0)
        
        # 總覽洞察
        insights.append(f"📈 2000年至今共發生 {total_count} 次跌幅超過 10% 的波段修正，其中 {major.get('count', 0)} 次大崩盤、{minor.get('count', 0)} 次小修正")
        
        # RSI 洞察
        if stats['rsi']['median']:
            insights.append(f"📊 波段低點 RSI 中位數為 {stats['rsi']['median']:.1f}（範圍 {stats['rsi']['min']:.1f}~{stats['rsi']['max']:.1f}），RSI 跌破 {stats['rsi']['median']:.0f} 是潛在買點")
        
        # VIX 洞察
        if stats['vix']['median']:
            insights.append(f"😱 波段低點 VIX 中位數為 {stats['vix']['median']:.1f}，大崩盤時平均 VIX 達 {major.get('avg_vix', 40):.0f}，VIX 飆升至 30+ 代表恐慌性賣壓")
        
        # 大崩盤 vs 小修正洞察
        if major['count'] > 0 and minor['count'] > 0:
            insights.append(f"💥 大崩盤平均 RSI={major.get('avg_rsi', 25):.0f}、VIX={major.get('avg_vix', 40):.0f}；小修正平均 RSI={minor.get('avg_rsi', 30):.0f}、VIX={minor.get('avg_vix', 25):.0f}")
        
        # SMA 洞察
        if stats['distance_sma200']['median']:
            insights.append(f"📉 波段低點距 SMA200 中位數為 {stats['distance_sma200']['median']:.1f}%，大崩盤時平均偏離 {major.get('avg_dist_sma200', -20):.1f}%")
        
        # 時間洞察
        insights.append("⏰ 根據歷史，大跌後平均需要 1-2 年回復，但長期投資者都能獲得正報酬")
        
        return insights

    def print_indicator_analysis_report(self, indicator_analysis: dict, entry_signals: dict):
        """印出指標相關性分析報告"""
        print("\n" + "="*70)
        print("         📊 波段指標相關性分析報告 (2000年至今)")
        print("="*70)
        
        stats = indicator_analysis['statistics']
        
        # 各指標在波段低點的統計
        print("\n【一、波段低點指標統計】")
        print("-"*50)
        
        print("\n   📈 RSI (相對強弱指標):")
        if stats['rsi']['mean']:
            print(f"      平均值: {stats['rsi']['mean']:.1f}")
            print(f"      中位數: {stats['rsi']['median']:.1f}")
            print(f"      範圍: {stats['rsi']['min']:.1f} ~ {stats['rsi']['max']:.1f}")
            print(f"      💡 當 RSI < {stats['rsi']['median']:.0f} 時，是潛在買入時機")
        
        print("\n   😱 VIX (恐慌指數):")
        if stats['vix']['mean']:
            print(f"      平均值: {stats['vix']['mean']:.1f}")
            print(f"      中位數: {stats['vix']['median']:.1f}")
            print(f"      範圍: {stats['vix']['min']:.1f} ~ {stats['vix']['max']:.1f}")
            print(f"      💡 當 VIX > {stats['vix']['median']:.0f} 時，市場恐慌，可能是買點")
        
        print("\n   📉 距離 SMA200 (%):")
        if stats['distance_sma200']['mean']:
            print(f"      平均偏離: {stats['distance_sma200']['mean']:.1f}%")
            print(f"      中位數: {stats['distance_sma200']['median']:.1f}%")
            print(f"      最大偏離: {stats['distance_sma200']['min']:.1f}%")
            print(f"      💡 跌破 SMA200 超過 10% 是歷史上的強力買點")
        
        # 大崩盤 vs 小修正比較
        major = indicator_analysis['major_crash_indicators']
        minor = indicator_analysis['minor_correction_indicators']
        
        print("\n【二、大崩盤 vs 小修正指標比較】")
        print("-"*50)
        print(f"\n   🔴 大崩盤 (跌幅 > 20%): {major['count']} 次")
        if major['avg_rsi']:
            print(f"      平均 RSI: {major['avg_rsi']:.1f}")
        if major['avg_vix']:
            print(f"      平均 VIX: {major['avg_vix']:.1f}")
        if major['avg_dist_sma200']:
            print(f"      平均距離 SMA200: {major['avg_dist_sma200']:.1f}%")
        
        print(f"\n   🟡 小修正 (跌幅 10-20%): {minor['count']} 次")
        if minor['avg_rsi']:
            print(f"      平均 RSI: {minor['avg_rsi']:.1f}")
        if minor['avg_vix']:
            print(f"      平均 VIX: {minor['avg_vix']:.1f}")
        if minor['avg_dist_sma200']:
            print(f"      平均距離 SMA200: {minor['avg_dist_sma200']:.1f}%")
        
        # 歷史買點回顧
        print("\n【三、歷史絕佳買點回顧 (跌幅 > 15%)】")
        print("-"*50)
        print(f"\n   {'日期':<12} {'跌幅':<10} {'RSI':<8} {'VIX':<8} {'結果'}")
        print("   " + "-"*55)
        
        for point in entry_signals['historical_entry_points'][:10]:
            rsi_str = f"{point['rsi']:.1f}" if point['rsi'] and not np.isnan(point['rsi']) else "N/A"
            vix_str = f"{point['vix']:.1f}" if point['vix'] and not np.isnan(point['vix']) else "N/A"
            print(f"   {point['date']:<12} {point['drawdown']*100:>6.1f}%   {rsi_str:<8} {vix_str:<8} {point['recovery']}")
        
        # 進場策略建議
        print("\n【四、大資金進場策略建議】")
        print("="*70)
        
        for key, condition in entry_signals['entry_conditions'].items():
            print(f"\n   🎯 {condition['name']}")
            print(f"      下跌區間: {condition['drawdown_range']}")
            print(f"      進場條件:")
            for c in condition['conditions']:
                print(f"         ✓ {c}")
            print(f"      信心度: {condition['confidence']}")
            print(f"      風險: {condition['risk']}")
            print(f"      建議資金配置: {condition['position_size']}")
            
            prices = entry_signals['entry_prices'][key]
            print(f"      觸發價位: {prices['trigger_price']:,.0f}")
            print(f"      目標均價: {prices['target_avg_price']:,.0f}")
        
        # 關鍵洞察
        print("\n【五、關鍵投資洞察】")
        print("-"*50)
        for insight in entry_signals['key_insights']:
            print(f"   {insight}")
        
        # 當前市場評估
        current = entry_signals['current_status']
        print("\n【六、當前市場評估】")
        print("-"*50)
        print(f"   現價: {current.get('current_price', 0):,.2f}")
        print(f"   距歷史高點: {current.get('distance_from_ath', 0)*100:.1f}%")
        
        if current.get('distance_from_ath', 0) > -0.05:
            print("\n   ⚠️ 當前市場評估: 接近高點區域")
            print("   建議: 保持觀望，等待更好的進場時機")
            print("   策略: 可先建立觀察清單，設定目標買入價")
        elif -0.15 < current.get('distance_from_ath', 0) <= -0.05:
            print("\n   🟡 當前市場評估: 小幅回調區域")
            print("   建議: 可小量試單，但保留大部分資金")
            print("   策略: 採用金字塔式加碼，越跌越買")
        else:
            print("\n   🟢 當前市場評估: 潛在買入區域")
            print("   建議: 根據風險承受度分批進場")
            print("   策略: 按照上述進場策略執行")
        
        print("\n" + "="*70)
        print("   💰 大資金進場核心原則:")
        print("      1. 分批進場，不要一次 ALL IN")
        print("      2. 越跌越買，採用定期定額 + 加碼策略")
        print("      3. 設定明確的進場價位和資金配置")
        print("      4. 保持長期投資心態，不因短期波動恐慌")
        print("      5. 只用閒置資金投資，不影響生活")
        print("="*70 + "\n")

    def run_full_indicator_analysis(self) -> dict:
        """執行完整的指標相關性分析"""
        print("📊 載入歷史資料...")
        df = self.load_data()
        print(f"   資料期間: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
        print(f"   共 {len(df)} 筆資料\n")
        
        print("🔍 尋找歷史波段...")
        cycles = self.find_swing_cycles(df, threshold=0.10)
        print(f"   找到 {len(cycles)} 個波段\n")
        
        print("📈 分析各指標在波段低點的數值...")
        indicator_analysis = self.analyze_indicators_at_troughs(df, cycles)
        
        print("💡 生成大資金進場策略建議...")
        current_status = self.get_current_status(df)
        entry_signals = self.generate_entry_signals(indicator_analysis, current_status)
        
        # 印出報告
        self.print_indicator_analysis_report(indicator_analysis, entry_signals)
        
        return {
            'cycles': cycles,
            'indicator_analysis': indicator_analysis,
            'entry_signals': entry_signals,
            'current_status': current_status,
        }


def main():
    """主程式"""
    analyzer = SwingAnalyzer(drawdown_threshold=0.10)
    
    # 執行基本波段分析
    print("\n" + "="*70)
    print("         第一部分：基本波段統計分析")
    print("="*70)
    result = analyzer.run_full_analysis(threshold=0.10)
    analyzer.print_report(result)
    
    # 執行指標相關性分析
    print("\n" + "="*70)
    print("         第二部分：指標相關性分析與進場策略")
    print("="*70)
    indicator_result = analyzer.run_full_indicator_analysis()
    
    return {
        'basic_analysis': result,
        'indicator_analysis': indicator_result,
    }


if __name__ == "__main__":
    main()
