"""
监控层 - 实时监控市场信号，触发预警和策略切换
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    PRICE_ABOVE = "价格突破上沿"
    PRICE_BELOW = "价格跌破下沿"
    VOLUME_SPIKE = "成交量异常"
    FUNDING_HIGH = "资金费率过高"
    FUNDING_NEGATIVE = "资金费率转负"
    LONG_SHORT_EXTREME = "多空比极端"
    FEAR_GREED_EXTREME = "情绪极端"


@dataclass
class Signal:
    """信号"""
    type: SignalType
    value: float
    threshold: float
    message: str
    timestamp: datetime
    severity: str  # info/warning/critical
    
    def __str__(self):
        emoji = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🚨'}
        return f"{emoji.get(self.severity, '📌')} {self.type.value}: {self.message}"


class MarketMonitor:
    """市场监控器"""
    
    def __init__(self, exchange_client, data_fetcher):
        self.exchange = exchange_client
        self.fetcher = data_fetcher
        
        # 监控规则
        self.rules: List[Dict] = []
        
        # 信号回调
        self.on_signal: Optional[Callable] = None
        
        # 状态追踪
        self.last_price: Optional[float] = None
        self.last_volume: Optional[float] = None
        self.last_check: Optional[datetime] = None
        
    def add_rule(self, signal_type: SignalType, threshold: float, 
                 severity: str = 'warning', enabled: bool = True):
        """添加监控规则"""
        self.rules.append({
            'type': signal_type,
            'threshold': threshold,
            'severity': severity,
            'enabled': enabled
        })
        logger.info(f"添加监控规则: {signal_type.value} 阈值={threshold}")
        
    def setup_default_rules(self):
        """设置默认监控规则"""
        # 价格监控
        self.add_rule(SignalType.PRICE_ABOVE, 0.03, 'warning')  # 涨幅 > 3%
        self.add_rule(SignalType.PRICE_BELOW, -0.03, 'warning')  # 跌幅 > 3%
        
        # 成交量监控
        self.add_rule(SignalType.VOLUME_SPIKE, 3.0, 'info')  # 量比 > 3
        
        # 资金费率监控
        self.add_rule(SignalType.FUNDING_HIGH, 0.05, 'warning')  # 费率 > 0.05%
        self.add_rule(SignalType.FUNDING_NEGATIVE, -0.01, 'info')  # 费率 < -0.01%
        
        # 多空比监控
        self.add_rule(SignalType.LONG_SHORT_EXTREME, 0.7, 'warning')  # 多头 > 70%
        
        # 情绪监控
        self.add_rule(SignalType.FEAR_GREED_EXTREME, 85, 'warning')  # 贪婪 > 85
        self.add_rule(SignalType.FEAR_GREED_EXTREME, 20, 'info')  # 恐惧 < 20
        
    async def check(self) -> List[Signal]:
        """检查所有监控规则"""
        signals = []
        
        # 1. 获取当前数据
        current_price = self.exchange.get_current_price()
        ticker = self.exchange.fetch_ticker()
        
        # 2. 获取外部数据
        funding = self.fetcher.get_binance_funding_rate()
        fg = self.fetcher.get_fear_greed_index()
        ls_ratio = self.fetcher.get_binance_long_short_ratio()
        
        # 3. 检查每个规则
        for rule in self.rules:
            if not rule['enabled']:
                continue
                
            signal = None
            
            # 价格涨跌幅
            if rule['type'] == SignalType.PRICE_ABOVE:
                if self.last_price:
                    change = (current_price - self.last_price) / self.last_price
                    if change > rule['threshold']:
                        signal = Signal(
                            type=rule['type'],
                            value=change,
                            threshold=rule['threshold'],
                            message=f"价格涨幅 {change*100:.2f}% 超过阈值",
                            timestamp=datetime.now(),
                            severity=rule['severity']
                        )
                        
            elif rule['type'] == SignalType.PRICE_BELOW:
                if self.last_price:
                    change = (current_price - self.last_price) / self.last_price
                    if change < rule['threshold']:
                        signal = Signal(
                            type=rule['type'],
                            value=change,
                            threshold=rule['threshold'],
                            message=f"价格跌幅 {change*100:.2f}% 超过阈值",
                            timestamp=datetime.now(),
                            severity=rule['severity']
                        )
                        
            # 成交量异常
            elif rule['type'] == SignalType.VOLUME_SPIKE:
                current_volume = ticker.get('baseVolume', 0)
                if self.last_volume and self.last_volume > 0:
                    volume_ratio = current_volume / self.last_volume
                    if volume_ratio > rule['threshold']:
                        signal = Signal(
                            type=rule['type'],
                            value=volume_ratio,
                            threshold=rule['threshold'],
                            message=f"成交量放大 {volume_ratio:.1f} 倍",
                            timestamp=datetime.now(),
                            severity=rule['severity']
                        )
                        
            # 资金费率
            elif rule['type'] == SignalType.FUNDING_HIGH and funding:
                rate = funding['funding_rate'] * 100
                if rate > rule['threshold']:
                    signal = Signal(
                        type=rule['type'],
                        value=rate,
                        threshold=rule['threshold'],
                        message=f"资金费率过高: {rate:.4f}%",
                        timestamp=datetime.now(),
                        severity=rule['severity']
                    )
                    
            elif rule['type'] == SignalType.FUNDING_NEGATIVE and funding:
                rate = funding['funding_rate'] * 100
                if rate < rule['threshold']:
                    signal = Signal(
                        type=rule['type'],
                        value=rate,
                        threshold=rule['threshold'],
                        message=f"资金费率转负: {rate:.4f}%",
                        timestamp=datetime.now(),
                        severity=rule['severity']
                    )
                    
            # 多空比
            elif rule['type'] == SignalType.LONG_SHORT_EXTREME and ls_ratio:
                long_ratio = ls_ratio['long_account_ratio'] / 100
                if long_ratio > rule['threshold'] or long_ratio < (1 - rule['threshold']):
                    signal = Signal(
                        type=rule['type'],
                        value=long_ratio,
                        threshold=rule['threshold'],
                        message=f"多空比极端: 多 {ls_ratio['long_account_ratio']:.1f}%",
                        timestamp=datetime.now(),
                        severity=rule['severity']
                    )
                    
            # 情绪指数
            elif rule['type'] == SignalType.FEAR_GREED_EXTREME and fg:
                value = fg['value']
                if value > rule['threshold'] or value < (100 - rule['threshold']):
                    signal = Signal(
                        type=rule['type'],
                        value=value,
                        threshold=rule['threshold'],
                        message=f"情绪极端: {value}/100 ({fg['classification']})",
                        timestamp=datetime.now(),
                        severity=rule['severity']
                    )
                    
            if signal:
                signals.append(signal)
                logger.warning(f"触发信号: {signal}")
                
        # 更新状态
        self.last_price = current_price
        self.last_volume = ticker.get('baseVolume', 0)
        self.last_check = datetime.now()
        
        # 触发回调
        if signals and self.on_signal:
            await self.on_signal(signals)
            
        return signals
    
    async def run_loop(self, interval: int = 60):
        """运行监控循环"""
        logger.info("🔍 市场监控启动")
        
        while True:
            try:
                signals = await self.check()
                
                if signals:
                    logger.info(f"检测到 {len(signals)} 个信号")
                    
            except Exception as e:
                logger.error(f"监控异常: {e}")
                
            await asyncio.sleep(interval)


# 使用示例
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/crypto-quant')
    
    from core.exchange import ExchangeClient
    from core.data_fetcher import ExternalDataFetcher
    
    async def on_signals(signals: List[Signal]):
        """信号回调"""
        print(f"\n🚨 检测到 {len(signals)} 个信号:")
        for s in signals:
            print(f"  {s}")
    
    async def main():
        exchange = ExchangeClient()
        fetcher = ExternalDataFetcher()
        
        monitor = MarketMonitor(exchange, fetcher)
        monitor.setup_default_rules()
        monitor.on_signal = on_signals
        
        # 运行一次检查
        signals = await monitor.check()
        if signals:
            for s in signals:
                print(s)
        else:
            print("✅ 当前无异常信号")
            
    asyncio.run(main())
