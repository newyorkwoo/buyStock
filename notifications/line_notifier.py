"""
LINE Messaging API Notifier
使用 LINE Messaging API 發送通知（LINE Notify 已於 2025/03 停用）
"""
from typing import Optional

from config import get_settings
from .base import BaseNotifier


class LineNotifier(BaseNotifier):
    """
    LINE Messaging API 通知器
    
    設定步驟：
    1. 到 https://developers.line.biz/console/ 建立 Messaging API Channel
    2. 取得 Channel Access Token
    3. 取得目標用戶的 LINE User ID（透過 Webhook 取得）
    4. 在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_USER_ID
    """
    
    def __init__(
        self,
        channel_access_token: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        初始化 LINE 通知器
        
        Args:
            channel_access_token: LINE Channel Access Token
            user_id: 目標用戶的 LINE User ID
        """
        settings = get_settings()
        
        self.channel_access_token = channel_access_token or settings.line_channel_access_token
        self.user_id = user_id or settings.line_user_id
        
        self._api_client = None
    
    @property
    def name(self) -> str:
        return "LINE"
    
    def is_configured(self) -> bool:
        """檢查 LINE 是否已設定"""
        return bool(self.channel_access_token and self.user_id)
    
    def _get_api_client(self):
        """取得或建立 LINE API Client（延遲載入）"""
        if self._api_client is None:
            try:
                from linebot.v3.messaging import (
                    Configuration,
                    ApiClient,
                    MessagingApi,
                )
                
                configuration = Configuration(access_token=self.channel_access_token)
                api_client = ApiClient(configuration)
                self._api_client = MessagingApi(api_client)
            except ImportError:
                print("⚠️ LINE Bot SDK 未安裝，請執行: pip install line-bot-sdk")
                return None
            except Exception as e:
                print(f"⚠️ LINE API 初始化失敗: {e}")
                return None
        
        return self._api_client
    
    def send(self, message: str, subject: Optional[str] = None) -> bool:
        """
        發送 LINE 通知
        
        Args:
            message: 通知內容
            subject: 主題（會加在訊息開頭）
            
        Returns:
            發送是否成功
        """
        if not self.is_configured():
            print("❌ LINE 通知未設定，請檢查 .env 檔案")
            return False
        
        try:
            from linebot.v3.messaging import (
                PushMessageRequest,
                TextMessage,
            )
            
            api = self._get_api_client()
            if api is None:
                return False
            
            # 組合訊息
            full_message = message
            if subject:
                full_message = f"【{subject}】\n\n{message}"
            
            # LINE 訊息長度限制為 5000 字元
            if len(full_message) > 5000:
                full_message = full_message[:4997] + "..."
            
            # 發送訊息
            api.push_message(
                PushMessageRequest(
                    to=self.user_id,
                    messages=[TextMessage(text=full_message)]
                )
            )
            
            print(f"✅ LINE 通知發送成功")
            return True
            
        except Exception as e:
            print(f"❌ LINE 通知發送失敗: {e}")
            return False
    
    def send_trading_signal(
        self,
        signal: str,
        nasdaq_price: float,
        nasdaq_change: float,
        vix_value: float,
        total_score: float,
        summary: str
    ) -> bool:
        """
        發送交易信號通知
        
        Args:
            signal: 交易信號 (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
            nasdaq_price: 那斯達克指數
            nasdaq_change: 日變化百分比
            vix_value: VIX 值
            total_score: 綜合評分
            summary: 摘要說明
            
        Returns:
            發送是否成功
        """
        signal_emoji = {
            "STRONG_BUY": "🚀🚀",
            "BUY": "📈",
            "HOLD": "⏸️",
            "SELL": "📉",
            "STRONG_SELL": "🔻🔻"
        }
        
        emoji = signal_emoji.get(signal, "📊")
        
        message = f"""
{emoji} 那斯達克買賣建議 {emoji}

📊 綜合建議: {signal}
📈 綜合評分: {total_score:.2f}

--- 市場概況 ---
那斯達克: {nasdaq_price:,.2f} ({nasdaq_change:+.2f}%)
VIX 恐慌指數: {vix_value:.2f}

--- 建議摘要 ---
{summary}

⚠️ 此為技術分析參考，投資請自行判斷
        """.strip()
        
        return self.send(message, subject="那斯達克交易信號")


def main():
    """測試 LINE 通知"""
    notifier = LineNotifier()
    
    if not notifier.is_configured():
        print("LINE 通知未設定")
        print("請在 .env 檔案中設定：")
        print("  LINE_CHANNEL_ACCESS_TOKEN=xxx")
        print("  LINE_USER_ID=xxx")
        return
    
    # 測試發送
    success = notifier.send("這是測試訊息", subject="測試")
    print(f"發送結果: {'成功' if success else '失敗'}")


if __name__ == "__main__":
    main()
