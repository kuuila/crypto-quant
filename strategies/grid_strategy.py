"""
网格交易策略
原理：在震荡行情中，在价格区间内设置多个买入/卖出点位
价格下跌到网格线时买入，上涨到网格线时卖出
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from core.exchange import ExchangeClient
from config.settings import GRID_CONFIG, RISK_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class GridLevel:
    """网格点位"""
    level: int
    price: float
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    filled: bool = False


class GridStrategy:
    """网格交易策略"""
    
    def __init__(self, exchange: ExchangeClient, config: Dict = None):
        self.exchange = exchange
        self.config = config or GRID_CONFIG
        self.risk_config = RISK_CONFIG
        
        # 网格参数
        self.upper_price = self.config['upper_price']
        self.lower_price = self.config['lower_price']
        self.grid_count = self.config['grid_count']
        self.investment = self.config['investment_amount']
        self.min_order_value = self.config['min_order_value']
        
        # 计算网格间距
        self.grid_step = (self.upper_price - self.lower_price) / (self.grid_count - 1)
        
        # 初始化网格
        self.grids: List[GridLevel] = self._init_grids()
        
        # 订单追踪
        self.active_orders: Dict[str, Dict] = {}
        
        logger.info(f"网格策略初始化: {self.lower_price} - {self.upper_price}, {self.grid_count} 格")
        
    def _init_grids(self) -> List[GridLevel]:
        """初始化网格点位"""
        grids = []
        for i in range(self.grid_count):
            price = self.lower_price + i * self.grid_step
            grids.append(GridLevel(level=i, price=price))
        return grids
    
    def calculate_position_size(self, price: float) -> float:
        """计算仓位大小"""
        # 每个网格的仓位 = 总资金 / 网格数量
        # 预留一半资金做多，一半做空（双向网格）
        per_grid_value = self.investment / self.grid_count
        
        # 根据价格计算数量
        amount = per_grid_value / price
        return amount
    
    def get_current_grid_level(self, current_price: float) -> int:
        """获取当前价格所在的网格层级"""
        if current_price >= self.upper_price:
            return self.grid_count - 1
        if current_price <= self.lower_price:
            return 0
        return int((current_price - self.lower_price) / self.grid_step)
    
    def should_place_orders(self) -> bool:
        """检查是否需要下单"""
        # 检查挂单数量
        open_orders = self.exchange.fetch_open_orders()
        if len(open_orders) >= self.risk_config['max_open_orders']:
            logger.warning(f"挂单数量已达上限: {len(open_orders)}")
            return False
        return True
    
    def place_grid_orders(self, current_price: float) -> List[Dict]:
        """在网格点位下单"""
        placed_orders = []
        current_level = self.get_current_grid_level(current_price)
        
        # 获取账户余额
        balance = self.exchange.fetch_balance()
        available_quote = balance['free'].get('USDT', 0)
        available_base = balance['free'].get(self.exchange.parse_symbol()['base'], 0)
        
        logger.info(f"当前价格: {current_price}, 层级: {current_level}, 可用 USDT: {available_quote}")
        
        # 在当前价格上方 2 格和下方 2 格下单
        for i in range(max(0, current_level - 2), min(self.grid_count, current_level + 3)):
            grid = self.grids[i]
            
            # 计算订单数量
            amount = self.calculate_position_size(grid.price)
            order_value = amount * grid.price
            
            # 检查最小订单金额
            if order_value < self.min_order_value:
                continue
            
            # 检查余额是否足够
            if i > current_level:  # 卖单，需要 base 币
                if available_base < amount:
                    continue
            else:  # 买单，需要 USDT
                if available_quote < order_value:
                    continue
                    
            # 检查是否已经有订单
            if grid.buy_order_id or grid.sell_order_id:
                continue
                
            # 下单
            if i < current_level:  # 价格低于当前价，挂买单
                try:
                    order = self.exchange.create_limit_order(
                        'buy', amount, grid.price
                    )
                    grid.buy_order_id = order['id']
                    self.active_orders[order['id']] = {
                        'type': 'buy',
                        'grid': grid,
                        'amount': amount,
                        'price': grid.price
                    }
                    placed_orders.append(order)
                    available_quote -= order_value
                    logger.info(f"挂买单: 层级 {i}, 价格 {grid.price}, 数量 {amount}")
                except Exception as e:
                    logger.error(f"挂买单失败: {e}")
                    
            elif i > current_level:  # 价格高于当前价，挂卖单
                try:
                    order = self.exchange.create_limit_order(
                        'sell', amount, grid.price
                    )
                    grid.sell_order_id = order['id']
                    self.active_orders[order['id']] = {
                        'type': 'sell',
                        'grid': grid,
                        'amount': amount,
                        'price': grid.price
                    }
                    placed_orders.append(order)
                    available_base -= amount
                    logger.info(f"挂卖单: 层级 {i}, 价格 {grid.price}, 数量 {amount}")
                except Exception as e:
                    logger.error(f"挂卖单失败: {e}")
        
        return placed_orders
    
    def check_and_cancel_orders(self, current_price: float) -> List[str]:
        """检查并取消被套住的订单"""
        cancelled = []
        current_level = self.get_current_grid_level(current_price)
        
        for grid in self.grids:
            # 如果买单价格高于当前价格 2 格以上，取消
            if grid.buy_order_id and grid.level < current_level - 2:
                try:
                    self.exchange.cancel_order(grid.buy_order_id)
                    cancelled.append(grid.buy_order_id)
                    grid.buy_order_id = None
                    logger.info(f"取消买单: 层级 {grid.level}, 价格 {grid.price}")
                except Exception as e:
                    logger.error(f"取消买单失败: {e}")
                    
            # 如果卖单价格低于当前价格 2 格以上，取消
            if grid.sell_order_id and grid.level > current_level + 2:
                try:
                    self.exchange.cancel_order(grid.sell_order_id)
                    cancelled.append(grid.sell_order_id)
                    grid.sell_order_id = None
                    logger.info(f"取消卖单: 层级 {grid.level}, 价格 {grid.price}")
                except Exception as e:
                    logger.error(f"取消卖单失败: {e}")
                    
        return cancelled
    
    def process_filled_orders(self) -> Dict:
        """处理已成交订单"""
        results = {
            'filled_buys': [],
            'filled_sells': [],
            'cancelled': []
        }
        
        # 检查所有活跃订单
        order_ids = list(self.active_orders.keys())
        for order_id in order_ids:
            try:
                order = self.exchange.fetch_order(order_id)
                
                if order['status'] == 'closed':  # 成交
                    order_info = self.active_orders.pop(order_id)
                    grid = order_info['grid']
                    
                    if order_info['type'] == 'buy':
                        grid.buy_order_id = None
                        grid.filled = True
                        results['filled_buys'].append({
                            'price': order['price'],
                            'amount': order['amount'],
                            'grid_level': grid.level
                        })
                        logger.info(f"买单成交: 层级 {grid.level}, 价格 {order['price']}")
                    else:
                        grid.sell_order_id = None
                        results['filled_sells'].append({
                            'price': order['price'],
                            'amount': order['amount'],
                            'grid_level': grid.level
                        })
                        logger.info(f"卖单成交: 层级 {grid.level}, 价格 {order['price']}")
                        
            except Exception as e:
                logger.error(f"检查订单失败 {order_id}: {e}")
                
        return results
    
    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            'config': self.config,
            'grids': [
                {
                    'level': g.level,
                    'price': round(g.price, 2),
                    'has_buy': g.buy_order_id is not None,
                    'has_sell': g.sell_order_id is not None
                }
                for g in self.grids
            ],
            'active_orders': len(self.active_orders)
        }


# 简单运行示例
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    exchange = ExchangeClient()
    strategy = GridStrategy(exchange)
    
    # 获取当前价格并下单
    current_price = exchange.get_current_price()
    print(f"当前价格: {current_price}")
    
    # 尝试下单
    orders = strategy.place_grid_orders(current_price)
    print(f"已挂订单数: {len(orders)}")
