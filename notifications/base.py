"""
Base Notifier Abstract Class
通知器的抽象基底類別
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseNotifier(ABC):
    """
    通知器抽象基底類別
    所有通知管道都需要實作此介面
    """
    
    @abstractmethod
    def send(self, message: str, subject: Optional[str] = None) -> bool:
        """
        發送通知
        
        Args:
            message: 通知內容
            subject: 主題（某些管道可能用不到）
            
        Returns:
            發送是否成功
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        檢查通知器是否已正確設定
        
        Returns:
            是否已設定完成
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """通知管道名稱"""
        pass
