#!/usr/bin/env python3
"""
测试 API 连接
"""
import sys
sys.path.insert(0, '/root/.openclaw/workspace/crypto-quant')

from dotenv import load_dotenv
load_dotenv('/root/.openclaw/workspace/crypto-quant/.env')

from core.exchange import ExchangeClient

def test_connection():
    print("=" * 50)
    print("🔍 测试 API 连接")
    print("=" * 50)
    
    try:
        client = ExchangeClient()
        
        # 1. 测试公开接口
        print("\n📊 测试公开接口...")
        ticker = client.fetch_ticker()
        print(f"✅ BTC/USDT 价格: {ticker['last']}")
        
        # 2. 测试私有接口（需要 API Key）
        print("\n🔐 测试私有接口...")
        balance = client.fetch_balance()
        print(f"✅ 账户余额: {balance['free']}")
        
        # 3. 测试挂单（测试网不会真实成交）
        print("\n📝 测试挂单...")
        print("⚠️  跳过挂单测试（需要手动确认）")
        
        print("\n" + "=" * 50)
        print("🎉 API 连接测试通过!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n可能原因:")
        print("1. API Key 未配置或错误")
        print("2. API Key 权限不足")
        print("3. 网络问题")
        return False
        
    return True


if __name__ == '__main__':
    test_connection()
