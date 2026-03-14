"""
外部数据获取模块 - 整合多种数据源
"""
import requests
import json
from typing import Dict, Optional
from datetime import datetime


class ExternalDataFetcher:
    """外部数据获取器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
    # ========== Fear & Greed Index ==========
    
    def get_fear_greed_index(self) -> Optional[Dict]:
        """获取恐惧贪婪指数"""
        url = "https://api.alternative.me/fng/"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('data'):
                item = data['data'][0]
                return {
                    'value': int(item['value']),
                    'classification': item['value_classification'],
                    'timestamp': datetime.fromtimestamp(int(item['timestamp']))
                }
        except Exception as e:
            print(f"获取 Fear & Greed 失败: {e}")
            
        return None
    
    # ========== 币安数据 ==========
    
    def get_binance_funding_rate(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """获取资金费率"""
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                'symbol': symbol,
                'funding_rate': float(data.get('lastFundingRate', 0)),
                'next_funding_time': datetime.fromtimestamp(data.get('nextFundingTime', 0) / 1000),
                'mark_price': float(data.get('markPrice', 0)),
                'index_price': float(data.get('indexPrice', 0))
            }
        except Exception as e:
            print(f"获取资金费率失败: {e}")
            return None
    
    def get_binance_long_short_ratio(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """获取多空比"""
        try:
            url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
            params = {'symbol': symbol, 'periodType': '1h', 'limit': 5}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data:
                latest = data[-1]
                return {
                    'long_account_ratio': float(latest['longAccount']) * 100,
                    'short_account_ratio': float(latest['shortAccount']) * 100,
                    'timestamp': datetime.fromtimestamp(latest['updateTime'] / 1000)
                }
        except Exception as e:
            print(f"获取多空比失败: {e}")
            return None
    
    def get_binance_open_interest(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """获取持仓量 OI"""
        try:
            url = "https://fapi.binance.com/futures/data/openInterestHist"
            params = {
                'symbol': symbol,
                'periodType': '1h',
                'limit': 5
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data:
                latest = data[-1]
                return {
                    'symbol': symbol,
                    'open_interest': float(latest['sumOpenInterest']),
                    'timestamp': datetime.fromtimestamp(latest['updateTime'] / 1000)
                }
        except Exception as e:
            print(f"获取 OI 失败: {e}")
            return None
    
    # ========== 链上数据 (简单版) ==========
    
    def get_onchain_simple(self) -> Optional[Dict]:
        """简单的链上数据（模拟）"""
        # 实际应该用 Glassnode API
        # 这里返回模拟数据演示
        return {
            'exchange_inflow_24h': -12500,  # 负数表示流出
            'whale_count': 15,
            'active_addresses': 1250000,
            'difficulty_adjustment': 3.2  # 百分比
        }
    
    # ========== 综合预判报告 ==========
    
    def generate_market_report(self, symbol: str = "BTCUSDT") -> Dict:
        """生成综合市场报告"""
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'sources': {}
        }
        
        # 1. Fear & Greed
        fg = self.get_fear_greed_index()
        if fg:
            report['sources']['fear_greed'] = fg
            
        # 2. 资金费率
        funding = self.get_binance_funding_rate(symbol)
        if funding:
            report['sources']['funding'] = funding
            
        # 3. 多空比
        ls_ratio = self.get_binance_long_short_ratio(symbol)
        if ls_ratio:
            report['sources']['long_short_ratio'] = ls_ratio
            
        # 4. 持仓量
        oi = self.get_binance_open_interest(symbol)
        if oi:
            report['sources']['open_interest'] = oi
        
        # 5. 综合判断
        report['analysis'] = self._analyze_sources(report['sources'])
        
        return report
    
    def _analyze_sources(self, sources: Dict) -> Dict:
        """分析各数据源"""
        signals = []
        
        # Fear & Greed
        if 'fear_greed' in sources:
            fg = sources['fear_greed']
            value = fg['value']
            if value < 25:
                signals.append({'type': 'fear_greed', 'signal': 'oversold', 'strength': 'strong', 'desc': '极度恐慌，可能抄底'})
            elif value < 45:
                signals.append({'type': 'fear_greed', 'signal': 'fear', 'strength': 'medium', 'desc': '恐慌，可能超卖'})
            elif value > 75:
                signals.append({'type': 'fear_greed', 'signal': 'greed', 'strength': 'medium', 'desc': '贪婪，注意风险'})
            elif value > 90:
                signals.append({'type': 'fear_greed', 'signal': 'extreme_greed', 'strength': 'strong', 'desc': '极度贪婪，可能见顶'})
                
        # 资金费率
        if 'funding' in sources:
            fr = sources['funding']
            rate = fr['funding_rate'] * 100
            if rate > 0.05:
                signals.append({'type': 'funding', 'signal': 'high_funding', 'strength': 'warning', 'desc': f'高资金费率 {rate:.3f}%'})
            elif rate < -0.05:
                signals.append({'type': 'funding', 'signal': 'low_funding', 'strength': 'info', 'desc': f'负费率 {rate:.3f}%'})
                
        # 多空比
        if 'long_short_ratio' in sources:
            ls = sources['long_short_ratio']
            if ls['long_account_ratio'] > 60:
                signals.append({'type': 'long_short', 'signal': 'long_heavy', 'strength': 'warning', 'desc': f'多头 {ls["long_account_ratio"]:.1f}% 偏多'})
            elif ls['short_account_ratio'] > 60:
                signals.append({'type': 'long_short', 'signal': 'short_heavy', 'strength': 'info', 'desc': f'空头 {ls["short_account_ratio"]:.1f}% 偏空'})
        
        # 综合判断
        bullish = sum(1 for s in signals if 'greed' in s.get('signal', '') or 'long' in s.get('signal', '') or s.get('signal') == 'oversold')
        bearish = sum(1 for s in signals if 'fear' in s.get('signal', '') or 'short' in s.get('signal', '') or 'greed' in s.get('signal', '') and s.get('strength') == 'strong')
        
        if bullish > bearish:
            overall = 'bullish'
            recommendation = '偏多，但注意高位风险'
        elif bearish > bullish:
            overall = 'bearish'
            recommendation = '偏空，可考虑分批建仓'
        else:
            overall = 'neutral'
            recommendation = '中性，等待方向明确'
            
        return {
            'signals': signals,
            'overall': overall,
            'recommendation': recommendation
        }


if __name__ == '__main__':
    fetcher = ExternalDataFetcher()
    
    print("=" * 60)
    print("📊 BTC/USDT 综合市场报告")
    print("=" * 60)
    
    report = fetcher.generate_market_report('BTCUSDT')
    
    print(f"\n⏰ {report['timestamp']}")
    print(f"📌 交易对: {report['symbol']}")
    
    print("\n" + "-" * 60)
    print("📈 数据源")
    print("-" * 60)
    
    # Fear & Greed
    if 'fear_greed' in report['sources']:
        fg = report['sources']['fear_greed']
        print(f"😨 Fear & Greed: {fg['value']}/100 ({fg['classification']})")
        
    # 资金费率
    if 'funding' in report['sources']:
        fr = report['sources']['funding']
        print(f"💰 资金费率: {fr['funding_rate']*100:.4f}%")
        
    # 多空比
    if 'long_short_ratio' in report['sources']:
        ls = report['sources']['long_short_ratio']
        print(f"📊 多空比: 多 {ls['long_account_ratio']:.1f}% / 空 {ls['short_account_ratio']:.1f}%")
        
    # OI
    if 'open_interest' in report['sources']:
        oi = report['sources']['open_interest']
        print(f"📉 持仓量: {oi['open_interest']/1000000:.2f}M BTC")
        
    print("\n" + "-" * 60)
    print("🔍 分析结果")
    print("-" * 60)
    
    analysis = report['analysis']
    
    print(f"📌 综合判断: {analysis['overall']}")
    print(f"💡 建议: {analysis['recommendation']}")
    
    print("\n📋 信号列表:")
    for signal in analysis['signals']:
        emoji = '🟢' if signal['strength'] == 'info' else ('🟡' if signal['strength'] == 'warning' else '🔴')
        print(f"  {emoji} {signal['desc']}")
