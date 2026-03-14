"""
监控模块 - 发送 Telegram 通知
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from telegram import Bot
from config.settings import MONITOR_CONFIG

logger = logging.getLogger(__name__)


class Monitor:
    """监控通知"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or MONITOR_CONFIG['telegram_token']
        self.chat_id = chat_id or MONITOR_CONFIG['telegram_chat_id']
        self.bot: Optional[Bot] = None
        
    async def init_bot(self):
        """初始化 Bot"""
        if self.token:
            self.bot = Bot(token=self.token)
            
    async def send_message(self, text: str, parse_mode='HTML'):
        """发送消息"""
        if not self.bot:
            logger.warning("Telegram Bot 未配置，跳过发送消息")
            return
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f"消息已发送: {text[:50]}...")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            
    def send_sync(self, text: str):
        """同步发送消息"""
        asyncio.run(self._send_async(text))
        
    async def _send_async(self, text: str):
        """异步发送"""
        await self.init_bot()
        await self.send_message(text)


# 消息模板
class MessageTemplates:
    """消息模板"""
    
    @staticmethod
    def trade_filled(side: str, symbol: str, price: float, amount: float, profit: float = None):
        """成交通知"""
        emoji = "🟢" if side == 'buy' else "🔴"
        msg = f"{emoji} <b>订单成交</b>\n\n"
        msg += f"交易对: {symbol}\n"
        msg += f"方向: {'买入' if side == 'buy' else '卖出'}\n"
        msg += f"价格: {price:.2f}\n"
        msg += f"数量: {amount:.6f}\n"
        if profit:
            emoji_p = "💰" if profit > 0 else "📉"
            msg += f"{emoji_p} 盈亏: {profit:+.2f} USDT\n"
        msg += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg
        
    @staticmethod
    def status_report(symbol: str, current_price: float, position_value: float, 
                      daily_pnl: float, open_orders: int):
        """状态报告"""
        msg = "📊 <b>状态报告</b>\n\n"
        msg += f"交易对: {symbol}\n"
        msg += f"当前价: {current_price:.2f}\n"
        msg += f"仓位值: {position_value:.2f} USDT\n"
        msg += f"今日盈亏: {daily_pnl:+.2f} USDT\n"
        msg += f"挂单数: {open_orders}\n"
        msg += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg
        
    @staticmethod
    def risk_alert(alert_type: str, message: str):
        """风险告警"""
        msg = "⚠️ <b>风险告警</b>\n\n"
        msg += f"类型: {alert_type}\n"
        msg += f"详情: {message}\n"
        msg += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg
        
    @staticmethod
    def error_alert(error_type: str, error_msg: str):
        """错误告警"""
        msg = "🚨 <b>错误告警</b>\n\n"
        msg += f"类型: {error_type}\n"
        msg += f"错误: {error_msg}\n"
        msg += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return msg


if __name__ == '__main__':
    # 测试
    monitor = Monitor()
    
    # 测试消息模板
    msg = MessageTemplates.trade_filled('buy', 'BTC/USDT', 70000, 0.01)
    print(msg)
