"""
市场分析模块 - 判断当前市场状态，选择合适策略
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketState(Enum):
    """市场状态"""
    TRENDING_UP = "单边上涨"      # 上涨趋势
    TRENDING_DOWN = "单边下跌"    # 下跌趋势
    RANGING = "横盘震荡"          # 区间震荡
    VOLATILE = "高波动"           # 剧烈波动
    CONSOLIDATING = "整理中"      # 方向不明


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    state: MarketState
    confidence: float  # 置信度 0-1
    indicators: Dict   # 技术指标
    recommendation: str  # 建议策略
    risk_level: str   # 风险等级 low/medium/high
    
    def __str__(self):
        return f"""
📊 市场状态: {self.state.value}
🎯 置信度: {self.confidence:.0%}
💡 建议: {self.recommendation}
⚠️ 风险: {self.risk_level}
"""


class MarketAnalyzer:
    """市场分析器"""
    
    def __init__(self):
        # 指标参数
        self.ma_short = 20    # 短期均线
        self.ma_long = 60     # 长期均线
        self.rsi_period = 14  # RSI 周期
        self.bb_period = 20   # Bollinger Bands 周期
        self.bb_std = 2       # BB 标准差倍数
        
    def analyze(self, df: pd.DataFrame, current_price: float) -> MarketAnalysis:
        """
        分析市场状态
        
        Args:
            df: K线数据 (OHLCV)
            current_price: 当前价格
        """
        # 计算技术指标
        indicators = self._calculate_indicators(df)
        
        # 综合判断市场状态
        state, confidence = self._determine_state(df, indicators, current_price)
        
        # 生成建议
        recommendation, risk_level = self._get_recommendation(state, indicators)
        
        return MarketAnalysis(
            state=state,
            confidence=confidence,
            indicators=indicators,
            recommendation=recommendation,
            risk_level=risk_level
        )
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """计算技术指标"""
        close = df['Close']
        
        # 1. 移动平均线
        ma20 = close.rolling(window=self.ma_short).mean()
        ma60 = close.rolling(window=self.ma_long).mean()
        
        # 2. RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands
        bb_ma = close.rolling(window=self.bb_period).mean()
        bb_std = close.rolling(window=self.bb_period).std()
        bb_upper = bb_ma + (bb_std * self.bb_std)
        bb_lower = bb_ma - (bb_std * self.bb_std)
        
        # 4. 波动率
        returns = close.pct_change()
        volatility = returns.rolling(window=20).std() * np.sqrt(24)  # 日化
        
        # 5. ATR (Average True Range)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - close.shift())
        low_close = np.abs(df['Low'] - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        # 6. 成交量变化
        volume_ma = df['Volume'].rolling(window=20).mean()
        
        return {
            'ma20': ma20.iloc[-1] if len(ma20) > 0 else 0,
            'ma60': ma60.iloc[-1] if len(ma60) > 0 else 0,
            'rsi': rsi.iloc[-1] if len(rsi) > 0 else 50,
            'bb_upper': bb_upper.iloc[-1] if len(bb_upper) > 0 else 0,
            'bb_lower': bb_lower.iloc[-1] if len(bb_lower) > 0 else 0,
            'bb_position': (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) if len(bb_upper) > 0 else 0.5,
            'volatility': volatility.iloc[-1] if len(volatility) > 0 else 0,
            'atr': atr.iloc[-1] if len(atr) > 0 else 0,
            'volume_ratio': df['Volume'].iloc[-1] / volume_ma.iloc[-1] if len(volume_ma) > 0 and volume_ma.iloc[-1] > 0 else 1,
            'trend_strength': self._calculate_trend_strength(ma20, ma60)
        }
    
    def _calculate_trend_strength(self, ma20: pd.Series, ma60: pd.Series) -> float:
        """计算趋势强度"""
        if len(ma20) < 2 or len(ma60) < 2:
            return 0
        # 均线斜率
        slope_short = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] if ma20.iloc[-5] != 0 else 0
        slope_long = (ma60.iloc[-1] - ma60.iloc[-5]) / ma60.iloc[-5] if ma60.iloc[-5] != 0 else 0
        
        # 趋势强度 = 斜率 * 方向
        return (slope_short + slope_long) / 2 * 100  # 转为百分比
    
    def _determine_state(self, df: pd.DataFrame, indicators: Dict, current_price: float) -> Tuple[MarketState, float]:
        """判断市场状态"""
        
        rsi = indicators['rsi']
        volatility = indicators['volatility']
        trend_strength = indicators['trend_strength']
        bb_position = indicators['bb_position']
        
        votes = {}
        
        # 1. RSI 判断
        if rsi > 70:
            votes[MarketState.TRENDING_UP] = 0.8
        elif rsi < 30:
            votes[MarketState.TRENDING_DOWN] = 0.8
        elif 40 <= rsi <= 60:
            votes[MarketState.RANGING] = 0.6
        else:
            votes[MarketState.CONSOLIDATING] = 0.5
            
        # 2. 均线判断
        if indicators['ma20'] > indicators['ma60'] * 1.05:
            votes[MarketState.TRENDING_UP] = votes.get(MarketState.TRENDING_UP, 0) + 0.7
        elif indicators['ma20'] < indicators['ma60'] * 0.95:
            votes[MarketState.TRENDING_DOWN] = votes.get(MarketState.TRENDING_DOWN, 0) + 0.7
            
        # 3. 波动率判断
        if volatility > 0.05:  # 日波动 > 5%
            votes[MarketState.VOLATILE] = 0.8
        elif volatility < 0.02:  # 日波动 < 2%
            votes[MarketState.RANGING] = votes.get(MarketState.RANGING, 0) + 0.5
            
        # 4. 趋势强度判断
        if trend_strength > 2:
            votes[MarketState.TRENDING_UP] = votes.get(MarketState.TRENDING_UP, 0) + 0.6
        elif trend_strength < -2:
            votes[MarketState.TRENDING_DOWN] = votes.get(MarketState.TRENDING_DOWN, 0) + 0.6
            
        # 5. 布林带位置判断
        if bb_position > 0.9:
            votes[MarketState.TRENDING_UP] = votes.get(MarketState.TRENDING_UP, 0) + 0.4
        elif bb_position < 0.1:
            votes[MarketState.TRENDING_DOWN] = votes.get(MarketState.TRENDING_DOWN, 0) + 0.4
        elif 0.3 <= bb_position <= 0.7:
            votes[MarketState.RANGING] = votes.get(MarketState.RANGING, 0) + 0.4
            
        # 投票结果
        if not votes:
            return MarketState.CONSOLIDATING, 0.5
            
        state = max(votes, key=votes.get)
        confidence = min(votes[state] / 1.5, 1.0)  # 归一化到 0-1
        
        return state, confidence
    
    def _get_recommendation(self, state: MarketState, indicators: Dict) -> Tuple[str, str]:
        """根据市场状态给出策略建议"""
        
        if state == MarketState.TRENDING_UP:
            return (
                "趋势上涨，建议持有或做多，设置移动止损",
                "medium"
            )
        elif state == MarketState.TRENDING_DOWN:
            return (
                "趋势下跌，建议空仓或做空，避免抄底",
                "high"
            )
        elif state == MarketState.RANGING:
            return (
                "区间震荡，适合网格交易或区间套利",
                "low"
            )
        elif state == MarketState.VOLATILE:
            return (
                "高波动行情，建议缩小仓位或使用期权对冲",
                "high"
            )
        else:
            return (
                "方向不明，建议观望或小仓位试盘",
                "medium"
            )


# 策略选择器
class StrategySelector:
    """根据市场状态选择合适策略"""
    
    STRATEGY_MAP = {
        MarketState.TRENDING_UP: ['trend_following', 'breakout'],
        MarketState.TRENDING_DOWN: ['short', 'cash'],
        MarketState.RANGING: ['grid', 'range_arbitrage'],
        MarketState.VOLATILE: ['grid', 'short'],
        MarketState.CONSOLIDATING: ['grid', 'wait']
    }
    
    @classmethod
    def select(cls, analysis: MarketAnalysis) -> str:
        """选择最佳策略"""
        strategies = cls.STRATEGY_MAP.get(analysis.state, ['wait'])
        
        # 根据置信度调整
        if analysis.confidence < 0.5:
            return 'wait'  # 置信度低，观望
            
        return strategies[0]  # 返回第一个策略
    
    @classmethod
    def get_strategy_params(cls, strategy: str, market_state: MarketState) -> Dict:
        """获取策略参数（根据市场状态调整）"""
        
        base_params = {
            'grid': {
                'grid_count': 10,
                'position_pct': 0.1,
            },
            'trend_following': {
                'ma_period': 20,
                'stop_loss': 0.03,
                'take_profit': 0.08,
            },
            'short': {
                'leverage': 2,
                'stop_loss': 0.05,
            }
        }
        
        params = base_params.get(strategy, {})
        
        # 根据市场状态调整参数
        if market_state == MarketState.VOLATILE:
            # 高波动：缩小仓位，提高止损
            if 'position_pct' in params:
                params['position_pct'] *= 0.5
            if 'stop_loss' in params:
                params['stop_loss'] *= 0.7
                
        elif market_state == MarketState.RANGING:
            # 震荡市：增加网格密度
            if 'grid_count' in params:
                params['grid_count'] = 15
                
        return params


if __name__ == '__main__':
    # 测试
    import ccxt
    
    # 获取数据
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # 分析
    analyzer = MarketAnalyzer()
    current_price = df['Close'].iloc[-1]
    analysis = analyzer.analyze(df, current_price)
    
    print(f"当前价格: {current_price}")
    print(analysis)
    print(f"\n建议策略: {StrategySelector.select(analysis)}")
