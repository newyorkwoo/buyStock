"""
Data Fetcher Module
使用 yfinance 下載那斯達克綜合指數 (^IXIC) 與 VIX 恐慌指數 (^VIX) 歷史資料
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import pytz

import pandas as pd
import yfinance as yf

from config import get_settings


class DataFetcher:
    """
    資料下載器
    負責從 Yahoo Finance 下載那斯達克指數與 VIX 的歷史資料
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化資料下載器
        
        Args:
            data_dir: 資料儲存目錄，預設為 data/raw/
        """
        self.settings = get_settings()
        
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "raw"
        else:
            self.data_dir = Path(data_dir)
        
        # 確保資料目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_nasdaq(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_csv: bool = True
    ) -> pd.DataFrame:
        """
        下載那斯達克綜合指數歷史資料
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)，預設為 2015-01-01
            end_date: 結束日期，預設為今天
            save_csv: 是否儲存為 CSV 檔案
            
        Returns:
            DataFrame 包含 OHLCV 資料
        """
        if start_date is None:
            start_date = self.settings.start_date
        if end_date is None:
            # 使用台灣時區並加一天，確保下載到最新資料
            tw_tz = pytz.timezone('Asia/Taipei')
            tw_now = datetime.now(tw_tz)
            end_date = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"📊 下載那斯達克指數 ({self.settings.nasdaq_symbol})...")
        print(f"   期間: {start_date} ~ {end_date}")
        
        try:
            data = yf.download(
                self.settings.nasdaq_symbol,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            if data.empty:
                raise ValueError("無法取得那斯達克指數資料")
            
            # 處理多層索引（如果存在）
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
            # 重新命名欄位
            data.index.name = 'Date'
            
            print(f"   ✅ 成功下載 {len(data)} 筆資料")
            print(f"   最新日期: {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"   最新收盤價: {data['Close'].iloc[-1]:,.2f}")
            
            # 顯示時區資訊
            us_et = pytz.timezone('US/Eastern')
            us_now = datetime.now(us_et)
            print(f"   🕒 美東時間: {us_now.strftime('%Y-%m-%d %H:%M %Z')} (美股交易時間 09:30-16:00)")
            
            if save_csv:
                csv_path = self.data_dir / "nasdaq_historical.csv"
                data.to_csv(csv_path)
                print(f"   💾 已儲存至: {csv_path}")
            
            return data
            
        except Exception as e:
            print(f"   ❌ 下載失敗: {e}")
            raise
    
    def fetch_vix(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_csv: bool = True
    ) -> pd.DataFrame:
        """
        下載 VIX 恐慌指數歷史資料
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)，預設為 2015-01-01
            end_date: 結束日期，預設為今天
            save_csv: 是否儲存為 CSV 檔案
            
        Returns:
            DataFrame 包含 VIX 資料
        """
        if start_date is None:
            start_date = self.settings.start_date
        if end_date is None:
            # 使用台灣時區並加一天，確保下載到最新資料
            tw_tz = pytz.timezone('Asia/Taipei')
            tw_now = datetime.now(tw_tz)
            end_date = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"\n😰 下載 VIX 恐慌指數 ({self.settings.vix_symbol})...")
        print(f"   期間: {start_date} ~ {end_date}")
        
        try:
            data = yf.download(
                self.settings.vix_symbol,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            if data.empty:
                raise ValueError("無法取得 VIX 資料")
            
            # 處理多層索引（如果存在）
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
            data.index.name = 'Date'
            
            print(f"   ✅ 成功下載 {len(data)} 筆資料")
            print(f"   最新日期: {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"   最新 VIX: {data['Close'].iloc[-1]:.2f}")
            
            # VIX 情緒判讀
            vix_value = data['Close'].iloc[-1]
            sentiment = self._get_vix_sentiment(vix_value)
            print(f"   市場情緒: {sentiment}")
            
            if save_csv:
                csv_path = self.data_dir / "vix_historical.csv"
                data.to_csv(csv_path)
                print(f"   💾 已儲存至: {csv_path}")
            
            return data
            
        except Exception as e:
            print(f"   ❌ 下載失敗: {e}")
            raise
    
    def fetch_all(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_csv: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        下載所有資料 (NASDAQ + VIX)
        
        Returns:
            Tuple of (nasdaq_data, vix_data)
        """
        nasdaq_data = self.fetch_nasdaq(start_date, end_date, save_csv)
        vix_data = self.fetch_vix(start_date, end_date, save_csv)
        
        return nasdaq_data, vix_data
    
    def load_nasdaq(self) -> pd.DataFrame:
        """從 CSV 載入那斯達克資料"""
        csv_path = self.data_dir / "nasdaq_historical.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到資料檔案: {csv_path}")
        
        data = pd.read_csv(csv_path, index_col='Date', parse_dates=True)
        return data
    
    def load_vix(self) -> pd.DataFrame:
        """從 CSV 載入 VIX 資料"""
        csv_path = self.data_dir / "vix_historical.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到資料檔案: {csv_path}")
        
        data = pd.read_csv(csv_path, index_col='Date', parse_dates=True)
        return data
    
    def get_merged_data(
        self,
        nasdaq_data: Optional[pd.DataFrame] = None,
        vix_data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        合併 NASDAQ 與 VIX 資料
        
        Returns:
            合併後的 DataFrame，VIX 欄位以 'VIX_' 前綴區分
        """
        if nasdaq_data is None:
            nasdaq_data = self.load_nasdaq()
        if vix_data is None:
            vix_data = self.load_vix()
        
        # 重新命名 VIX 欄位
        vix_renamed = vix_data.add_prefix('VIX_')
        
        # 合併資料 (以日期為索引)
        merged = nasdaq_data.join(vix_renamed, how='inner')
        
        return merged
    
    def _get_vix_sentiment(self, vix_value: float) -> str:
        """根據 VIX 值判斷市場情緒"""
        thresholds = self.settings.vix
        
        if vix_value < 12:
            return "😎 極度樂觀 (Extreme Complacency)"
        elif vix_value < thresholds.normal:
            return "😊 正常 (Normal)"
        elif vix_value < thresholds.fear:
            return "😐 輕度恐懼 (Mild Fear)"
        elif vix_value < thresholds.high_fear:
            return "😟 恐懼 (Fear)"
        elif vix_value < thresholds.extreme_fear:
            return "😨 高度恐懼 (High Fear)"
        else:
            return "😱 極度恐慌 (Extreme Panic)"


def main():
    """測試資料下載功能"""
    fetcher = DataFetcher()
    
    print("=" * 60)
    print("那斯達克買賣建議系統 - 資料下載")
    print("=" * 60)
    
    nasdaq_data, vix_data = fetcher.fetch_all()
    
    print("\n" + "=" * 60)
    print("資料摘要")
    print("=" * 60)
    print(f"\n那斯達克指數最近 5 日:")
    print(nasdaq_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail())
    
    print(f"\nVIX 恐慌指數最近 5 日:")
    print(vix_data[['Open', 'High', 'Low', 'Close']].tail())


if __name__ == "__main__":
    main()
