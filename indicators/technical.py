"""
Technical Indicators Module
計算 RSI、MACD、移動平均線、布林通道等技術指標
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

from config import get_settings


@dataclass
class IndicatorScore:
    """指標評分結果"""
    name: str
    value: float
    score: int  # -2 to +2
    signal: str  # BUY, SELL, HOLD
    description: str


class TechnicalIndicators:
    """
    技術指標計算器
    計算各種技術指標並產生評分
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算所有技術指標
        
        Args:
            df: 包含 OHLCV 資料的 DataFrame
            
        Returns:
            添加了技術指標欄位的 DataFrame
        """
        df = df.copy()
        
        # 確保使用正確的收盤價欄位
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # RSI
        df['RSI'] = RSIIndicator(
            close=close,
            window=self.settings.rsi.period
        ).rsi()
        
        # MACD
        macd = MACD(close=close)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Histogram'] = macd.macd_diff()
        
        # 移動平均線
        df['SMA_Short'] = SMAIndicator(
            close=close,
            window=self.settings.ma.short_period
        ).sma_indicator()
        
        df['SMA_Long'] = SMAIndicator(
            close=close,
            window=self.settings.ma.long_period
        ).sma_indicator()
        
        df['EMA_12'] = EMAIndicator(close=close, window=12).ema_indicator()
        df['EMA_26'] = EMAIndicator(close=close, window=26).ema_indicator()
        
        # 布林通道
        bb = BollingerBands(close=close)
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Middle'] = bb.bollinger_mavg()
        df['BB_Lower'] = bb.bollinger_lband()
        df['BB_Width'] = bb.bollinger_wband()
        df['BB_Percent'] = bb.bollinger_pband()
        
        # ATR (Average True Range)
        df['ATR'] = AverageTrueRange(
            high=high,
            low=low,
            close=close
        ).average_true_range()
        
        # Stochastic Oscillator
        stoch = StochasticOscillator(high=high, low=low, close=close)
        df['Stoch_K'] = stoch.stoch()
        df['Stoch_D'] = stoch.stoch_signal()
        
        # 計算信號
        df = self._calculate_signals(df)
        
        return df
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算各指標的交易信號"""
        df = df.copy()
        
        # RSI 信號
        df['RSI_Signal'] = 'HOLD'
        df.loc[df['RSI'] < self.settings.rsi.oversold, 'RSI_Signal'] = 'BUY'
        df.loc[df['RSI'] > self.settings.rsi.overbought, 'RSI_Signal'] = 'SELL'
        
        # MACD 信號 (金叉/死叉)
        df['MACD_Signal_Type'] = 'HOLD'
        df.loc[df['MACD'] > df['MACD_Signal'], 'MACD_Signal_Type'] = 'BUY'
        df.loc[df['MACD'] < df['MACD_Signal'], 'MACD_Signal_Type'] = 'SELL'
        
        # 移動平均線信號 (黃金交叉/死亡交叉)
        df['MA_Trend'] = 'NEUTRAL'
        df.loc[df['SMA_Short'] > df['SMA_Long'], 'MA_Trend'] = 'BULLISH'
        df.loc[df['SMA_Short'] < df['SMA_Long'], 'MA_Trend'] = 'BEARISH'
        
        # 布林通道信號
        df['BB_Signal'] = 'HOLD'
        df.loc[df['Close'] <= df['BB_Lower'], 'BB_Signal'] = 'BUY'
        df.loc[df['Close'] >= df['BB_Upper'], 'BB_Signal'] = 'SELL'
        
        return df
    
    def get_rsi_score(self, rsi_value: float) -> IndicatorScore:
        """
        計算 RSI 評分
        
        RSI < 20: +2 (強烈超賣)
        RSI < 30: +1 (超賣)
        RSI 30-70: 0 (中性)
        RSI > 70: -1 (超買)
        RSI > 80: -2 (強烈超買)
        """
        if pd.isna(rsi_value):
            return IndicatorScore(
                name="RSI",
                value=0,
                score=0,
                signal="HOLD",
                description="資料不足"
            )
        
        if rsi_value < 20:
            score, signal, desc = 2, "BUY", "強烈超賣"
        elif rsi_value < self.settings.rsi.oversold:
            score, signal, desc = 1, "BUY", "超賣"
        elif rsi_value > 80:
            score, signal, desc = -2, "SELL", "強烈超買"
        elif rsi_value > self.settings.rsi.overbought:
            score, signal, desc = -1, "SELL", "超買"
        else:
            score, signal, desc = 0, "HOLD", "中性區間"
        
        return IndicatorScore(
            name="RSI",
            value=round(rsi_value, 2),
            score=score,
            signal=signal,
            description=f"RSI={rsi_value:.1f} ({desc})"
        )
    
    def get_macd_score(
        self,
        macd: float,
        macd_signal: float,
        macd_hist: float,
        prev_macd_hist: Optional[float] = None
    ) -> IndicatorScore:
        """
        計算 MACD 評分
        
        MACD 金叉 + 柱狀圖轉正: +2
        MACD 金叉: +1
        MACD 死叉 + 柱狀圖轉負: -2
        MACD 死叉: -1
        """
        if pd.isna(macd) or pd.isna(macd_signal):
            return IndicatorScore(
                name="MACD",
                value=0,
                score=0,
                signal="HOLD",
                description="資料不足"
            )
        
        # 基本信號
        is_bullish = macd > macd_signal
        
        # 動量變化
        momentum_increasing = False
        if prev_macd_hist is not None and not pd.isna(prev_macd_hist):
            momentum_increasing = macd_hist > prev_macd_hist
        
        if is_bullish:
            if macd_hist > 0 and momentum_increasing:
                score, signal, desc = 2, "BUY", "金叉且動能增強"
            else:
                score, signal, desc = 1, "BUY", "金叉"
        else:
            if macd_hist < 0 and not momentum_increasing:
                score, signal, desc = -2, "SELL", "死叉且動能減弱"
            else:
                score, signal, desc = -1, "SELL", "死叉"
        
        return IndicatorScore(
            name="MACD",
            value=round(macd_hist, 4),
            score=score,
            signal=signal,
            description=f"MACD柱狀圖={macd_hist:.4f} ({desc})"
        )
    
    def get_ma_score(
        self,
        close: float,
        sma_short: float,
        sma_long: float
    ) -> IndicatorScore:
        """
        計算移動平均線評分
        
        黃金交叉 (短 > 長) + 價格在均線上方: +2
        黃金交叉: +1
        死亡交叉 (短 < 長) + 價格在均線下方: -2
        死亡交叉: -1
        """
        if pd.isna(sma_short) or pd.isna(sma_long):
            return IndicatorScore(
                name="MA",
                value=0,
                score=0,
                signal="HOLD",
                description="資料不足 (需要更長歷史資料)"
            )
        
        is_golden_cross = sma_short > sma_long
        price_above_ma = close > sma_short
        
        if is_golden_cross:
            if price_above_ma:
                score, signal, desc = 2, "BUY", "黃金交叉+價格在均線上方"
            else:
                score, signal, desc = 1, "BUY", "黃金交叉"
        else:
            if not price_above_ma:
                score, signal, desc = -2, "SELL", "死亡交叉+價格在均線下方"
            else:
                score, signal, desc = -1, "SELL", "死亡交叉"
        
        return IndicatorScore(
            name="MA",
            value=round(sma_short - sma_long, 2),
            score=score,
            signal=signal,
            description=f"SMA{self.settings.ma.short_period}-SMA{self.settings.ma.long_period}={sma_short-sma_long:.2f} ({desc})"
        )
    
    def get_latest_scores(self, df: pd.DataFrame) -> Dict[str, IndicatorScore]:
        """
        取得最新一筆資料的所有指標評分
        
        Returns:
            Dict containing scores for RSI, MACD, MA
        """
        if len(df) < 2:
            raise ValueError("資料筆數不足")
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        return {
            'rsi': self.get_rsi_score(latest.get('RSI')),
            'macd': self.get_macd_score(
                latest.get('MACD'),
                latest.get('MACD_Signal'),
                latest.get('MACD_Histogram'),
                prev.get('MACD_Histogram')
            ),
            'ma': self.get_ma_score(
                latest['Close'],
                latest.get('SMA_Short'),
                latest.get('SMA_Long')
            )
        }


def main():
    """測試技術指標計算"""
    import yfinance as yf
    
    print("=" * 60)
    print("技術指標計算測試")
    print("=" * 60)
    
    # 下載測試資料
    data = yf.download("^IXIC", start="2024-01-01", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    
    # 計算指標
    indicators = TechnicalIndicators()
    df = indicators.calculate_all(data)
    
    # 顯示結果
    print("\n最近 5 日指標:")
    print(df[['Close', 'RSI', 'MACD', 'MACD_Signal', 'SMA_Short', 'SMA_Long']].tail())
    
    # 取得評分
    scores = indicators.get_latest_scores(df)
    
    print("\n最新評分:")
    for name, score in scores.items():
        print(f"  {score.name}: {score.signal} (Score: {score.score}) - {score.description}")


if __name__ == "__main__":
    main()
