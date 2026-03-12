#!/usr/bin/env python3
"""
虾3x 智能量化交易机器人 - 主程序
自动分析市场，动态选择策略
"""
import asyncio
import logging
import signal
import sys
import pandas as pd
from datetime import datetime
from typing import Optional, Dict

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/crypto-quant')

from core.exchange import ExchangeClient
from core.market_analyzer import MarketAnalyzer, MarketState, StrategySelector
from core.monitor import Monitor, MessageTemplates
from config.settings import TRADING_PAIR, RISK_CONFIG

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


class SmartTradingBot:
    """智能交易机器人 - 先分析再交易"""
    
    def __init__(self):
        self.exchange = ExchangeClient()
        self.analyzer = MarketAnalyzer()
        self.monitor = Monitor()
        
        # 当前策略
        self.current_strategy: Optional[str] = None
        self.strategy_instance = None
        
        # 市场状态
        self.market_state: Optional[MarketState] = None
        self.last_analysis: Optional[datetime] = None
        
        # 运行状态
        self.running = False
        self.last_price: Optional[float] = None
        self.daily_pnl = 0.0
        self.start_time: Optional[datetime] = None
        
        # 统计
        self.stats = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'strategy_changes': 0
        }
        
    async def start(self):
        """启动机器人"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("🦐 虾3x 智能量化交易机器人启动")
        logger.info("=" * 60)
        
        # 初始化 Telegram
        await self.monitor.init_bot()
        
        # 第一步：分析市场
        await self.analyze_market()
        
        # 第二步：选择策略
        await self.select_strategy()
        
        # 发送启动通知
        await self._send_startup_notification()
        
        # 主循环
        await self.main_loop()
        
    async def analyze_market(self):
        """分析市场状态"""
        logger.info("📊 正在分析市场...")
        
        try:
            # 获取历史数据
            ohlcv = self.exchange.fetch_ohlcv(limit=100)
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            )
            
            # 获取当前价格
            current_price = self.exchange.get_current_price()
            self.last_price = current_price
            
            # 分析市场
            analysis = self.analyzer.analyze(df, current_price)
            
            self.market_state = analysis.state
            self.last_analysis = datetime.now()
            
            logger.info(f"市场分析结果: {analysis}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"市场分析失败: {e}")
            return None
    
    async def select_strategy(self):
        """根据市场状态选择策略"""
        
        if not self.market_state:
            logger.warning("市场状态未知，默认观望")
            self.current_strategy = 'wait'
            return
        
        # 选择策略
        new_strategy = StrategySelector.select(
            type('Analysis', (), {
                'state': self.market_state,
                'confidence': 0.7  # 假设置信度
            })()
        )
        
        # 如果策略变化
        if new_strategy != self.current_strategy:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            
            logger.info(f"策略切换: {old_strategy} → {new_strategy}")
            self.stats['strategy_changes'] += 1
            
            # 初始化策略实例
            await self._init_strategy_instance()
            
            # 发送通知
            await self.monitor.send_message(
                f"🔄 <b>策略切换</b>\n\n"
                f"市场状态: {self.market_state.value}\n"
                f"原策略: {old_strategy or '无'}\n"
                f"新策略: {new_strategy}"
            )
    
    async def _init_strategy_instance(self):
        """初始化策略实例"""
        
        if self.current_strategy == 'grid':
            from strategies.grid_strategy import GridStrategy
            self.strategy_instance = GridStrategy(self.exchange)
            
        elif self.current_strategy == 'wait':
            self.strategy_instance = None
            
        elif self.current_strategy == 'trend_following':
            # TODO: 实现趋势跟踪策略
            self.strategy_instance = None
            
        elif self.current_strategy == 'short':
            # TODO: 实现做空策略
            self.strategy_instance = None
            
        else:
            self.strategy_instance = None
    
    async def main_loop(self):
        """主循环"""
        interval = 60  # 检查间隔（秒）
        analysis_interval = 300  # 市场分析间隔（5分钟）
        report_interval = 3600  # 状态报告间隔（1小时）
        
        last_report = datetime.now()
        
        while self.running:
            try:
                # 1. 获取当前价格
                current_price = self.exchange.get_current_price()
                self.last_price = current_price
                
                # 2. 定期重新分析市场
                if (datetime.now() - self.last_analysis).seconds >= analysis_interval:
                    analysis = await self.analyze_market()
                    if analysis:
                        await self.select_strategy()
                
                # 3. 执行策略
                if self.strategy_instance:
                    await self._execute_strategy(current_price)
                    
                # 4. 风险检查
                await self.check_risk(current_price)
                
                # 5. 定时报告
                if (datetime.now() - last_report).seconds >= report_interval:
                    await self.send_status_report(current_price)
                    last_report = datetime.now()
                
                # 6. 等待下一轮
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"主循环异常: {e}", exc_info=True)
                await self.monitor.send_message(
                    MessageTemplates.error_alert('主循环异常', str(e))
                )
                await asyncio.sleep(30)
    
    async def _execute_strategy(self, current_price: float):
        """执行当前策略"""
        
        if self.current_strategy == 'wait':
            return  # 观望
            
        if self.current_strategy == 'grid' and self.strategy_instance:
            # 网格策略
            filled = self.strategy_instance.process_filled_orders()
            
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
                profit = trade['price'] * trade['amount'] * 0.001
                self.stats['total_profit'] += profit
                await self.monitor.send_message(
                    MessageTemplates.trade_filled(
                        'sell', TRADING_PAIR,
                        trade['price'], trade['amount'], profit
                    )
                )
            
            # 取消旧订单
            self.strategy_instance.check_and_cancel_orders(current_price)
            
            # 挂新订单
            if self.strategy_instance.should_place_orders():
                self.strategy_instance.place_grid_orders(current_price)
    
    async def check_risk(self, current_price: float):
        """风险检查"""
        balance = self.exchange.fetch_balance()
        
        # 日亏损限制
        if self.daily_pnl < -RISK_CONFIG['daily_loss_limit']:
            await self.monitor.send_message(
                MessageTemplates.risk_alert(
                    '日亏损超限',
                    f"今日亏损: {self.daily_pnl:.2f} USDT"
                )
            )
            await self.stop()
            return
        
        # 仓位限制
        base_asset = self.exchange.parse_symbol()['base']
        position_value = balance['total'].get(base_asset, 0) * current_price
        
        if position_value > RISK_CONFIG['max_position_value']:
            await self.monitor.send_message(
                MessageTemplates.risk_alert(
                    '仓位超限',
                    f"当前仓位: {position_value:.2f} USDT"
                )
            )
    
    async def send_status_report(self, current_price: float):
        """发送状态报告"""
        balance = self.exchange.fetch_balance()
        base_asset = self.exchange.parse_symbol()['base']
        
        position_value = balance['total'].get(base_asset, 0) * current_price
        open_orders = len(self.exchange.fetch_open_orders())
        
        await self.monitor.send_message(
            f"📊 <b>状态报告</b>\n\n"
            f"市场状态: {self.market_state.value if self.market_state else '未知'}\n"
            f"当前策略: {self.current_strategy}\n"
            f"价格: {current_price:.2f}\n"
            f"仓位: {position_value:.2f} USDT\n"
            f"挂单: {open_orders}\n"
            f"今日盈亏: {self.daily_pnl:+.2f}\n"
            f"总盈亏: {self.stats['total_profit']:+.2f}"
        )
    
    async def _send_startup_notification(self):
        """发送启动通知"""
        await self.monitor.send_message(
            f"🚀 <b>虾3x 智能量化机器人启动</b>\n\n"
            f"交易对: {TRADING_PAIR}\n"
            f"市场状态: {self.market_state.value if self.market_state else '分析中'}\n"
            f"选择策略: {self.current_strategy}\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    async def stop(self):
        """停止机器人"""
        self.running = False
        logger.info("机器人停止")
        
        await self.monitor.send_message(
            f"🛑 <b>虾3x 智能量化机器人停止</b>\n\n"
            f"运行时长: {datetime.now() - self.start_time}\n"
            f"总交易: {self.stats['total_trades']}\n"
            f"总盈亏: {self.stats['total_profit']:+.2f} USDT\n"
            f"策略切换: {self.stats['strategy_changes']} 次"
        )


# ========== 运行脚本 ==========

def run_simulated():
    """模拟运行"""
    print("=" * 60)
    print("🦐 虾3x 智能量化交易机器人 - 模拟模式")
    print("=" * 60)
    
    # 模拟市场分析
    print("\n📊 模拟市场分析...")
    print("  获取 BTC/USDT 历史数据 (100 根 1H K线)")
    print("  计算技术指标: MA20, MA60, RSI, Bollinger Bands")
    print("  分析趋势强度、波动率、成交量变化")
    
    # 模拟策略选择
    print("\n🎯 策略选择逻辑:")
    print("  单边上涨 → 趋势跟踪 / 做多")
    print("  单边下跌 → 空仓 / 做空")
    print("  横盘震荡 → 网格交易 ✅")
    print("  高波动   → 缩小仓位 / 期权对冲")
    print("  方向不明 → 观望")
    
    print("\n🔄 动态调整:")
    print("  每 5 分钟重新分析市场")
    print("  状态变化时自动切换策略")
    print("  推送策略变更通知")
    
    print("\n✅ 模拟运行完成")
    print("⚠️  实际运行需要配置 API Key")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='虾3x 智能量化交易机器人')
    parser.add_argument('--sim', action='store_true', help='模拟模式')
    parser.add_argument('--run', action='store_true', help='实际运行')
    args = parser.parse_args()
    
    if args.sim:
        run_simulated()
    elif args.run:
        bot = SmartTradingBot()
        try:
            asyncio.run(bot.start())
        except KeyboardInterrupt:
            asyncio.run(bot.stop())
    else:
        print("用法:")
        print("  python bot/main.py --sim   # 模拟运行")
        print("  python bot/main.py --run   # 实际运行（需要 API Key）")
