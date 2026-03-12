# 币安测试网 API 申请指南

## 1. 注册账号
访问 https://testnet.binance.vision/

点击「Login / Register」，用 GitHub 或邮箱注册。

## 2. 获取 API Key
登录后访问：https://testnet.binance.vision/api/

点击「API Key」→ 「Create API Key」

- API Key 和 Secret 会显示一次，**立即复制保存**
- 勾选「Read Info」「Spot Trading」「Margin Trading」权限

## 3. 配置到项目

```bash
cd /root/.openclaw/workspace/crypto-quant

# 复制配置模板
cp .env.example .env

# 编辑配置
nano .env
```

填入你的 API Key：
```
BINANCE_API_KEY=你的APIKey
BINANCE_API_SECRET=你的Secret
```

## 4. 测试连接
```bash
source venv/bin/activate
python -c "
from core.exchange import ExchangeClient
c = ExchangeClient()
t = c.fetch_ticker()
print(f'连接成功! BTC价格: {t[\"last\"]}')
"
```

---

## Telegram Bot 申请（可选）

1. 打开 Telegram，搜索 @BotFather
2. /newbot 创建新机器人
3. 获取 Token
4. 搜索 @userinfobot 获取你的 Chat ID
5. 填入 .env 配置
