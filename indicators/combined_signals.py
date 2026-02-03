"""
Combined Signal Generator Module
整合多項技術指標與 VIX 的加權評分系統，產生綜合買賣建議
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

import pandas as pd
import numpy as np

from config import get_settings
from .technical import TechnicalIndicators, IndicatorScore
from .vix_indicator import VIXIndicator, VIXScore


class SignalType(Enum):
    """交易信號類型"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class SignalResult:
    """綜合信號結果"""
    signal: SignalType
    total_score: float
    confidence: float  # 0-100%
    
    # 各指標評分
    rsi_score: IndicatorScore
    macd_score: IndicatorScore
    ma_score: IndicatorScore
    vix_score: VIXScore
    
    # 市場資訊
    nasdaq_price: float
    nasdaq_change: float  # 日變化百分比
    vix_value: float
    
    # 時間戳記
    date: str
    
    # 詳細說明
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'signal': self.signal.value,
            'total_score': self.total_score,
            'confidence': self.confidence,
            'date': self.date,
            'nasdaq_price': self.nasdaq_price,
            'nasdaq_change': self.nasdaq_change,
            'vix_value': self.vix_value,
            'scores': {
                'rsi': {'value': self.rsi_score.value, 'score': self.rsi_score.score, 'signal': self.rsi_score.signal},
                'macd': {'value': self.macd_score.value, 'score': self.macd_score.score, 'signal': self.macd_score.signal},
                'ma': {'value': self.ma_score.value, 'score': self.ma_score.score, 'signal': self.ma_score.signal},
                'vix': {'value': self.vix_score.value, 'score': self.vix_score.score, 'signal': self.vix_score.signal},
            },
            'summary': self.summary,
            'recommendations': self.recommendations
        }
    
    def __str__(self) -> str:
        """格式化輸出"""
        signal_emoji = {
            SignalType.STRONG_BUY: "🚀",
            SignalType.BUY: "📈",
            SignalType.HOLD: "⏸️",
            SignalType.SELL: "📉",
            SignalType.STRONG_SELL: "🔻"
        }
        
        lines = [
            "=" * 60,
            f"📊 那斯達克買賣建議報告 - {self.date}",
            "=" * 60,
            "",
            f"🎯 綜合建議: {signal_emoji.get(self.signal, '')} {self.signal.value}",
            f"📈 綜合評分: {self.total_score:.2f} (信心度: {self.confidence:.1f}%)",
            "",
            "--- 市場概況 ---",
            f"那斯達克指數: {self.nasdaq_price:,.2f} ({self.nasdaq_change:+.2f}%)",
            f"VIX 恐慌指數: {self.vix_value:.2f} - {self.vix_score.sentiment}",
            "",
            "--- 指標分析 ---",
            f"RSI:  {self.rsi_score.description} [Score: {self.rsi_score.score:+d}]",
            f"MACD: {self.macd_score.description} [Score: {self.macd_score.score:+d}]",
            f"MA:   {self.ma_score.description} [Score: {self.ma_score.score:+d}]",
            f"VIX:  {self.vix_score.description} [Score: {self.vix_score.score:+d}]",
            "",
            "--- 建議摘要 ---",
            self.summary,
        ]
        
        if self.recommendations:
            lines.append("")
            lines.append("--- 操作建議 ---")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


class CombinedSignalGenerator:
    """
    綜合信號產生器
    整合 RSI、MACD、移動平均線與 VIX 產生買賣建議
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化信號產生器
        
        Args:
            weights: 各指標權重，預設為均等權重
                     {'rsi': 0.25, 'macd': 0.25, 'ma': 0.25, 'vix': 0.25}
        """
        self.settings = get_settings()
        self.technical = TechnicalIndicators()
        self.vix_indicator = VIXIndicator()
        
        # 預設權重
        if weights is None:
            self.weights = {
                'rsi': self.settings.weights.rsi,
                'macd': self.settings.weights.macd,
                'ma': self.settings.weights.ma,
                'vix': self.settings.weights.vix
            }
        else:
            self.weights = weights
        
        # 確保權重總和為 1
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            for key in self.weights:
                self.weights[key] /= total_weight
    
    def generate_signal(
        self,
        nasdaq_data: pd.DataFrame,
        vix_data: pd.DataFrame
    ) -> SignalResult:
        """
        產生綜合買賣信號
        
        Args:
            nasdaq_data: 那斯達克指數資料 (需包含 OHLCV)
            vix_data: VIX 恐慌指數資料
            
        Returns:
            SignalResult 物件
        """
        # 計算那斯達克技術指標
        nasdaq_with_indicators = self.technical.calculate_all(nasdaq_data)
        
        # 取得最新資料
        latest_nasdaq = nasdaq_with_indicators.iloc[-1]
        prev_nasdaq = nasdaq_with_indicators.iloc[-2] if len(nasdaq_with_indicators) > 1 else latest_nasdaq
        
        # 確定 VIX 收盤價欄位
        vix_close_col = 'Close'
        if isinstance(vix_data.columns, pd.MultiIndex):
            vix_data.columns = vix_data.columns.droplevel(1)
        
        latest_vix = vix_data[vix_close_col].iloc[-1]
        
        # 計算各指標評分
        rsi_score = self.technical.get_rsi_score(latest_nasdaq.get('RSI'))
        
        macd_score = self.technical.get_macd_score(
            latest_nasdaq.get('MACD'),
            latest_nasdaq.get('MACD_Signal'),
            latest_nasdaq.get('MACD_Histogram'),
            prev_nasdaq.get('MACD_Histogram')
        )
        
        ma_score = self.technical.get_ma_score(
            latest_nasdaq['Close'],
            latest_nasdaq.get('SMA_Short'),
            latest_nasdaq.get('SMA_Long')
        )
        
        vix_score = self.vix_indicator.calculate_score(latest_vix, vix_data)
        
        # 計算加權總分
        # 注意：VIX 評分範圍是 -2 到 +4，需要標準化
        normalized_vix_score = min(max(vix_score.score, -2), 2)  # 限制在 -2 到 +2
        
        total_score = (
            rsi_score.score * self.weights['rsi'] +
            macd_score.score * self.weights['macd'] +
            ma_score.score * self.weights['ma'] +
            normalized_vix_score * self.weights['vix']
        )
        
        # 決定最終信號
        signal = self._determine_signal(total_score, vix_score.score)
        
        # 計算信心度 (根據指標一致性)
        confidence = self._calculate_confidence(
            rsi_score, macd_score, ma_score, vix_score
        )
        
        # 計算價格變化
        nasdaq_change = (
            (latest_nasdaq['Close'] - prev_nasdaq['Close']) / prev_nasdaq['Close'] * 100
        )
        
        # 產生建議摘要
        summary, recommendations = self._generate_recommendations(
            signal, rsi_score, macd_score, ma_score, vix_score, total_score
        )
        
        return SignalResult(
            signal=signal,
            total_score=total_score,
            confidence=confidence,
            rsi_score=rsi_score,
            macd_score=macd_score,
            ma_score=ma_score,
            vix_score=vix_score,
            nasdaq_price=latest_nasdaq['Close'],
            nasdaq_change=nasdaq_change,
            vix_value=latest_vix,
            date=latest_nasdaq.name.strftime('%Y-%m-%d'),
            summary=summary,
            recommendations=recommendations
        )
    
    def _determine_signal(self, total_score: float, vix_raw_score: int) -> SignalType:
        """
        決定最終交易信號
        
        考慮總分與 VIX 的特殊情況
        """
        # VIX 極端值的特殊處理
        if vix_raw_score >= 4:  # 極度恐慌
            if total_score >= 0:
                return SignalType.STRONG_BUY
            else:
                return SignalType.BUY
        elif vix_raw_score <= -2:  # 極度樂觀
            if total_score <= 0:
                return SignalType.STRONG_SELL
            else:
                return SignalType.SELL
        
        # 一般情況根據總分決定
        if total_score >= 1.5:
            return SignalType.STRONG_BUY
        elif total_score >= 0.5:
            return SignalType.BUY
        elif total_score <= -1.5:
            return SignalType.STRONG_SELL
        elif total_score <= -0.5:
            return SignalType.SELL
        else:
            return SignalType.HOLD
    
    def _calculate_confidence(
        self,
        rsi_score: IndicatorScore,
        macd_score: IndicatorScore,
        ma_score: IndicatorScore,
        vix_score: VIXScore
    ) -> float:
        """
        計算信號信心度
        
        根據指標信號一致性計算
        """
        scores = [
            rsi_score.score,
            macd_score.score,
            ma_score.score,
            min(max(vix_score.score, -2), 2)  # 標準化 VIX 評分
        ]
        
        # 計算信號一致性
        positive_count = sum(1 for s in scores if s > 0)
        negative_count = sum(1 for s in scores if s < 0)
        
        # 一致性越高，信心度越高
        agreement = max(positive_count, negative_count) / len(scores)
        
        # 評分強度
        avg_strength = np.mean([abs(s) for s in scores])
        
        # 綜合信心度
        confidence = agreement * 50 + (avg_strength / 2) * 50
        
        return min(confidence, 100)
    
    def _generate_recommendations(
        self,
        signal: SignalType,
        rsi_score: IndicatorScore,
        macd_score: IndicatorScore,
        ma_score: IndicatorScore,
        vix_score: VIXScore,
        total_score: float
    ) -> tuple:
        """產生建議摘要與操作建議"""
        
        # 統計多空指標數量
        bullish_count = sum(1 for s in [rsi_score.score, macd_score.score, ma_score.score, vix_score.score] if s > 0)
        bearish_count = sum(1 for s in [rsi_score.score, macd_score.score, ma_score.score, vix_score.score] if s < 0)
        neutral_count = 4 - bullish_count - bearish_count
        
        # 取得各指標數值
        rsi_val = rsi_score.value
        vix_val = vix_score.value
        
        # 建構動態摘要
        summary_parts = []
        
        # 主要趨勢判斷
        if signal == SignalType.STRONG_BUY:
            summary_parts.append(f"🔥 強力買入訊號！{bullish_count}/4 指標看多")
            if vix_val > 30:
                summary_parts.append(f"VIX={vix_val:.1f} 顯示市場恐慌，歷史經驗這是絕佳買點")
            if rsi_val < 30:
                summary_parts.append(f"RSI={rsi_val:.1f} 超賣區，反彈機率高")
        elif signal == SignalType.BUY:
            summary_parts.append(f"📈 偏多格局，{bullish_count}/4 指標看多")
            if ma_score.score > 0:
                summary_parts.append("均線多頭排列，順勢做多")
            if rsi_val < 40:
                summary_parts.append(f"RSI={rsi_val:.1f} 尚在低檔，可考慮分批布局")
        elif signal == SignalType.HOLD:
            summary_parts.append(f"⏸️ 多空交戰中（多:{bullish_count} 空:{bearish_count} 中:{neutral_count}）")
            summary_parts.append("建議觀望，等待方向明確再行動")
        elif signal == SignalType.SELL:
            summary_parts.append(f"📉 偏空格局，{bearish_count}/4 指標看空")
            if rsi_val > 60:
                summary_parts.append(f"RSI={rsi_val:.1f} 偏高，注意回檔風險")
            summary_parts.append("考慮減碼或設定停損保護")
        else:  # STRONG_SELL
            summary_parts.append(f"⚠️ 強力賣出訊號！{bearish_count}/4 指標看空")
            if vix_val < 15:
                summary_parts.append(f"VIX={vix_val:.1f} 過低，市場過度樂觀")
            if rsi_val > 70:
                summary_parts.append(f"RSI={rsi_val:.1f} 超買區，回調風險高")
        
        summary = "。".join(summary_parts) + "。"
        
        # 操作建議
        recommendations = []
        
        # 根據 VIX 給出建議
        if vix_score.score >= 3:
            recommendations.append("VIX 處於高位，歷史經驗顯示這往往是不錯的買點，可分批進場")
        elif vix_score.score <= -2:
            recommendations.append("VIX 過低顯示市場過度樂觀，注意回調風險")
        
        # 根據 RSI 給出建議
        if rsi_score.score >= 2:
            recommendations.append("RSI 超賣，短線可能有反彈機會")
        elif rsi_score.score <= -2:
            recommendations.append("RSI 超買，注意短線回檔風險")
        
        # 根據 MA 趨勢給出建議
        if ma_score.score >= 1:
            recommendations.append("中長期趨勢向上（黃金交叉），順勢操作")
        elif ma_score.score <= -1:
            recommendations.append("中長期趨勢向下（死亡交叉），宜保守操作")
        
        # 根據 MACD 給出建議
        if macd_score.score >= 1:
            recommendations.append("MACD 金叉，短線動能轉強")
        elif macd_score.score <= -1:
            recommendations.append("MACD 死叉，短線動能轉弱")
        
        # 風險提示
        recommendations.append("此為技術分析建議，投資有風險，請依個人風險承受能力做決策")
        
        return summary, recommendations
    
    def generate_historical_signals(
        self,
        nasdaq_data: pd.DataFrame,
        vix_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        產生歷史信號序列（用於回測）
        
        Returns:
            包含每日信號的 DataFrame
        """
        # 計算技術指標
        nasdaq_with_indicators = self.technical.calculate_all(nasdaq_data)
        
        # 合併 VIX 資料
        if isinstance(vix_data.columns, pd.MultiIndex):
            vix_data.columns = vix_data.columns.droplevel(1)
        
        vix_renamed = vix_data[['Close']].rename(columns={'Close': 'VIX_Close'})
        merged = nasdaq_with_indicators.join(vix_renamed, how='inner')
        
        # 添加 VIX 指標
        merged = self.vix_indicator.add_vix_indicators(merged)
        
        # 計算綜合評分
        merged['RSI_Score'] = merged['RSI'].apply(
            lambda x: self.technical.get_rsi_score(x).score
        )
        
        # MACD 評分需要前一天的柱狀圖
        merged['MACD_Score'] = 0
        for i in range(1, len(merged)):
            score = self.technical.get_macd_score(
                merged['MACD'].iloc[i],
                merged['MACD_Signal'].iloc[i],
                merged['MACD_Histogram'].iloc[i],
                merged['MACD_Histogram'].iloc[i-1]
            )
            merged.iloc[i, merged.columns.get_loc('MACD_Score')] = score.score
        
        # MA 評分
        def ma_score_func(row):
            return self.technical.get_ma_score(
                row['Close'],
                row['SMA_Short'],
                row['SMA_Long']
            ).score
        merged['MA_Score'] = merged.apply(ma_score_func, axis=1)
        
        # VIX 評分已在 add_vix_indicators 中計算
        
        # 計算加權總分
        merged['Total_Score'] = (
            merged['RSI_Score'] * self.weights['rsi'] +
            merged['MACD_Score'] * self.weights['macd'] +
            merged['MA_Score'] * self.weights['ma'] +
            merged['VIX_Score'].clip(-2, 2) * self.weights['vix']
        )
        
        # 產生信號
        merged['Signal'] = merged['Total_Score'].apply(self._score_to_signal)
        
        return merged
    
    def _score_to_signal(self, score: float) -> str:
        """將分數轉換為信號字串"""
        if score >= 1.5:
            return "STRONG_BUY"
        elif score >= 0.5:
            return "BUY"
        elif score <= -1.5:
            return "STRONG_SELL"
        elif score <= -0.5:
            return "SELL"
        else:
            return "HOLD"


def main():
    """測試綜合信號產生"""
    from data import DataFetcher
    
    print("=" * 60)
    print("綜合信號產生測試")
    print("=" * 60)
    
    # 下載資料
    fetcher = DataFetcher()
    nasdaq_data, vix_data = fetcher.fetch_all(start_date="2024-01-01", save_csv=False)
    
    # 產生信號
    generator = CombinedSignalGenerator()
    result = generator.generate_signal(nasdaq_data, vix_data)
    
    print(result)


if __name__ == "__main__":
    main()
