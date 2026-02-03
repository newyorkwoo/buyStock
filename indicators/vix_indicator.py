"""
VIX Indicator Module
VIX 恐慌指數分析 - 作為市場情緒的逆向指標
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np

from config import get_settings


@dataclass
class VIXScore:
    """VIX 評分結果"""
    value: float
    score: int  # -2 to +4
    sentiment: str
    signal: str  # BUY, SELL, HOLD
    description: str
    percentile: Optional[float] = None  # 歷史百分位


class VIXIndicator:
    """
    VIX 恐慌指數分析器
    VIX 是市場恐懼指標，作為逆向指標使用：
    - 高 VIX = 市場恐慌 = 潛在買點
    - 低 VIX = 市場樂觀 = 謹慎
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.thresholds = self.settings.vix
    
    def calculate_score(
        self,
        vix_value: float,
        historical_data: Optional[pd.DataFrame] = None
    ) -> VIXScore:
        """
        計算 VIX 評分
        
        VIX < 12: -2 (極度樂觀/自滿，謹慎)
        VIX 12-20: 0 (正常)
        VIX 20-25: +1 (輕度恐懼，逢低布局)
        VIX 25-30: +2 (恐懼，買入機會)
        VIX 30-40: +3 (高度恐懼，強烈買入信號)
        VIX > 40: +4 (極度恐慌，歷史級買點)
        
        Args:
            vix_value: 當前 VIX 值
            historical_data: 可選的歷史資料，用於計算百分位
            
        Returns:
            VIXScore 物件
        """
        # 計算歷史百分位
        percentile = None
        if historical_data is not None and len(historical_data) > 0:
            close_col = 'VIX_Close' if 'VIX_Close' in historical_data.columns else 'Close'
            if close_col in historical_data.columns:
                percentile = (
                    historical_data[close_col] < vix_value
                ).mean() * 100
        
        # 根據閾值評分
        if vix_value < 12:
            score = -2
            sentiment = "😎 極度樂觀 (Extreme Complacency)"
            signal = "SELL"
            desc = "市場過度自滿，謹慎追高"
        elif vix_value < self.thresholds.normal:
            score = 0
            sentiment = "😊 正常 (Normal)"
            signal = "HOLD"
            desc = "市場情緒正常"
        elif vix_value < self.thresholds.fear:
            score = 1
            sentiment = "😐 輕度恐懼 (Mild Fear)"
            signal = "HOLD"
            desc = "市場略有擔憂，可逢低布局"
        elif vix_value < self.thresholds.high_fear:
            score = 2
            sentiment = "😟 恐懼 (Fear)"
            signal = "BUY"
            desc = "市場恐懼，出現買入機會"
        elif vix_value < self.thresholds.extreme_fear:
            score = 3
            sentiment = "😨 高度恐懼 (High Fear)"
            signal = "BUY"
            desc = "市場高度恐懼，強烈買入信號"
        else:
            score = 4
            sentiment = "😱 極度恐慌 (Extreme Panic)"
            signal = "BUY"
            desc = "市場極度恐慌，歷史級買點"
        
        return VIXScore(
            value=round(vix_value, 2),
            score=score,
            sentiment=sentiment,
            signal=signal,
            description=desc,
            percentile=round(percentile, 1) if percentile else None
        )
    
    def add_vix_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        在 DataFrame 中添加 VIX 相關指標
        
        Args:
            df: 包含 VIX 資料的 DataFrame (需有 VIX_Close 或 Close 欄位)
            
        Returns:
            添加了 VIX 指標的 DataFrame
        """
        df = df.copy()
        
        # 確定 VIX 收盤價欄位名稱
        vix_col = 'VIX_Close' if 'VIX_Close' in df.columns else 'Close'
        
        if vix_col not in df.columns:
            raise ValueError(f"找不到 VIX 收盤價欄位: {vix_col}")
        
        vix = df[vix_col]
        
        # VIX 移動平均
        df['VIX_SMA_10'] = vix.rolling(window=10).mean()
        df['VIX_SMA_20'] = vix.rolling(window=20).mean()
        
        # VIX 相對於移動平均的位置
        df['VIX_vs_SMA20'] = (vix / df['VIX_SMA_20'] - 1) * 100
        
        # VIX 變化率
        df['VIX_Change_1D'] = vix.pct_change() * 100
        df['VIX_Change_5D'] = vix.pct_change(periods=5) * 100
        
        # VIX 波動率 (VIX 的標準差)
        df['VIX_Volatility'] = vix.rolling(window=20).std()
        
        # VIX 歷史百分位 (過去 252 天)
        df['VIX_Percentile'] = vix.rolling(window=252).apply(
            lambda x: (x < x.iloc[-1]).mean() * 100 if len(x) > 0 else 50,
            raw=False
        )
        
        # VIX 等級
        df['VIX_Level'] = pd.cut(
            vix,
            bins=[0, 12, 20, 25, 30, 40, 100],
            labels=['極度樂觀', '正常', '輕度恐懼', '恐懼', '高度恐懼', '極度恐慌']
        )
        
        # VIX 信號
        df['VIX_Signal'] = 'HOLD'
        df.loc[vix < 12, 'VIX_Signal'] = 'SELL'
        df.loc[vix >= self.thresholds.fear, 'VIX_Signal'] = 'BUY'
        
        # VIX 評分
        df['VIX_Score'] = df[vix_col].apply(lambda x: self._calculate_raw_score(x))
        
        return df
    
    def _calculate_raw_score(self, vix_value: float) -> int:
        """計算原始 VIX 評分"""
        if pd.isna(vix_value):
            return 0
        
        if vix_value < 12:
            return -2
        elif vix_value < self.thresholds.normal:
            return 0
        elif vix_value < self.thresholds.fear:
            return 1
        elif vix_value < self.thresholds.high_fear:
            return 2
        elif vix_value < self.thresholds.extreme_fear:
            return 3
        else:
            return 4
    
    def get_vix_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        取得 VIX 綜合分析
        
        Args:
            df: 包含 VIX 資料的 DataFrame
            
        Returns:
            VIX 分析結果字典
        """
        vix_col = 'VIX_Close' if 'VIX_Close' in df.columns else 'Close'
        
        if vix_col not in df.columns:
            raise ValueError("找不到 VIX 資料欄位")
        
        latest_vix = df[vix_col].iloc[-1]
        vix_score = self.calculate_score(latest_vix, df)
        
        # 計算統計資訊
        vix_series = df[vix_col]
        
        analysis = {
            'current': {
                'value': latest_vix,
                'score': vix_score.score,
                'signal': vix_score.signal,
                'sentiment': vix_score.sentiment,
                'description': vix_score.description,
                'percentile': vix_score.percentile
            },
            'statistics': {
                'mean': vix_series.mean(),
                'median': vix_series.median(),
                'std': vix_series.std(),
                'min': vix_series.min(),
                'max': vix_series.max(),
                'current_vs_mean': ((latest_vix / vix_series.mean()) - 1) * 100
            },
            'recent': {
                'change_1d': vix_series.pct_change().iloc[-1] * 100 if len(vix_series) > 1 else 0,
                'change_5d': vix_series.pct_change(5).iloc[-1] * 100 if len(vix_series) > 5 else 0,
                'change_20d': vix_series.pct_change(20).iloc[-1] * 100 if len(vix_series) > 20 else 0,
            }
        }
        
        return analysis


def main():
    """測試 VIX 指標計算"""
    import yfinance as yf
    
    print("=" * 60)
    print("VIX 恐慌指數分析測試")
    print("=" * 60)
    
    # 下載 VIX 資料
    vix_data = yf.download("^VIX", start="2024-01-01", progress=False)
    if isinstance(vix_data.columns, pd.MultiIndex):
        vix_data.columns = vix_data.columns.droplevel(1)
    
    indicator = VIXIndicator()
    
    # 添加指標
    df = indicator.add_vix_indicators(vix_data)
    
    # 顯示結果
    print("\n最近 5 日 VIX 指標:")
    print(df[['Close', 'VIX_SMA_20', 'VIX_Percentile', 'VIX_Level', 'VIX_Signal', 'VIX_Score']].tail())
    
    # 取得分析
    analysis = indicator.get_vix_analysis(vix_data)
    
    print(f"\n當前 VIX 分析:")
    print(f"  VIX 值: {analysis['current']['value']:.2f}")
    print(f"  市場情緒: {analysis['current']['sentiment']}")
    print(f"  信號: {analysis['current']['signal']} (Score: {analysis['current']['score']})")
    print(f"  說明: {analysis['current']['description']}")
    
    if analysis['current']['percentile']:
        print(f"  歷史百分位: {analysis['current']['percentile']:.1f}%")
    
    print(f"\n統計資訊:")
    print(f"  平均: {analysis['statistics']['mean']:.2f}")
    print(f"  中位數: {analysis['statistics']['median']:.2f}")
    print(f"  最小/最大: {analysis['statistics']['min']:.2f} / {analysis['statistics']['max']:.2f}")
    print(f"  當前 vs 平均: {analysis['statistics']['current_vs_mean']:+.1f}%")


if __name__ == "__main__":
    main()
