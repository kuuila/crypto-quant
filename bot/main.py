#!/usr/bin/env python3
"""
虾3x 量化交易机器人 - 主程序
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/crypto-quant')

from core.exchange import ExchangeClient
from strategies.grid_strategy import GridStrategy
from core.monitor import Monitor, MessageTemplates
from config.settings import TRADING_PAIR, GRID_CONFIG, RISK_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/root/.openclaw/workspace/crypto-quant/logs/bot.log')
    ]
)
logger = logging.getLogger('bot')


class TradingBot:
    """交易机器人"""
    
    def __init__(self):
        self.exchange = ExchangeClient()
        self.strategy = GridStrategy(self.exchange)
        self.monitor = Monitor()
        
        self.running = False
        self.last_price: Optional[float] = None
        self.daily_pnl = 0.0
        self.start_time: Optional[datetime] = None
        
        # 统计
        self.stats = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_profit': 0.0,
            'max_drawdown': 0.0
        }
        
    async def start(self):
        """启动机器人"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("=" * 50)
        logger.info("🦐 虾3x 量化交易机器人启动")
        logger.info(f"交易对: {TRADING_PAIR}")
        logger.info(f"网格范围: {GRID_CONFIG['lower_price']} - {GRID_CONFIG['upper_price']}")
        logger.info(f"网格数量: {GRID_CONFIG['grid_count']}")
        logger.info("=" * 50)
        
        # 初始化 Telegram
        await self.monitor.init_bot()
        
        # 发送启动通知
        await self.monitor.send_message(
            f"🚀 <b>虾3x 量化机器人启动</b>\n\n"
            f"交易对: {TRADING_PAIR}\n"
            f"网格: {GRID_CONFIG['lower_price']} - {GRID_CONFIG['upper_price']}\n"
            f"网格数: {GRID_CONFIG['grid_count']}\n"
            f"投入资金: {GRID_CONFIG['investment_amount']} USDT"
        )
        
        # 主循环
        await self.main_loop()
        
    async def stop(self):
        """停止机器人"""
        self.running = False
        logger.info("机器人停止")
        
        # 发送停止通知
        await self.monitor.send_message(
            f"🛑 <b>虾3x 量化机器人停止</b>\n\n"
            f"运行时长: {datetime.now() - self.start_time}\n"
            f"总交易次数: {self.stats['total_trades']}\n"
            f"总盈亏: {self.stats['total_profit']:+.2f} USDT"
        )
        
    async def main_loop(self):
        """主循环"""
        interval = 60  # 检查间隔（秒）
        report_interval = 3600  # 状态报告间隔（秒）
        last_report = datetime.now()
        
        while self.running:
            try:
                # 1. 获取当前价格
                current_price = self.exchange.get_current_price()
                self.last_price = current_price
                
                logger.info(f"当前价格: {current_price}")
                
                # 2. 处理已成交订单
                filled = self.strategy.process_filled_orders()
                
                # 发送成交通知
                for trade in filled['filled_buys']:
                    self.stats['total_trades'] += 1
                    await self.monitor.send_message(
                        MessageTemplates.trade_filled(
                            'buy', TRADING_PAIR, 
                            trade['price'], trade['amount']
                        )
                    )
                    
                for trade in filled['filled_sells']:
                    self.stats['total_trades'] += 1
                    # 计算盈亏（简化）
                    profit = trade['price'] * trade['amount'] * 0.001  # 假设
                    self.stats['total_profit'] += profit
                    await self.monitor.send_message(
                        MessageTemplates.trade_filled(
                            'sell', TRADING_PAIR,
                            trade['price'], trade['amount'], profit
                        )
                    )
                
                # 3. 取消被套住的订单
                self.strategy.check_and_cancel_orders(current_price)
                
                # 4. 挂新订单
                if self.strategy.should_place_orders():
                    self.strategy.place_grid_orders(current_price)
                
                # 5. 检查风险
                await self.check_risk(current_price)
                
                # 6. 定时状态报告
                if (datetime.now() - last_report).seconds >= report_interval:
                    await self.send_status_report(current_price)
                    last_report = datetime.now()
                
                # 7. 等待下一轮
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"主循环异常: {e}", exc_info=True)
                await self.monitor.send_message(
                    MessageTemplates.error_alert('主循环异常', str(e))
                )
                await asyncio.sleep(30)  # 异常后等待 30 秒
                
    async def check_risk(self, current_price: float):
        """风险检查"""
        # 获取账户信息
        balance = self.exchange.fetch_balance()
        
        # 检查日亏损限制
        if self.daily_pnl < -RISK_CONFIG['daily_loss_limit']:
            await self.monitor.send_message(
                MessageTemplates.risk_alert(
                    '日亏损超限',
                    f"今日亏损: {self.daily_pnl:.2f} USDT，已达到止损线"
                )
            )
            await self.stop()
            return
            
        # 检查仓位价值
        base_asset = self.exchange.parse_symbol()['base']
        position_value = balance['total'].get(base_asset, 0) * current_price
        
        if position_value > RISK_CONFIG['max_position_value']:
            await self.monitor.send_message(
                MessageTemplates.risk_alert(
                    '仓位超限',
                    f"当前仓位价值: {position_value:.2f} USDT"
                )
            )
            
    async def send_status_report(self, current_price: float):
        """发送状态报告"""
        balance = self.exchange.fetch_balance()
        base_asset = self.exchange.parse_symbol()['base']
        
        position_value = balance['total'].get(base_asset, 0) * current_price
        open_orders = len(self.exchange.fetch_open_orders())
        
        await self.monitor.send_message(
            MessageTemplates.status_report(
                TRADING_PAIR, current_price, position_value,
                self.daily_pnl, open_orders
            )
        )


# ========== 运行脚本 ==========

def run_simulated():
    """模拟运行（不连接交易所）"""
    print("=" * 50)
    print("🦐 虾3x 量化交易机器人 - 模拟模式")
    print("=" * 50)
    
    # 模拟测试
    from config.settings import GRID_CONFIG
    
    print(f"\n📊 网格配置:")
    print(f"  交易对: {TRADING_PAIR}")
    print(f"  价格区间: {GRID_CONFIG['lower_price']} - {GRID_CONFIG['upper_price']}")
    print(f"  网格数量: {GRID_CONFIG['grid_count']}")
    print(f"  投入资金: {GRID_CONFIG['investment_amount']} USDT")
    
    # 计算网格
    grid_step = (GRID_CONFIG['upper_price'] - GRID_CONFIG['lower_price']) / (GRID_CONFIG['grid_count'] - 1)
    print(f"\n📐 网格点位:")
    for i in range(GRID_CONFIG['grid_count']):
        price = GRID_CONFIG['lower_price'] + i * grid_step
        amount = GRID_CONFIG['investment_amount'] / GRID_CONFIG['grid_count'] / price
        print(f"  层级 {i}: 价格 {price:.2f}, 数量 {amount:.6f}")
        
    print("\n✅ 模拟运行完成")
    print("⚠️  实际运行需要配置交易所 API Key")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='虾3x 量化交易机器人')
    parser.add_argument('--sim', action='store_true', help='模拟模式')
    parser.add_argument('--run', action='store_true', help='实际运行')
    args = parser.parse_args()
    
    if args.sim:
        run_simulated()
    elif args.run:
        # 实际运行需要 API Key
        bot = TradingBot()
        try:
            asyncio.run(bot.start())
        except KeyboardInterrupt:
            asyncio.run(bot.stop())
    else:
        print("用法:")
        print("  python bot/main.py --sim   # 模拟运行")
        print("  python bot/main.py --run   # 实际运行（需要 API Key）")
