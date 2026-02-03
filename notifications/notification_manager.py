"""
Notification Manager
統一管理多個通知管道
"""
from typing import List, Optional

from config import get_settings
from .base import BaseNotifier
from .line_notifier import LineNotifier
from .email_notifier import EmailNotifier


class NotificationManager:
    """
    通知管理器
    統一管理 LINE 和 Email 通知的發送
    """
    
    def __init__(self):
        """初始化通知管理器"""
        self.settings = get_settings()
        
        # 初始化各通知器
        self.notifiers: List[BaseNotifier] = []
        
        # 根據設定決定啟用哪些通知管道
        channel = self.settings.notification_channel.lower()
        
        if channel in ['line', 'both']:
            self.notifiers.append(LineNotifier())
        
        if channel in ['email', 'both']:
            self.notifiers.append(EmailNotifier())
    
    def get_configured_notifiers(self) -> List[BaseNotifier]:
        """取得已正確設定的通知器列表"""
        return [n for n in self.notifiers if n.is_configured()]
    
    def send_all(
        self,
        message: str,
        subject: Optional[str] = None
    ) -> dict:
        """
        透過所有已設定的管道發送通知
        
        Args:
            message: 通知內容
            subject: 主題
            
        Returns:
            各管道發送結果 {'LINE': True, 'Email': False, ...}
        """
        results = {}
        
        for notifier in self.get_configured_notifiers():
            results[notifier.name] = notifier.send(message, subject)
        
        if not results:
            print("⚠️ 沒有已設定的通知管道")
        
        return results
    
    def send_trading_signal(
        self,
        signal: str,
        nasdaq_price: float,
        nasdaq_change: float,
        vix_value: float,
        total_score: float,
        summary: str,
        recommendations: list = None
    ) -> dict:
        """
        發送交易信號通知到所有管道
        
        Returns:
            各管道發送結果
        """
        results = {}
        
        for notifier in self.get_configured_notifiers():
            if isinstance(notifier, LineNotifier):
                results[notifier.name] = notifier.send_trading_signal(
                    signal=signal,
                    nasdaq_price=nasdaq_price,
                    nasdaq_change=nasdaq_change,
                    vix_value=vix_value,
                    total_score=total_score,
                    summary=summary
                )
            elif isinstance(notifier, EmailNotifier):
                results[notifier.name] = notifier.send_trading_signal(
                    signal=signal,
                    nasdaq_price=nasdaq_price,
                    nasdaq_change=nasdaq_change,
                    vix_value=vix_value,
                    total_score=total_score,
                    summary=summary,
                    recommendations=recommendations
                )
            else:
                results[notifier.name] = notifier.send(
                    f"交易信號: {signal}\n評分: {total_score}\n{summary}",
                    subject="那斯達克交易信號"
                )
        
        if not results:
            print("⚠️ 沒有已設定的通知管道")
        
        return results
    
    def send_from_signal_result(self, signal_result) -> dict:
        """
        從 SignalResult 物件發送通知
        
        Args:
            signal_result: CombinedSignalGenerator.generate_signal() 的結果
            
        Returns:
            各管道發送結果
        """
        return self.send_trading_signal(
            signal=signal_result.signal.value,
            nasdaq_price=signal_result.nasdaq_price,
            nasdaq_change=signal_result.nasdaq_change,
            vix_value=signal_result.vix_value,
            total_score=signal_result.total_score,
            summary=signal_result.summary,
            recommendations=signal_result.recommendations
        )
    
    def status(self) -> dict:
        """
        取得各通知管道的設定狀態
        
        Returns:
            各管道狀態 {'LINE': {'enabled': True, 'configured': False}, ...}
        """
        status = {}
        
        # 檢查 LINE
        line_notifier = LineNotifier()
        status['LINE'] = {
            'enabled': self.settings.notification_channel.lower() in ['line', 'both'],
            'configured': line_notifier.is_configured()
        }
        
        # 檢查 Email
        email_notifier = EmailNotifier()
        status['Email'] = {
            'enabled': self.settings.notification_channel.lower() in ['email', 'both'],
            'configured': email_notifier.is_configured()
        }
        
        return status
    
    def print_status(self):
        """印出通知管道狀態"""
        print("\n📬 通知管道狀態:")
        print("-" * 40)
        
        status = self.status()
        
        for channel, info in status.items():
            enabled_emoji = "✅" if info['enabled'] else "❌"
            config_emoji = "✅" if info['configured'] else "⚠️"
            
            print(f"  {channel}:")
            print(f"    啟用: {enabled_emoji}")
            print(f"    已設定: {config_emoji}")
        
        print("-" * 40)
        
        configured = self.get_configured_notifiers()
        if configured:
            print(f"  可用管道: {', '.join(n.name for n in configured)}")
        else:
            print("  ⚠️ 目前沒有可用的通知管道")
            print("  請檢查 .env 檔案的設定")


def main():
    """測試通知管理器"""
    manager = NotificationManager()
    
    # 顯示狀態
    manager.print_status()
    
    # 如果有可用管道，發送測試通知
    if manager.get_configured_notifiers():
        print("\n發送測試通知...")
        results = manager.send_all("這是測試通知", subject="系統測試")
        
        print("\n發送結果:")
        for channel, success in results.items():
            emoji = "✅" if success else "❌"
            print(f"  {channel}: {emoji}")


if __name__ == "__main__":
    main()
