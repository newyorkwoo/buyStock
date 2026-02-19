"""
GitHub Actions 專用：更新 NASDAQ 和 VIX 的 CSV 資料
下載最新資料並覆蓋 public/data/raw/ 和 data/raw/ 中的 CSV 檔案
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz
import yfinance as yf

# Project root
ROOT = Path(__file__).resolve().parent

# Output paths (both public/ for frontend and data/ for backend)
OUTPUT_DIRS = [
    ROOT / "public" / "data" / "raw",
    ROOT / "data" / "raw",
]

SYMBOLS = {
    "nasdaq_2000.csv": "^IXIC",
    "vix_2000.csv": "^VIX",
}

START_DATE = "2000-01-01"


def download_and_save():
    tw_tz = pytz.timezone("Asia/Taipei")
    tw_now = datetime.now(tw_tz)
    end_date = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"🕒 台灣時間: {tw_now.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"📅 下載範圍: {START_DATE} ~ {end_date}")

    any_updated = False

    for filename, symbol in SYMBOLS.items():
        print(f"\n📊 下載 {symbol} ...")
        try:
            df = yf.download(symbol, start=START_DATE, end=end_date, progress=False)

            if df.empty:
                print(f"   ⚠️  {symbol} 回傳空資料，跳過")
                continue

            last_date = df.index[-1].strftime("%Y-%m-%d")
            last_close = df["Close"].iloc[-1]

            # Handle MultiIndex columns from yfinance
            if isinstance(last_close, pd.Series):
                last_close = last_close.iloc[0]

            print(f"   ✅ {len(df)} 筆，最新: {last_date}，收盤: {last_close:,.2f}")

            for out_dir in OUTPUT_DIRS:
                out_dir.mkdir(parents=True, exist_ok=True)
                csv_path = out_dir / filename
                df.to_csv(csv_path)
                print(f"   💾 {csv_path}")

            any_updated = True

        except Exception as e:
            print(f"   ❌ 下載 {symbol} 失敗: {e}")

    return any_updated


if __name__ == "__main__":
    success = download_and_save()
    if not success:
        print("\n❌ 沒有任何資料更新")
        sys.exit(1)
    print("\n✅ 資料更新完成")
