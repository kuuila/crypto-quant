"""
回测模块 - 验证策略在历史数据上的表现
"""
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from typing import List


class GridStrategyBacktest(Strategy):
    """网格策略回测实现"""
    
    # 策略参数（会在回测中优化）
    grid_count = 10
    grid_upper = 75000
    grid_lower = 65000
    position_pct = 0.1  # 每格仓位比例
    
    def init(self):
        # 计算网格点位
        self.grid_step = (self.grid_upper - self.grid_lower) / (self.grid_count - 1)
        self.grids = [self.grid_lower + i * self.grid_step for i in range(self.grid_count)]
        
        # 追踪挂单
        self.pending_buys = set()
        self.pending_sells = set()
        self.grid_positions = {}  # 每个网格的持仓
        
    def next(self):
        """每个K线周期执行"""
        current_price = self.data.Close[-1]
        
        # 找到当前价格所在网格
        current_grid = None
        for i, grid_price in enumerate(self.grids):
            if current_price >= grid_price:
                current_grid = i
        
        if current_grid is None:
            return
            
        # 在当前价格上下 2 格挂单
        for i in range(max(0, current_grid - 2), min(self.grid_count, current_grid + 3)):
            grid_price = self.grids[i]
            
            # 计算订单大小
            position_value = self.equity * self.position_pct
            size = position_value / grid_price
            
            # 挂买单（低于当前价）
            if i < current_grid and grid_price not in self.pending_buys:
                self.buy(limit=grid_price, size=size)
                self.pending_buys.add(grid_price)
                
            # 挂卖单（高于当前价）
            elif i > current_grid and grid_price not in self.pending_sells:
                if self.position.size > 0:
                    self.sell(limit=grid_price, size=size)
                    self.pending_sells.add(grid_price)


def run_backtest(df: pd.DataFrame, **kwargs):
    """
    运行回测
    
    Args:
        df: 包含 OHLCV 数据的 DataFrame
            columns: Open, High, Low, Close, Volume
            index: DateTime
        **kwargs: 策略参数
    
    Returns:
        Backtest 结果对象
    """
    bt = Backtest(
        df, 
        GridStrategyBacktest,
        cash=10000,  # 初始资金
        commission=0.001,  # 手续费 0.1%
        exclusive_orders=False  # 允许同时存在多个订单
    )
    
    # 运行优化
    stats = bt.optimize(
        grid_count=range(5, 20, 2),
        grid_upper=range(70000, 80000, 5000),
        grid_lower=range(60000, 65000, 2500),
        position_pct=[0.05, 0.1, 0.15],
        maximize='Sharpe Ratio'
    )
    
    return stats, bt


def fetch_historical_data(exchange, symbol: str, timeframe: str = '1h', limit: int = 1000):
    """获取历史数据"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    df = pd.DataFrame(
        ohlcv, 
        columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    return df


if __name__ == '__main__':
    from core.exchange import ExchangeClient
    
    # 获取历史数据
    exchange = ExchangeClient()
    df = fetch_historical_data(exchange, 'BTC/USDT', '1h', 500)
    
    print(f"获取 {len(df)} 条历史数据")
    print(df.head())
    
    # 运行回测（这里只是示例，实际优化很耗时间）
    # stats, bt = run_backtest(df)
    # print(stats)
    # bt.plot()
