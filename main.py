"""
NASDAQ Trading Suggestion System - Main Entry Point
那斯達克買賣建議系統主程式

Usage:
    python main.py              # 執行分析並顯示建議
    python main.py --download   # 下載最新資料
    python main.py --backtest   # 執行回測
    python main.py --notify     # 執行分析並發送通知
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# 將專案根目錄加入 Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from data import DataFetcher
from indicators import CombinedSignalGenerator, TechnicalIndicators
from notifications import NotificationManager
from backtesting import BacktestRunner
from visualization import ChartGenerator
from analysis import SwingAnalyzer


def print_banner():
    """印出程式標題"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       📈 那斯達克買賣建議系統 (NASDAQ Trading Advisor) 📉      ║
║                                                               ║
║       整合 VIX + RSI + MACD + 移動平均線 的多指標策略          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def download_data(save: bool = True):
    """下載最新的完整歷史資料 (從 2000 年至今)"""
    import yfinance as yf
    from datetime import timedelta
    import pytz
    
    print("\n📥 下載那斯達克指數與 VIX 完整歷史資料 (2000-至今)...")
    print("-" * 50)
    
    # 取得專案根目錄
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    nasdaq_2000_file = data_dir / "nasdaq_2000.csv"
    vix_2000_file = data_dir / "vix_2000.csv"
    nasdaq_historical_file = data_dir / "nasdaq_historical.csv"
    vix_historical_file = data_dir / "vix_historical.csv"
    
    # 使用台灣時區
    tw_tz = pytz.timezone('Asia/Taipei')
    tw_now = datetime.now(tw_tz)
    today = tw_now.strftime("%Y-%m-%d")
    end_date = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = "2000-01-01"
    
    print(f"   📥 下載 NASDAQ 指數 ({start_date} ~ {today})...")
    nasdaq_data = yf.download("^IXIC", start=start_date, end=end_date, progress=False)
    
    if save:
        nasdaq_data.to_csv(nasdaq_2000_file)
        nasdaq_data.to_csv(nasdaq_historical_file)  # 同時更新歷史檔案
        print(f"   ✅ NASDAQ 資料: {len(nasdaq_data)} 筆")
        print(f"      已儲存至: {nasdaq_2000_file.name}")
    
    print(f"   📥 下載 VIX 指數...")
    vix_data = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    if save:
        vix_data.to_csv(vix_2000_file)
        vix_data.to_csv(vix_historical_file)  # 同時更新歷史檔案
        print(f"   ✅ VIX 資料: {len(vix_data)} 筆")
        print(f"      已儲存至: {vix_2000_file.name}")
    
    print(f"   📅 資料範圍: {nasdaq_data.index[0].strftime('%Y-%m-%d')} ~ {nasdaq_data.index[-1].strftime('%Y-%m-%d')}")
    print("   ✅ 資料下載完成！")
    
    return nasdaq_data, vix_data


def run_backtest(start_date="2015-01-01", end_date=None):
    """執行策略回測"""
    print("\n📊 執行策略回測...")
    print("-" * 50)
    
    runner = BacktestRunner(
        initial_capital=100000,
        commission=0.001,
        slippage=0.0005
    )
    
    metrics, result_df = runner.run_quick_backtest(
        start_date=start_date,
        end_date=end_date
    )
    
    # 顯示結果
    print(metrics)
    
    # 策略評估
    print("\n🎯 策略評估:")
    print("-" * 50)
    evaluation = metrics.is_good_strategy()
    
    all_passed = True
    for criterion, passed in evaluation.items():
        emoji = "✅" if passed else "❌"
        print(f"   {emoji} {criterion.replace('_', ' ')}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n   🎉 策略通過所有基本標準！")
    else:
        print("\n   ⚠️ 策略未通過部分標準，建議調整參數")
    
    return metrics, result_df


def generate_interactive_report():
    """產生互動式 HTML 報告 (可捲動、縮放) - 2000年至今"""
    import webbrowser
    import pytz
    
    print("\n📊 產生互動式 HTML 報告 (2000年至今)...")
    print("-" * 50)
    
    # 讀取已下載的歷史資料
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "raw"
    nasdaq_2000_file = data_dir / "nasdaq_2000.csv"
    vix_2000_file = data_dir / "vix_2000.csv"
    
    # 讀取 CSV 檔案
    print("   📂 讀取歷史資料...")
    nasdaq_data = pd.read_csv(nasdaq_2000_file, index_col=0, parse_dates=True, header=[0, 1])
    vix_data = pd.read_csv(vix_2000_file, index_col=0, parse_dates=True, header=[0, 1])
    
    # 扁平化 MultiIndex columns
    if isinstance(nasdaq_data.columns, pd.MultiIndex):
        nasdaq_data.columns = nasdaq_data.columns.get_level_values(0)
    if isinstance(vix_data.columns, pd.MultiIndex):
        vix_data.columns = vix_data.columns.get_level_values(0)
    
    # 確保 index 是 datetime 類型
    if not isinstance(nasdaq_data.index, pd.DatetimeIndex):
        nasdaq_data.index = pd.to_datetime(nasdaq_data.index)
    if not isinstance(vix_data.index, pd.DatetimeIndex):
        vix_data.index = pd.to_datetime(vix_data.index)
    
    # 顯示資料資訊
    us_et = pytz.timezone('US/Eastern')
    us_now = datetime.now(us_et)
    print(f"   ✅ 資料範圍: {nasdaq_data.index[0].strftime('%Y-%m-%d')} ~ {nasdaq_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"   🕒 美東時間: {us_now.strftime('%Y-%m-%d %H:%M %Z')} (美股交易時間 09:30-16:00)")
    print(f"   📊 共 {len(nasdaq_data)} 筆資料")
    
    # 計算技術指標
    print("   🔮 計算技術指標...")
    tech = TechnicalIndicators()
    df = tech.calculate_all(nasdaq_data)
    
    # 合併 VIX
    vix_renamed = vix_data[['Close']].rename(columns={'Close': 'VIX_Close'})
    df = df.join(vix_renamed, how='inner')
    
    # 產生交易信號
    print("   📈 產生交易建議...")
    generator = CombinedSignalGenerator()
    result = generator.generate_signal(nasdaq_data, vix_data)
    
    # 執行波段分析
    print("   📊 執行波段指標相關性分析...")
    analyzer = SwingAnalyzer()
    swing_df = analyzer.load_data()
    cycles = analyzer.find_swing_cycles(swing_df, threshold=0.10)
    indicator_analysis = analyzer.analyze_indicators_at_troughs(swing_df, cycles)
    current_status = analyzer.get_current_status(swing_df)
    entry_signals = analyzer.generate_entry_signals(indicator_analysis, current_status)
    
    swing_analysis = {
        'indicator_analysis': indicator_analysis,
        'entry_signals': entry_signals,
        'current_status': current_status,
    }
    
    # 產生互動式報告 - 顯示所有資料
    print("   🎨 產生互動式圖表...")
    charts = ChartGenerator()
    report_path = charts.save_interactive_report(
        df=df,
        signal_result=result,
        vix_data=vix_data,
        days=len(df),  # 顯示所有歷史資料
        swing_analysis=swing_analysis
    )
    
    print(f"\n   ✅ 報告已儲存: {report_path}")
    
    # 自動開啟瀏覽器
    print("   🌐 開啟瀏覽器...")
    webbrowser.open(f'file://{report_path}')
    
    print("\n💡 提示: HTML 報告支援:")
    print("   • 🖱️ 滑鼠滾輪捲動檢視")
    print("   • 🔍 點擊拖曳縮放圖表")
    print("   • 📊 hover 顯示詳細數據")
    print("   • 📤 右上角工具列可下載圖片")
    print("   • 💰 波段分析與大資金進場策略")


def show_status():
    """顯示系統狀態"""
    settings = get_settings()
    
    print("\n⚙️ 系統設定狀態:")
    print("-" * 50)
    
    print(f"   資料起始日期: {settings.start_date}")
    print(f"   那斯達克代號: {settings.nasdaq_symbol}")
    print(f"   VIX 代號: {settings.vix_symbol}")
    
    print(f"\n   指標權重:")
    print(f"     RSI:  {settings.weights.rsi * 100:.0f}%")
    print(f"     MACD: {settings.weights.macd * 100:.0f}%")
    print(f"     MA:   {settings.weights.ma * 100:.0f}%")
    print(f"     VIX:  {settings.weights.vix * 100:.0f}%")
    
    print(f"\n   VIX 閾值:")
    print(f"     正常: < {settings.vix.normal}")
    print(f"     恐懼: {settings.vix.normal} - {settings.vix.fear}")
    print(f"     高度恐懼: {settings.vix.fear} - {settings.vix.high_fear}")
    print(f"     極度恐慌: > {settings.vix.extreme_fear}")
    
    # 通知狀態
    manager = NotificationManager()
    manager.print_status()


def analyze_swing_history():
    """執行歷史波段分析"""
    print("\n" + "=" * 70)
    print("📊 執行歷史波段分析 (2000/01/01 至今)")
    print("=" * 70)
    
    # 取得專案根目錄
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "raw"
    
    nasdaq_file = data_dir / "nasdaq_2000.csv"
    vix_file = data_dir / "vix_2000.csv"
    
    # 確認資料檔案存在
    if not nasdaq_file.exists() or not vix_file.exists():
        print("\n❌ 錯誤: 歷史資料檔案不存在")
        print("   請先執行 python main.py --download 下載資料")
        return
    
    print(f"   📂 使用已下載的歷史資料")
    print(f"   • NASDAQ: {nasdaq_file.name}")
    print(f"   • VIX: {vix_file.name}")
    
    # 執行波段分析
    analyzer = SwingAnalyzer()
    
    # 第一部分：基本波段統計
    result = analyzer.run_full_analysis(threshold=0.10)
    analyzer.print_report(result)
    
    # 第二部分：指標相關性分析與大資金進場策略
    print("\n" + "=" * 70)
    print("         第二部分：指標相關性分析與進場策略")
    print("=" * 70)
    indicator_result = analyzer.run_full_indicator_analysis()


def main():
    """主程式進入點"""
    parser = argparse.ArgumentParser(
        description="那斯達克買賣建議系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
    python main.py                    # 產生互動式 HTML 報告（預設）
    python main.py --download         # 下載最新資料
    python main.py --backtest         # 執行策略回測
    python main.py --status           # 顯示系統狀態
    python main.py --report           # 產生互動式 HTML 報告（等同預設）
    python main.py --analyze          # 執行歷史波段分析（2000年至今）
    python main.py --backtest --start 2020-01-01  # 指定回測起始日
        """
    )
    
    parser.add_argument(
        '--download', '-d',
        action='store_true',
        help='下載最新資料'
    )
    
    parser.add_argument(
        '--backtest', '-b',
        action='store_true',
        help='執行策略回測'
    )
    
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='顯示系統狀態'
    )
    
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='產生互動式 HTML 報告 (可捲動、縮放)'
    )
    
    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='執行歷史波段分析 (從 2000 年至今)'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        default='2015-01-01',
        help='回測起始日期 (預設: 2015-01-01)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='回測結束日期 (預設: 今天)'
    )
    
    args = parser.parse_args()
    
    # 印出標題
    print_banner()
    
    try:
        # 判斷是否需要下載最新資料
        needs_data = not args.status  # 除了查看狀態外，其他操作都需要最新資料
        
        if needs_data:
            # ⭐️ 重要：先下載最新的歷史指數資訊
            print("\n🔄 自動更新最新市場資料...")
            print("=" * 60)
            download_data(save=True)
            print("=" * 60)
        
        if args.status:
            show_status()
        elif args.download:
            # 已經在上面下載過了，這裡只顯示確認訊息
            print("\n✅ 資料下載完成！")
        elif args.backtest:
            run_backtest(start_date=args.start, end_date=args.end)
        elif args.report:
            generate_interactive_report()
        elif args.analyze:
            analyze_swing_history()
        else:
            # 預設：產生互動式 HTML 報告（取代 PNG 圖表）
            generate_interactive_report()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 使用者中斷程式")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
