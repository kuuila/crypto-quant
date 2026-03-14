"""
交易所接口模块 - 统一封装 CCXT
"""
import ccxt
import time
from typing import Optional, Dict, List, Any
from config.settings import EXCHANGE_CONFIG, TRADING_PAIR


class ExchangeClient:
    """交易所客户端"""
    
    def __init__(self, config: Dict = None):
        self.config = config or EXCHANGE_CONFIG
        self.exchange_id = self.config.get('exchange_id', 'binance')
        self.exchange = self._init_exchange()
        self.symbol = TRADING_PAIR
        
    def _init_exchange(self):
        """初始化交易所"""
        exchange_class = getattr(ccxt, self.exchange_id)
        
        params = {
            'enableRateLimit': True,
            'options': self.config.get('options', {})
        }
        
        # 如果有 API key 则配置
        if self.config.get('api_key'):
            params['apiKey'] = self.config['api_key']
            params['secret'] = self.config['api_secret']
        
        # 如果是测试网模式
        if self.config.get('sandbox', False):
            params['urls'] = {
                'api': {
                    'public': 'https://testnet.binance.vision/api',
                    'private': 'https://testnet.binance.vision/api',
                }
            }
            
        return exchange_class(params)
    
    # ========== 市场数据 ==========
    
    def fetch_ticker(self, symbol: str = None) -> Dict:
        """获取实时行情"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_ticker(symbol)
    
    def fetch_order_book(self, symbol: str = None, limit: int = 20) -> Dict:
        """获取订单簿"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_order_book(symbol, limit)
    
    def fetch_ohlcv(self, symbol: str = None, timeframe: str = '1h', 
                    since: Optional[int] = None, limit: int = 100) -> List:
        """获取 K 线数据"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    
    def fetch_balance(self) -> Dict:
        """获取账户余额"""
        return self.exchange.fetch_balance()
    
    # ========== 订单操作 ==========
    
    def create_limit_order(self, side: str, amount: float, price: float, 
                           symbol: str = None) -> Dict:
        """创建限价单"""
        symbol = symbol or self.symbol
        return self.exchange.create_limit_order(symbol, side, amount, price)
    
    def create_market_order(self, side: str, amount: float, symbol: str = None) -> Dict:
        """创建市价单"""
        symbol = symbol or self.symbol
        return self.exchange.create_order(symbol, 'market', side, amount)
    
    def cancel_order(self, order_id: str, symbol: str = None) -> Dict:
        """取消订单"""
        symbol = symbol or self.symbol
        return self.exchange.cancel_order(order_id, symbol)
    
    def fetch_open_orders(self, symbol: str = None) -> List:
        """获取当前挂单"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_open_orders(symbol)
    
    def fetch_order(self, order_id: str, symbol: str = None) -> Dict:
        """查询订单状态"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_order(order_id, symbol)
    
    def fetch_my_trades(self, symbol: str = None, limit: int = 100) -> List:
        """获取我的成交记录"""
        symbol = symbol or self.symbol
        return self.exchange.fetch_my_trades(symbol, limit=limit)
    
    # ========== 辅助功能 ==========
    
    def get_current_price(self, symbol: str = None) -> float:
        """获取当前价格"""
        ticker = self.fetch_ticker(symbol)
        return ticker['last']
    
    def get_mid_price(self, symbol: str = None) -> float:
        """获取中间价"""
        ticker = self.fetch_ticker(symbol)
        return (ticker['bid'] + ticker['ask']) / 2
    
    def parse_symbol(self, symbol: str = None) -> Dict:
        """解析交易对"""
        symbol = symbol or self.symbol
        base, quote = symbol.split('/')
        return {'base': base, 'quote': quote}


# 测试
if __name__ == '__main__':
    client = ExchangeClient()
    
    # 测试获取行情
    ticker = client.fetch_ticker()
    print(f"当前 {client.symbol} 价格: {ticker['last']}")
    
    # 测试获取余额
    balance = client.fetch_balance()
    print(f"可用 USDT: {balance['free']['USDT']}")
