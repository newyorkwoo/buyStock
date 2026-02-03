"""
Email Notifier
使用 SMTP (Gmail) 發送 Email 通知
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import get_settings
from .base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """
    Email 通知器 (Gmail SMTP)
    
    設定步驟：
    1. 啟用 Google 帳戶的兩步驟驗證
    2. 到 Google 帳戶 → 安全性 → 應用程式密碼
    3. 建立一組應用程式密碼
    4. 在 .env 設定 EMAIL_SENDER、EMAIL_APP_PASSWORD、EMAIL_RECIPIENT
    """
    
    def __init__(
        self,
        sender_email: Optional[str] = None,
        app_password: Optional[str] = None,
        recipient_email: Optional[str] = None
    ):
        """
        初始化 Email 通知器
        
        Args:
            sender_email: 寄件者 Email (Gmail)
            app_password: Gmail 應用程式密碼
            recipient_email: 收件者 Email
        """
        settings = get_settings()
        
        self.sender_email = sender_email or settings.email_sender
        self.app_password = app_password or settings.email_app_password
        self.recipient_email = recipient_email or settings.email_recipient
        
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465  # SSL port
    
    @property
    def name(self) -> str:
        return "Email"
    
    def is_configured(self) -> bool:
        """檢查 Email 是否已設定"""
        return bool(
            self.sender_email and 
            self.app_password and 
            self.recipient_email
        )
    
    def send(self, message: str, subject: Optional[str] = None) -> bool:
        """
        發送 Email 通知
        
        Args:
            message: 通知內容
            subject: 郵件主題
            
        Returns:
            發送是否成功
        """
        if not self.is_configured():
            print("❌ Email 通知未設定，請檢查 .env 檔案")
            return False
        
        try:
            # 建立郵件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject or "那斯達克買賣建議通知"
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            
            # 純文字版本
            msg.attach(MIMEText(message, "plain", "utf-8"))
            
            # HTML 版本
            html_message = self._convert_to_html(message, subject)
            msg.attach(MIMEText(html_message, "html", "utf-8"))
            
            # 建立 SSL 連線並發送
            context = ssl.create_default_context()
            
            with smtplib.SMTP_SSL(
                self.smtp_server, 
                self.smtp_port, 
                context=context
            ) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(
                    self.sender_email,
                    self.recipient_email,
                    msg.as_string()
                )
            
            print(f"✅ Email 通知發送成功 → {self.recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("❌ Email 驗證失敗，請檢查 Email 和應用程式密碼")
            return False
        except Exception as e:
            print(f"❌ Email 通知發送失敗: {e}")
            return False
    
    def _convert_to_html(self, message: str, subject: Optional[str] = None) -> str:
        """將純文字訊息轉換為 HTML 格式"""
        
        # 處理換行
        html_content = message.replace("\n", "<br>")
        
        # 處理表情符號（保持原樣）
        
        # 組合 HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .content {{
            background: #f9f9f9;
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 10px 10px;
        }}
        .signal-buy {{
            color: #28a745;
            font-weight: bold;
        }}
        .signal-sell {{
            color: #dc3545;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>{subject or '那斯達克買賣建議'}</h2>
    </div>
    <div class="content">
        {html_content}
    </div>
    <div class="footer">
        <p>此郵件由那斯達克買賣建議系統自動發送</p>
        <p>⚠️ 以上僅供參考，投資請自行判斷風險</p>
    </div>
</body>
</html>
        """
        
        return html
    
    def send_trading_signal(
        self,
        signal: str,
        nasdaq_price: float,
        nasdaq_change: float,
        vix_value: float,
        total_score: float,
        summary: str,
        recommendations: list = None
    ) -> bool:
        """
        發送交易信號通知
        
        Args:
            signal: 交易信號
            nasdaq_price: 那斯達克指數
            nasdaq_change: 日變化百分比
            vix_value: VIX 值
            total_score: 綜合評分
            summary: 摘要說明
            recommendations: 操作建議列表
            
        Returns:
            發送是否成功
        """
        signal_emoji = {
            "STRONG_BUY": "🚀🚀 強烈買入",
            "BUY": "📈 買入",
            "HOLD": "⏸️ 持有",
            "SELL": "📉 賣出",
            "STRONG_SELL": "🔻🔻 強烈賣出"
        }
        
        signal_text = signal_emoji.get(signal, signal)
        
        # 建立訊息內容
        lines = [
            f"📊 綜合建議: {signal_text}",
            f"📈 綜合評分: {total_score:.2f}",
            "",
            "━━━ 市場概況 ━━━",
            f"那斯達克指數: {nasdaq_price:,.2f} ({nasdaq_change:+.2f}%)",
            f"VIX 恐慌指數: {vix_value:.2f}",
            "",
            "━━━ 分析摘要 ━━━",
            summary,
        ]
        
        if recommendations:
            lines.append("")
            lines.append("━━━ 操作建議 ━━━")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        lines.append("")
        lines.append("⚠️ 此為技術分析參考，投資請自行判斷風險")
        
        message = "\n".join(lines)
        
        # 設定郵件主題
        subject = f"【{signal_text}】那斯達克交易信號 - {nasdaq_price:,.0f}"
        
        return self.send(message, subject=subject)


def main():
    """測試 Email 通知"""
    notifier = EmailNotifier()
    
    if not notifier.is_configured():
        print("Email 通知未設定")
        print("請在 .env 檔案中設定：")
        print("  EMAIL_SENDER=your-email@gmail.com")
        print("  EMAIL_APP_PASSWORD=your-app-password")
        print("  EMAIL_RECIPIENT=recipient@example.com")
        return
    
    # 測試發送
    success = notifier.send("這是測試訊息\n\n第二行\n第三行", subject="測試郵件")
    print(f"發送結果: {'成功' if success else '失敗'}")


if __name__ == "__main__":
    main()
