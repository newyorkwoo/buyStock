"""
Scheduler Module
定時執行買賣建議分析並發送通知

可使用兩種方式執行：
1. 獨立執行: python scheduler.py
2. 作為 cron job 或 systemd service
"""
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 將專案根目錄加入 Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from data import DataFetcher
from indicators import CombinedSignalGenerator
from notifications import NotificationManager

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def run_analysis_job():
    """
    執行分析任務
    
    1. 下載最新資料
    2. 產生交易信號
    3. 發送通知
    """
    logger.info("=" * 50)
    logger.info("開始執行分析任務")
    logger.info("=" * 50)
    
    try:
        # 下載資料
        logger.info("下載最新資料...")
        fetcher = DataFetcher()
        nasdaq_data, vix_data = fetcher.fetch_all(save_csv=True)
        
        # 產生信號
        logger.info("分析市場狀況...")
        generator = CombinedSignalGenerator()
        result = generator.generate_signal(nasdaq_data, vix_data)
        
        logger.info(f"分析結果: {result.signal.value} (Score: {result.total_score:.2f})")
        logger.info(f"那斯達克: {result.nasdaq_price:,.2f} ({result.nasdaq_change:+.2f}%)")
        logger.info(f"VIX: {result.vix_value:.2f}")
        
        # 發送通知
        logger.info("發送通知...")
        manager = NotificationManager()
        
        if manager.get_configured_notifiers():
            notification_results = manager.send_from_signal_result(result)
            
            for channel, success in notification_results.items():
                status = "成功" if success else "失敗"
                logger.info(f"  {channel}: {status}")
        else:
            logger.warning("沒有可用的通知管道，跳過通知")
        
        logger.info("分析任務完成")
        return result
        
    except Exception as e:
        logger.error(f"分析任務失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_scheduler_with_schedule():
    """
    使用 schedule 套件執行定時任務
    """
    try:
        import schedule
    except ImportError:
        logger.error("請先安裝 schedule 套件: pip install schedule")
        return
    
    settings = get_settings()
    schedule_time = settings.schedule_time  # 例如 "06:00"
    
    logger.info(f"排程器啟動，每日 {schedule_time} 執行分析")
    logger.info("按 Ctrl+C 停止")
    
    # 設定每日任務
    schedule.every().day.at(schedule_time).do(run_analysis_job)
    
    # 也可以設定每小時或每分鐘測試
    # schedule.every().hour.do(run_analysis_job)
    # schedule.every(30).minutes.do(run_analysis_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次


def run_scheduler_with_apscheduler():
    """
    使用 APScheduler 執行定時任務 (更強大的排程器)
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("請先安裝 APScheduler 套件: pip install APScheduler")
        return
    
    settings = get_settings()
    hour, minute = map(int, settings.schedule_time.split(':'))
    
    scheduler = BlockingScheduler()
    
    # 設定每日任務 (美股收盤後，台灣時間早上)
    scheduler.add_job(
        run_analysis_job,
        CronTrigger(hour=hour, minute=minute),
        id='daily_analysis',
        name='每日那斯達克分析',
        replace_existing=True
    )
    
    logger.info(f"APScheduler 啟動，每日 {hour:02d}:{minute:02d} 執行分析")
    logger.info("按 Ctrl+C 停止")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("排程器停止")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="那斯達克買賣建議系統 - 排程器")
    
    parser.add_argument(
        '--run-now',
        action='store_true',
        help='立即執行一次分析'
    )
    
    parser.add_argument(
        '--scheduler',
        choices=['schedule', 'apscheduler'],
        default='schedule',
        help='使用的排程套件 (預設: schedule)'
    )
    
    args = parser.parse_args()
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           📅 那斯達克買賣建議系統 - 排程器                      ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    if args.run_now:
        # 立即執行
        run_analysis_job()
    else:
        # 啟動排程器
        if args.scheduler == 'apscheduler':
            run_scheduler_with_apscheduler()
        else:
            run_scheduler_with_schedule()


if __name__ == "__main__":
    main()
