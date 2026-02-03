"""
Backtest Runner Module
執行策略回測並計算績效
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from config import get_settings
from data import DataFetcher
from indicators import CombinedSignalGenerator
from .metrics import (
    PerformanceMetrics,
    calculate_returns,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_trade_statistics
)


class BacktestRunner:
    """
    回測執行器
    執行買賣策略的歷史回測並計算績效指標
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1% 手續費
        slippage: float = 0.0005,   # 0.05% 滑價
    ):
        """
        初始化回測器
        
        Args:
            initial_capital: 初始資金
            commission: 交易手續費比例
            slippage: 滑價比例
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.settings = get_settings()
    
    def run(
        self,
        nasdaq_data: pd.DataFrame,
        vix_data: pd.DataFrame,
        signal_generator: Optional[CombinedSignalGenerator] = None
    ) -> Tuple[PerformanceMetrics, pd.DataFrame]:
        """
        執行回測
        
        Args:
            nasdaq_data: 那斯達克指數資料
            vix_data: VIX 資料
            signal_generator: 信號產生器，若無則使用預設
            
        Returns:
            (績效指標, 詳細回測資料)
        """
        if signal_generator is None:
            signal_generator = CombinedSignalGenerator()
        
        # 產生歷史信號
        print("📊 產生歷史交易信號...")
        signals_df = signal_generator.generate_historical_signals(nasdaq_data, vix_data)
        
        # 執行回測模擬
        print("🔄 執行回測模擬...")
        backtest_result = self._simulate_trading(signals_df)
        
        # 計算績效指標
        print("📈 計算績效指標...")
        metrics = self._calculate_metrics(backtest_result, nasdaq_data)
        
        return metrics, backtest_result
    
    def _simulate_trading(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """
        模擬交易
        
        根據信號執行買賣，計算資產淨值變化
        """
        df = signals_df.copy()
        
        # 初始化 - 使用 float 類型避免型別衝突
        df['Position'] = 0.0       # 持倉比例 (0-1)
        df['Cash'] = float(self.initial_capital)
        df['Holdings'] = 0.0       # 持股價值
        df['Portfolio'] = float(self.initial_capital)  # 總資產
        df['Trade'] = 0.0          # 交易動作 (1=買, -1=賣, 0=無)
        df['Trade_Return'] = 0.0   # 單筆交易報酬
        
        position = 0.0
        cash = self.initial_capital
        entry_price = 0.0
        
        for i in range(len(df)):
            signal = df['Signal'].iloc[i]
            price = df['Close'].iloc[i]
            
            trade = 0
            trade_return = 0.0
            
            # 根據信號決定動作
            if signal in ['STRONG_BUY', 'BUY'] and position < 1.0:
                # 買入 (如果還有空間)
                if signal == 'STRONG_BUY':
                    target_position = 1.0  # 全倉
                else:
                    target_position = min(position + 0.5, 1.0)  # 半倉
                
                # 計算可買入金額
                buy_amount = (target_position - position) * cash
                if buy_amount > 0:
                    # 扣除手續費和滑價
                    actual_price = price * (1 + self.slippage)
                    cost = buy_amount * (1 + self.commission)
                    
                    if cost <= cash:
                        cash -= cost
                        position = target_position
                        entry_price = actual_price
                        trade = 1
            
            elif signal in ['STRONG_SELL', 'SELL'] and position > 0:
                # 賣出
                if signal == 'STRONG_SELL':
                    sell_ratio = 1.0  # 全部賣出
                else:
                    sell_ratio = 0.5  # 賣出一半
                
                sell_position = position * sell_ratio
                if sell_position > 0:
                    # 計算賣出金額
                    actual_price = price * (1 - self.slippage)
                    sell_value = sell_position * self.initial_capital * (actual_price / entry_price if entry_price > 0 else 1)
                    sell_value *= (1 - self.commission)
                    
                    # 計算此筆交易報酬
                    if entry_price > 0:
                        trade_return = (actual_price - entry_price) / entry_price
                    
                    cash += sell_value
                    position *= (1 - sell_ratio)
                    trade = -1
                    
                    if position == 0:
                        entry_price = 0
            
            # 計算當前資產
            holdings = position * self.initial_capital * (price / df['Close'].iloc[0])
            portfolio = cash + holdings
            
            # 記錄
            df.iloc[i, df.columns.get_loc('Position')] = position
            df.iloc[i, df.columns.get_loc('Cash')] = cash
            df.iloc[i, df.columns.get_loc('Holdings')] = holdings
            df.iloc[i, df.columns.get_loc('Portfolio')] = portfolio
            df.iloc[i, df.columns.get_loc('Trade')] = trade
            df.iloc[i, df.columns.get_loc('Trade_Return')] = trade_return
        
        # 計算每日報酬率
        df['Daily_Return'] = df['Portfolio'].pct_change()
        
        # 計算累積報酬
        df['Cumulative_Return'] = (df['Portfolio'] / self.initial_capital - 1) * 100
        
        # 計算基準 (買入持有)
        df['Benchmark'] = df['Close'] / df['Close'].iloc[0] * self.initial_capital
        df['Benchmark_Return'] = (df['Benchmark'] / self.initial_capital - 1) * 100
        
        return df
    
    def _calculate_metrics(
        self,
        backtest_result: pd.DataFrame,
        original_data: pd.DataFrame
    ) -> PerformanceMetrics:
        """計算績效指標"""
        
        df = backtest_result
        
        # 基本資訊
        start_date = df.index[0].strftime('%Y-%m-%d')
        end_date = df.index[-1].strftime('%Y-%m-%d')
        trading_days = len(df)
        years = trading_days / 252
        
        # 報酬計算
        final_value = df['Portfolio'].iloc[-1]
        total_return = (final_value / self.initial_capital - 1) * 100
        annualized_return = ((final_value / self.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        benchmark_final = df['Benchmark'].iloc[-1]
        benchmark_return = (benchmark_final / self.initial_capital - 1) * 100
        excess_return = total_return - benchmark_return
        
        # 風險計算
        daily_returns = df['Daily_Return'].dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        max_dd, max_dd_duration = calculate_max_drawdown(df['Portfolio'])
        
        # 風險調整報酬
        sharpe = calculate_sharpe_ratio(daily_returns)
        sortino = calculate_sortino_ratio(daily_returns)
        calmar = annualized_return / abs(max_dd) if max_dd != 0 else 0
        
        # 交易統計
        trades = df[df['Trade'] != 0].copy()
        if len(trades) > 0:
            trade_stats = calculate_trade_statistics(trades['Trade_Return'])
        else:
            trade_stats = {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
            }
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            volatility=volatility,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=trade_stats['total_trades'],
            win_rate=trade_stats['win_rate'],
            profit_factor=trade_stats['profit_factor'],
            avg_win=trade_stats['avg_win'],
            avg_loss=trade_stats['avg_loss'],
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days
        )
    
    def run_quick_backtest(
        self,
        start_date: str = "2020-01-01",
        end_date: Optional[str] = None
    ) -> Tuple[PerformanceMetrics, pd.DataFrame]:
        """
        快速執行回測
        
        自動下載資料並執行回測
        """
        fetcher = DataFetcher()
        
        print(f"📥 下載資料 ({start_date} ~ {end_date or '今天'})...")
        nasdaq_data, vix_data = fetcher.fetch_all(
            start_date=start_date,
            end_date=end_date,
            save_csv=False
        )
        
        return self.run(nasdaq_data, vix_data)


def main():
    """測試回測功能"""
    print("=" * 60)
    print("策略回測測試")
    print("=" * 60)
    
    runner = BacktestRunner(
        initial_capital=100000,
        commission=0.001,
        slippage=0.0005
    )
    
    # 執行回測
    metrics, result = runner.run_quick_backtest(start_date="2020-01-01")
    
    # 顯示結果
    print(metrics)
    
    # 檢查是否為好策略
    print("\n策略評估:")
    evaluation = metrics.is_good_strategy()
    for criterion, passed in evaluation.items():
        emoji = "✅" if passed else "❌"
        print(f"  {emoji} {criterion}")
    
    # 顯示最近交易
    trades = result[result['Trade'] != 0].tail(10)
    if len(trades) > 0:
        print(f"\n最近 10 筆交易:")
        print(trades[['Close', 'Signal', 'Trade', 'Position', 'Portfolio']].to_string())


if __name__ == "__main__":
    main()
