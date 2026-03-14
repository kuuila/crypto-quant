import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 交易所配置
EXCHANGE_CONFIG = {
    'exchange_id': 'binance',  # 币安
    'api_key': os.getenv('BINANCE_API_KEY', ''),
    'api_secret': os.getenv('BINANCE_API_SECRET', ''),
    'sandbox': True,  # 默认使用测试网
    'options': {
        'defaultType': 'spot',  # 现货交易
    }
}

# 交易对配置
TRADING_PAIR = 'BTC/USDT'

# 网格策略参数
GRID_CONFIG = {
    'upper_price': 75000,      # 网格上限
    'lower_price': 65000,      # 网格下限
    'grid_count': 10,          # 网格数量
    'investment_amount': 1000, # 投入资金 (USDT)
    'min_order_value': 10,     # 最小订单金额
}

# 风控配置
RISK_CONFIG = {
    'max_position_value': 2000,    # 最大仓位价值
    'stop_loss_pct': 0.05,         # 止损比例 5%
    'daily_loss_limit': 100,       # 日亏损上限 (USDT)
    'max_open_orders': 20,         # 最大挂单数量
}

# 监控配置
MONITOR_CONFIG = {
    'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    'log_level': 'INFO',
}

# 数据存储
DATA_CONFIG = {
    'data_dir': './data',
    'log_dir': './logs',
}
