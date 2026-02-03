"""
Performance Metrics Module
計算回測績效指標
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """績效指標結果"""
    # 報酬
    total_return: float          # 總報酬率 (%)
    annualized_return: float     # 年化報酬率 (%)
    benchmark_return: float      # 基準報酬率 (買入持有)
    excess_return: float         # 超額報酬 (vs 基準)
    
    # 風險
    volatility: float            # 年化波動率 (%)
    max_drawdown: float          # 最大回撤 (%)
    max_drawdown_duration: int   # 最大回撤持續天數
    
    # 風險調整報酬
    sharpe_ratio: float          # 夏普比率
    sortino_ratio: float         # 索提諾比率
    calmar_ratio: float          # 卡瑪比率
    
    # 交易統計
    total_trades: int            # 總交易次數
    win_rate: float              # 勝率 (%)
    profit_factor: float         # 獲利因子
    avg_win: float               # 平均獲利 (%)
    avg_loss: float              # 平均虧損 (%)
    
    # 期間
    start_date: str
    end_date: str
    trading_days: int
    
    def __str__(self) -> str:
        """格式化輸出"""
        lines = [
            "=" * 60,
            "📊 回測績效報告",
            "=" * 60,
            f"期間: {self.start_date} ~ {self.end_date} ({self.trading_days} 交易日)",
            "",
            "--- 報酬指標 ---",
            f"總報酬率:      {self.total_return:+.2f}%",
            f"年化報酬率:    {self.annualized_return:+.2f}%",
            f"基準報酬 (B&H): {self.benchmark_return:+.2f}%",
            f"超額報酬:      {self.excess_return:+.2f}%",
            "",
            "--- 風險指標 ---",
            f"年化波動率:    {self.volatility:.2f}%",
            f"最大回撤:      {self.max_drawdown:.2f}%",
            f"最大回撤天數:  {self.max_drawdown_duration} 天",
            "",
            "--- 風險調整報酬 ---",
            f"夏普比率:      {self.sharpe_ratio:.3f}",
            f"索提諾比率:    {self.sortino_ratio:.3f}",
            f"卡瑪比率:      {self.calmar_ratio:.3f}",
            "",
            "--- 交易統計 ---",
            f"總交易次數:    {self.total_trades}",
            f"勝率:          {self.win_rate:.1f}%",
            f"獲利因子:      {self.profit_factor:.2f}",
            f"平均獲利:      {self.avg_win:+.2f}%",
            f"平均虧損:      {self.avg_loss:.2f}%",
            "=" * 60,
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'returns': {
                'total_return': self.total_return,
                'annualized_return': self.annualized_return,
                'benchmark_return': self.benchmark_return,
                'excess_return': self.excess_return,
            },
            'risk': {
                'volatility': self.volatility,
                'max_drawdown': self.max_drawdown,
                'max_drawdown_duration': self.max_drawdown_duration,
            },
            'risk_adjusted': {
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'calmar_ratio': self.calmar_ratio,
            },
            'trades': {
                'total_trades': self.total_trades,
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
            },
            'period': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'trading_days': self.trading_days,
            }
        }
    
    def is_good_strategy(self) -> Dict[str, bool]:
        """
        評估策略是否符合基本標準
        
        Returns:
            各指標是否達標
        """
        return {
            'sharpe_above_1': self.sharpe_ratio > 1.0,
            'max_dd_below_20': self.max_drawdown > -20,
            'win_rate_above_40': self.win_rate > 40,
            'profit_factor_above_1.5': self.profit_factor > 1.5,
            'beats_benchmark': self.excess_return > 0,
        }


def calculate_returns(portfolio_values: pd.Series) -> pd.Series:
    """計算日報酬率"""
    return portfolio_values.pct_change().dropna()


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    計算夏普比率
    
    Sharpe = (年化報酬 - 無風險利率) / 年化波動率
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / periods_per_year
    return np.sqrt(periods_per_year) * excess_returns.mean() / returns.std()


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    計算索提諾比率
    
    只考慮下行風險（負報酬的標準差）
    """
    if len(returns) == 0:
        return 0.0
    
    negative_returns = returns[returns < 0]
    
    if len(negative_returns) == 0 or negative_returns.std() == 0:
        return float('inf') if returns.mean() > 0 else 0.0
    
    downside_std = negative_returns.std()
    excess_return = returns.mean() - risk_free_rate / periods_per_year
    
    return np.sqrt(periods_per_year) * excess_return / downside_std


def calculate_max_drawdown(portfolio_values: pd.Series) -> tuple:
    """
    計算最大回撤
    
    Returns:
        (最大回撤百分比, 最大回撤持續天數)
    """
    if len(portfolio_values) == 0:
        return 0.0, 0
    
    # 計算累積最高點
    running_max = portfolio_values.expanding().max()
    
    # 計算回撤
    drawdown = (portfolio_values - running_max) / running_max * 100
    
    max_dd = drawdown.min()
    
    # 計算最大回撤持續時間
    is_drawdown = drawdown < 0
    
    if not is_drawdown.any():
        return 0.0, 0
    
    # 找出最大回撤的起點和終點
    drawdown_groups = (is_drawdown != is_drawdown.shift()).cumsum()
    drawdown_groups = drawdown_groups[is_drawdown]
    
    if len(drawdown_groups) == 0:
        return max_dd, 0
    
    max_duration = drawdown_groups.value_counts().max()
    
    return max_dd, int(max_duration)


def calculate_trade_statistics(
    trades: pd.DataFrame
) -> Dict[str, float]:
    """
    計算交易統計
    
    Args:
        trades: 包含 'return' 欄位的交易記錄，或直接是報酬率 Series
        
    Returns:
        交易統計字典
    """
    if trades is None or len(trades) == 0:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
        }
    
    # 處理 DataFrame 或 Series
    if isinstance(trades, pd.DataFrame):
        returns = trades['return'] if 'return' in trades.columns else trades.iloc[:, 0]
    else:
        returns = trades
    
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    
    total_trades = len(returns)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = wins.sum() if len(wins) > 0 else 0
    total_loss = abs(losses.sum()) if len(losses) > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    avg_win = wins.mean() * 100 if len(wins) > 0 else 0
    avg_loss = losses.mean() * 100 if len(losses) > 0 else 0
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
    }
