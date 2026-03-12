#!/usr/bin/env python3
"""
虾3x 智能量化系统 - 三层架构
Layer 1: 预判 → Layer 2: 监控 → Layer 3: 执行
"""
import asyncio
import logging
import sys
import pandas as pd
from datetime import datetime
from typing import Optional

sys.path.insert(0, '/root/.openclaw/workspace/crypto-quant')

from core.exchange import ExchangeClient
from core.data_fetcher import ExternalDataFetcher
from core.monitor_layer import MarketMonitor, Signal
from core.market_analyzer import MarketAnalyzer, StrategySelector
from core.monitor import Monitor, MessageTemplates
from config.settings import TRADING_PAIR, RISK_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')


class QuantSystem:
    """量化交易系统 - 三层架构"""
    
    def __init__(self):
        # 初始化各层
        self.exchange = ExchangeClient()
        self.fetcher = ExternalDataFetcher()
        self.analyzer = MarketAnalyzer()
        self.monitor = MarketMonitor(self.exchange, self.fetcher)
        self.telegram = Monitor()
        
        # 状态
        self.current_strategy = 'wait'
        self.strategy_instance = None
        self.running = False
        
        # 统计
        self.stats = {
            'signals_caught': 0,
            'trades': 0,
            'profit': 0.0
        }
        
    async def start(self):
        """启动系统"""
        self.running = True
        
        print("=" * 60)
        print("🦐 虾3x 智能量化系统启动")
        print("=" * 60)
        
        # Layer 1: 预判
        await self.layer1_prediction()
        
        # Layer 2: 监控
        self.monitor.setup_default_rules()
        self.monitor.on_signal = self.on_market_signal
        
        # 启动监控循环
        asyncio.create_task(self.monitor.run_loop(interval=60))
        
        # Layer 3: 执行
        await self.layer3_execution()
        
    async def layer1_prediction(self):
        """Layer 1: 生成预判报告"""
        logger.info("📊 Layer 1: 生成市场预判报告...")
        
        # 1. 获取技术分析数据
        ohlcv = self.exchange.fetch_ohlcv(limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        current_price = self.exchange.get_current_price()
        
        # 2. 技术指标分析
        tech_analysis = self.analyzer.analyze(df, current_price)
        
        # 3. 外部数据
        market_report = self.fetcher.generate_market_report('BTCUSDT')
        
        # 4. 生成综合报告
        report = self._generate_prediction_report(tech_analysis, market_report, current_price)
        
        print(report)
        
        # 5. 基于预判选择策略
        await self.select_strategy(tech_analysis)
        
        return report
    
    def _generate_prediction_report(self, tech, market_report, current_price) -> str:
        """生成预判报告"""
        
        lines = [
            "=" * 50,
            "📊 BTC/USDT 综合预判报告",
            "=" * 50,
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"💰 当前价格: ${current_price:,.2f}",
            "",
            "📈 技术面分析:",
            f"  市场状态: {tech.state.value}",
            f"  置信度: {tech.confidence:.0%}",
            f"  RSI: {tech.indicators.get('rsi', 0):.1f}",
            f"  趋势强度: {tech.indicators.get('trend_strength', 0):.2f}%",
            "",
        ]
        
        # 外部数据
        if 'fear_greed' in market_report['sources']:
            fg = market_report['sources']['fear_greed']
            lines.append(f"😨 Fear & Greed: {fg['value']}/100 ({fg['classification']})")
            
        if 'funding' in market_report['sources']:
            fr = market_report['sources']['funding']
            lines.append(f"💰 资金费率: {fr['funding_rate']*100:.4f}%")
            
        if 'long_short_ratio' in market_report['sources']:
            ls = market_report['sources']['long_short_ratio']
            lines.append(f"📊 多空比: 多 {ls['long_account_ratio']:.1f}% / 空 {ls['short_account_ratio']:.1f}%")
            
        lines.extend([
            "",
            f"🎯 综合判断: {market_report['analysis']['overall']}",
            f"💡 建议: {market_report['analysis']['recommendation']}",
            "=" * 50,
        ])
        
        return "\n".join(lines)
    
    async def on_market_signal(self, signals: list):
        """Layer 2: 信号处理"""
        logger.warning(f"🚨 捕获信号: {len(signals)} 个")
        
        for signal in signals:
            self.stats['signals_caught'] += 1
            
            # 构建消息
            msg = f"🚨 <b>市场信号</b>\n\n"
            msg += f"类型: {signal.type.value}\n"
            msg += f"详情: {signal.message}\n"
            msg += f"时间: {signal.timestamp.strftime('%H:%M:%S')}"
            
            # 发送通知
            await self.telegram.send_message(msg)
            
            # 如果是重大信号，可能需要调整策略
            if signal.severity in ['warning', 'critical']:
                await self.layer1_prediction()  # 重新预判
    
    async def select_strategy(self, analysis):
        """选择策略"""
        new_strategy = StrategySelector.select(analysis)
        
        if new_strategy != self.current_strategy:
            logger.info(f"🔄 策略切换: {self.current_strategy} → {new_strategy}")
            self.current_strategy = new_strategy
            
            # 初始化策略
            if new_strategy == 'grid':
                from strategies.grid_strategy import GridStrategy
                self.strategy_instance = GridStrategy(self.exchange)
                
            # 通知
            await self.telegram.send_message(
                f"🔄 <b>策略切换</b>\n\n"
                f"新策略: {new_strategy}\n"
                f"原因: {analysis.recommendation}"
            )
    
    async def layer3_execution(self):
        """Layer 3: 策略执行"""
        logger.info("⚡ Layer 3: 策略执行循环启动")
        
        while self.running:
            try:
                # 获取当前价格
                current_price = self.exchange.get_current_price()
                
                # 执行当前策略
                if self.current_strategy == 'grid' and self.strategy_instance:
                    # 网格策略逻辑
                    filled = self.strategy_instance.process_filled_orders()
                    
                    for trade in filled['filled_sells']:
                        self.stats['trades'] += 1
                        profit = trade['price'] * trade['amount'] * 0.001
                        self.stats['profit'] += profit
                        logger.info(f"✅ 卖单成交: ${trade['price']}, 利润: ${profit:.2f}")
                        
                    # 挂单
                    self.strategy_instance.check_and_cancel_orders(current_price)
                    if self.strategy_instance.should_place_orders():
                        self.strategy_instance.place_grid_orders(current_price)
                        
                elif self.current_strategy == 'wait':
                    logger.debug("观望中，不执行交易")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"执行异常: {e}")
                await asyncio.sleep(30)


if __name__ == '__main__':
    system = QuantSystem()
    asyncio.run(system.start())
