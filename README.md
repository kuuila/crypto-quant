# 🦐 虾3x 智能量化交易机器人

> 先分析市场，再选择策略，动态调整，智能交易

## 核心特性

### 🧠 智能策略选择
不是固定策略！机器人会分析市场状态，自动选择最合适的策略：

| 市场状态 | 选择策略 | 说明 |
|----------|----------|------|
| 📈 单边上涨 | 趋势跟踪/做多 | 均线多头排列，RSI 强势 |
| 📉 单边下跌 | 空仓/做空 | 避免抄底，保护本金 |
| ↔️ 横盘震荡 | 网格交易 | 低买高卖，赚波动 |
| ⚡ 高波动 | 小仓位/观望 | 降低风险 |
| ❓ 方向不明 | 观望等待 | 不强行交易 |

### 📊 分析指标
- **移动平均线**: MA20, MA60 趋势判断
- **RSI**: 超买超卖识别
- **布林带**: 价格位置和波动范围
- **ATR**: 真实波动幅度
- **成交量**: 量价配合分析
- **趋势强度**: 斜率计算

### 🔄 动态调整
- 每 5 分钟重新分析市场
- 状态变化自动切换策略
- Telegram 实时推送变更通知

---

## 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/kuuila/crypto-quant.git
cd crypto-quant
```

### 2. 安装依赖
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 API Key
```bash
cp .env.example .env
# 编辑 .env，填入币安测试网 API Key
```

### 4. 运行测试
```bash
# 模拟模式
python bot/main.py --sim

# 实际运行（测试网）
python bot/main.py --run
```

---

## 项目结构

```
crypto-quant/
├── bot/
│   └── main.py              # 主程序 - 智能调度
├── core/
│   ├── exchange.py          # 交易所接口 (CCXT)
│   ├── market_analyzer.py   # 市场分析引擎 ⭐
│   └── monitor.py           # Telegram 监控
├── strategies/
│   └── grid_strategy.py     # 网格策略
├── backtest/
│   └── engine.py            # 回测系统
├── config/
│   └── settings.py          # 配置文件
├── README.md
└── SETUP.md                 # 详细部署指南
```

---

## 策略对比

| 策略 | 适用市场 | 风险 | 预期收益 |
|------|----------|------|----------|
| **网格交易** | 震荡市 | ⭐⭐ | 月化 2-5% |
| **趋势跟踪** | 单边市 | ⭐⭐⭐ | 月化 5-15% |
| **资金费率套利** | 永续合约 | ⭐ | 年化 10-30% |

---

## 风控配置

```python
# config/settings.py
RISK_CONFIG = {
    'daily_loss_limit': 100,    # 日亏损上限 (USDT)
    'max_position_value': 2000,  # 最大仓位
    'max_open_orders': 20,       # 最大挂单数
}
```

---

## 风险提示

⚠️ **加密货币交易高风险**
- 机器人只能降低风险，不能保证盈利
- 建议先在测试网运行 2 周
- 小资金实盘，逐步增加

---

## 技术栈

- **Python 3.11+**
- **CCXT**: 统一交易所接口
- **Pandas/NumPy**: 数据分析
- **python-telegram-bot**: 消息推送

---

*Created by 虾3x @ kuuila* ♠️
