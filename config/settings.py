"""
Settings configuration for NASDAQ Trading Suggestion System
載入環境變數與預設設定
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class VIXThresholds:
    """VIX 恐慌指數閾值設定"""
    normal: float = 20.0        # < 20: 正常市場
    fear: float = 25.0          # 20-25: 輕度恐懼
    high_fear: float = 30.0     # 25-30: 恐懼
    extreme_fear: float = 40.0  # > 40: 極度恐慌


@dataclass
class RSIThresholds:
    """RSI 相對強弱指標閾值設定"""
    oversold: float = 30.0      # < 30: 超賣 (買入信號)
    overbought: float = 70.0    # > 70: 超買 (賣出信號)
    period: int = 14            # RSI 計算週期


@dataclass
class MASettings:
    """移動平均線設定"""
    short_period: int = 50      # 短期均線
    long_period: int = 200      # 長期均線


@dataclass
class SignalWeights:
    """多指標評分權重設定"""
    rsi: float = 0.25
    macd: float = 0.25
    ma: float = 0.25
    vix: float = 0.25


@dataclass
class Settings:
    """主設定類別"""
    # 交易標的
    nasdaq_symbol: str = "^IXIC"
    vix_symbol: str = "^VIX"
    
    # 資料期間
    start_date: str = "2015-01-01"
    
    # 指標閾值
    vix: VIXThresholds = field(default_factory=VIXThresholds)
    rsi: RSIThresholds = field(default_factory=RSIThresholds)
    ma: MASettings = field(default_factory=MASettings)
    weights: SignalWeights = field(default_factory=SignalWeights)
    
    # LINE Messaging API
    line_channel_access_token: Optional[str] = None
    line_channel_secret: Optional[str] = None
    line_user_id: Optional[str] = None
    
    # Email
    email_sender: Optional[str] = None
    email_app_password: Optional[str] = None
    email_recipient: Optional[str] = None
    
    # 通知管道
    notification_channel: str = "both"  # line, email, both, none
    
    # 排程時間
    schedule_time: str = "06:00"
    
    def __post_init__(self):
        """從環境變數載入設定"""
        # LINE 設定
        self.line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        self.line_user_id = os.getenv('LINE_USER_ID')
        
        # Email 設定
        self.email_sender = os.getenv('EMAIL_SENDER')
        self.email_app_password = os.getenv('EMAIL_APP_PASSWORD')
        self.email_recipient = os.getenv('EMAIL_RECIPIENT')
        
        # 通知管道
        self.notification_channel = os.getenv('NOTIFICATION_CHANNEL', 'both')
        
        # 排程時間
        self.schedule_time = os.getenv('SCHEDULE_TIME', '06:00')
        
        # VIX 閾值
        self.vix = VIXThresholds(
            normal=float(os.getenv('VIX_NORMAL_THRESHOLD', 20)),
            fear=float(os.getenv('VIX_FEAR_THRESHOLD', 25)),
            high_fear=float(os.getenv('VIX_HIGH_FEAR_THRESHOLD', 30)),
            extreme_fear=float(os.getenv('VIX_EXTREME_FEAR_THRESHOLD', 40)),
        )
        
        # RSI 閾值
        self.rsi = RSIThresholds(
            oversold=float(os.getenv('RSI_OVERSOLD', 30)),
            overbought=float(os.getenv('RSI_OVERBOUGHT', 70)),
        )
        
        # MA 設定
        self.ma = MASettings(
            short_period=int(os.getenv('MA_SHORT_PERIOD', 50)),
            long_period=int(os.getenv('MA_LONG_PERIOD', 200)),
        )
    
    @property
    def line_enabled(self) -> bool:
        """檢查 LINE 通知是否已設定"""
        return all([
            self.line_channel_access_token,
            self.line_user_id
        ])
    
    @property
    def email_enabled(self) -> bool:
        """檢查 Email 通知是否已設定"""
        return all([
            self.email_sender,
            self.email_app_password,
            self.email_recipient
        ])


# 全域設定實例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """取得全域設定實例 (Singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
