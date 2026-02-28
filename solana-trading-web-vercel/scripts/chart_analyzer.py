#!/usr/bin/env python3
"""
Chart Analysis & Scalp Trading Signal Generator
Uses DexScreener API to analyze price action and identify entry/exit points
"""

import asyncio
import json
import sys
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import aiohttp
from database import ContractDatabase

DEXSCREENER_API = "https://api.dexscreener.com"

@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def wick_top(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def wick_bottom(self) -> float:
        return min(self.open, self.close) - self.low

@dataclass
class SupportResistance:
    level: float
    touches: int
    strength: str  # weak, moderate, strong
    type: str  # support, resistance

@dataclass
class TradingSignal:
    action: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: str  # low, medium, high
    timeframe: str
    reason: str
    risk_reward: float

@dataclass
class ChartAnalysis:
    contract_address: str
    pair_address: str
    timeframe: str
    candles: List[Candle]
    current_price: float
    price_change_24h: float
    
    # Technical levels
    support_levels: List[SupportResistance]
    resistance_levels: List[SupportResistance]
    
    # Moving averages
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    sma_50: Optional[float] = None
    
    # Indicators
    rsi: Optional[float] = None
    trend: str = "neutral"  # bullish, bearish, neutral
    volatility: float = 0.0
    
    # Signals
    signals: List[TradingSignal] = field(default_factory=list)
    scalp_recommendation: str = ""

class ChartAnalyzer:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.db = ContractDatabase()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _dexscreener_call(self, endpoint: str) -> Dict:
        """Make a DexScreener API call."""
        url = f"{DEXSCREENER_API}{endpoint}"
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"  ⚠️ API error: {e}")
            return {}
    
    async def get_pair_address(self, contract_address: str) -> Optional[str]:
        """Get the best pair address for a contract."""
        data = await self._dexscreener_call(f"/token-pairs/v1/solana/{contract_address}")
        
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        
        # Get pair with highest liquidity
        pairs = sorted(data, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
        return pairs[0].get("pairAddress") if pairs else None
    
    async def get_ohlcv_data(self, pair_address: str, timeframe: str = "1h", limit: int = 100) -> List[Candle]:
        """Fetch OHLCV data from DexScreener."""
        # Try to get data from pair page which has recent candles
        data = await self._dexscreener_call(f"/latest/dex/pairs/solana/{pair_address}")
        
        candles = []
        
        if data and "pairs" in data and len(data["pairs"]) > 0:
            pair = data["pairs"][0]
            
            # Get price history if available
            price_history = pair.get("priceHistory", [])
            
            if price_history:
                for i, point in enumerate(price_history):
                    candle = Candle(
                        timestamp=point.get("timestamp", 0),
                        open=float(point.get("open", 0)),
                        high=float(point.get("high", 0)),
                        low=float(point.get("low", 0)),
                        close=float(point.get("close", 0)),
                        volume=float(point.get("volume", 0))
                    )
                    candles.append(candle)
        
        # If no OHLCV data, create synthetic candles from current data
        if not candles:
            # Get current pair data
            data = await self._dexscreener_call(f"/latest/dex/pairs/solana/{pair_address}")
            if data and "pairs" in data and len(data["pairs"]) > 0:
                pair = data["pairs"][0]
                current_price = float(pair.get("priceUsd", 0))
                
                # Create a single candle with current data
                candle = Candle(
                    timestamp=int(datetime.now().timestamp()),
                    open=current_price,
                    high=current_price * 1.02,
                    low=current_price * 0.98,
                    close=current_price,
                    volume=float(pair.get("volume", {}).get("h24", 0))
                )
                candles.append(candle)
        
        return candles
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def calculate_rsi(self, candles: List[Candle], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(candles) < period + 1:
            return None
        
        closes = [c.close for c in candles]
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def find_support_resistance(self, candles: List[Candle], num_levels: int = 3) -> Tuple[List[SupportResistance], List[SupportResistance]]:
        """Find support and resistance levels from recent price action."""
        if len(candles) < 10:
            return [], []
        
        highs = [c.high for c in candles[-20:]]
        lows = [c.low for c in candles[-20:]]
        
        # Find clusters of similar prices
        def find_clusters(prices: List[float], tolerance: float = 0.02) -> List[Tuple[float, int]]:
            clusters = []
            for price in prices:
                found = False
                for i, (level, count) in enumerate(clusters):
                    if abs(price - level) / level < tolerance:
                        clusters[i] = (level + (price - level) * 0.3, count + 1)
                        found = True
                        break
                if not found:
                    clusters.append((price, 1))
            return sorted(clusters, key=lambda x: x[1], reverse=True)
        
        resistance_clusters = find_clusters(highs)
        support_clusters = find_clusters(lows)
        
        resistances = []
        for level, touches in resistance_clusters[:num_levels]:
            strength = "strong" if touches >= 3 else "moderate" if touches >= 2 else "weak"
            resistances.append(SupportResistance(level, touches, strength, "resistance"))
        
        supports = []
        for level, touches in support_clusters[:num_levels]:
            strength = "strong" if touches >= 3 else "moderate" if touches >= 2 else "weak"
            supports.append(SupportResistance(level, touches, strength, "support"))
        
        return supports, resistances
    
    def determine_trend(self, candles: List[Candle], ema_9: float, ema_21: float) -> str:
        """Determine trend based on EMAs and price action."""
        if not candles or ema_9 is None or ema_21 is None:
            return "neutral"
        
        current_price = candles[-1].close
        
        # EMA crossover
        if ema_9 > ema_21 and current_price > ema_9:
            return "bullish"
        elif ema_9 < ema_21 and current_price < ema_9:
            return "bearish"
        
        # Check recent candles
        recent_candles = candles[-5:]
        bullish_count = sum(1 for c in recent_candles if c.is_bullish)
        bearish_count = sum(1 for c in recent_candles if c.is_bearish)
        
        if bullish_count >= 3:
            return "bullish"
        elif bearish_count >= 3:
            return "bearish"
        
        return "neutral"
    
    def calculate_volatility(self, candles: List[Candle]) -> float:
        """Calculate price volatility as percentage."""
        if len(candles) < 2:
            return 0.0
        
        closes = [c.close for c in candles]
        avg_price = sum(closes) / len(closes)
        
        if avg_price == 0:
            return 0.0
        
        variance = sum((c - avg_price) ** 2 for c in closes) / len(closes)
        std_dev = variance ** 0.5
        
        return (std_dev / avg_price) * 100
    
    def generate_scalp_signals(self, analysis: ChartAnalysis, risk_score: int) -> List[TradingSignal]:
        """Generate scalp trading signals based on technical analysis and risk score."""
        signals = []
        
        if not analysis.candles:
            return signals
        
        current_price = analysis.current_price
        current_candle = analysis.candles[-1]
        
        # Adjust position sizing based on risk score
        risk_multiplier = 1.0
        if risk_score <= 30:
            risk_multiplier = 1.0  # Can take larger positions
        elif risk_score <= 40:
            risk_multiplier = 0.7  # Medium positions
        else:
            risk_multiplier = 0.4  # Small positions only
        
        # Check RSI for overbought/oversold
        if analysis.rsi is not None:
            if analysis.rsi < 30:
                # Oversold - potential long
                stop_loss = current_price * 0.97
                take_profit = current_price * 1.04
                
                signals.append(TradingSignal(
                    action="BUY",
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence="medium" if risk_score <= 35 else "low",
                    timeframe="scalp",
                    reason=f"RSI oversold ({analysis.rsi:.1f}). Potential bounce from support.",
                    risk_reward=(take_profit - current_price) / (current_price - stop_loss)
                ))
            
            elif analysis.rsi > 70:
                # Overbought - potential short or avoid
                signals.append(TradingSignal(
                    action="HOLD",
                    entry_price=current_price,
                    stop_loss=current_price * 1.03,
                    take_profit=current_price * 0.95,
                    confidence="low",
                    timeframe="scalp",
                    reason=f"RSI overbought ({analysis.rsi:.1f}). Wait for pullback.",
                    risk_reward=0
                ))
        
        # Support/Resistance bounce plays
        for support in analysis.support_levels[:2]:
            if abs(current_price - support.level) / current_price < 0.02:
                # Price near support
                stop_loss = support.level * 0.98
                take_profit = current_price * 1.03
                
                signals.append(TradingSignal(
                    action="BUY",
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence="medium" if support.strength == "strong" else "low",
                    timeframe="scalp",
                    reason=f"Bounce from {support.strength} support at ${support.level:.6f}",
                    risk_reward=(take_profit - current_price) / (current_price - stop_loss)
                ))
        
        for resistance in analysis.resistance_levels[:2]:
            if abs(current_price - resistance.level) / current_price < 0.02:
                # Price near resistance
                stop_loss = resistance.level * 1.02
                take_profit = current_price * 0.97
                
                signals.append(TradingSignal(
                    action="SELL" if risk_score <= 35 else "HOLD",
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence="medium" if resistance.strength == "strong" else "low",
                    timeframe="scalp",
                    reason=f"Rejection from {resistance.strength} resistance at ${resistance.level:.6f}",
                    risk_reward=(current_price - take_profit) / (stop_loss - current_price)
                ))
        
        # EMA crossover signals
        if analysis.ema_9 and analysis.ema_21:
            if analysis.ema_9 > analysis.ema_21 * 1.005:
                # Golden cross - bullish
                if not any(s.action == "BUY" for s in signals):
                    stop_loss = current_price * 0.96
                    take_profit = current_price * 1.05
                    
                    signals.append(TradingSignal(
                        action="BUY",
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence="medium",
                        timeframe="scalp",
                        reason="EMA9 above EMA21 - short term bullish momentum",
                        risk_reward=(take_profit - current_price) / (current_price - stop_loss)
                    ))
            elif analysis.ema_9 < analysis.ema_21 * 0.995:
                # Death cross - bearish
                if not any(s.action == "SELL" for s in signals):
                    signals.append(TradingSignal(
                        action="HOLD",
                        entry_price=current_price,
                        stop_loss=current_price * 1.04,
                        take_profit=current_price * 0.94,
                        confidence="medium",
                        timeframe="scalp",
                        reason="EMA9 below EMA21 - bearish momentum, wait for better entry",
                        risk_reward=0
                    ))
        
        # If no signals generated, provide a default based on trend
        if not signals:
            if analysis.trend == "bullish" and risk_score <= 35:
                stop_loss = current_price * 0.95
                take_profit = current_price * 1.06
                
                signals.append(TradingSignal(
                    action="BUY",
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence="low",
                    timeframe="scalp",
                    reason="Bullish trend continuation play",
                    risk_reward=(take_profit - current_price) / (current_price - stop_loss)
                ))
            else:
                signals.append(TradingSignal(
                    action="WAIT",
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    confidence="low",
                    timeframe="scalp",
                    reason="No clear setup. Wait for better entry.",
                    risk_reward=0
                ))
        
        return signals
    
    async def analyze_contract(self, contract_address: str) -> ChartAnalysis:
        """Perform full chart analysis for a contract."""
        print(f"\n📈 Analyzing chart for: {contract_address[:20]}...")
        
        # Get pair address
        pair_address = await self.get_pair_address(contract_address)
        if not pair_address:
            print("  ❌ No trading pair found")
            return ChartAnalysis(
                contract_address=contract_address,
                pair_address="",
                timeframe="1h",
                candles=[],
                current_price=0,
                support_levels=[],
                resistance_levels=[]
            )
        
        # Get OHLCV data
        candles = await self.get_ohlcv_data(pair_address, "1h")
        
        if not candles:
            print("  ❌ No chart data available")
            return ChartAnalysis(
                contract_address=contract_address,
                pair_address=pair_address,
                timeframe="1h",
                candles=[],
                current_price=0,
                support_levels=[],
                resistance_levels=[]
            )
        
        current_price = candles[-1].close
        
        # Get contract data from database
        db_data = self.db.get_analysis(contract_address)
        price_change_24h = db_data.get("price_change_24h", 0) if db_data else 0
        risk_score = db_data.get("overall_risk_score", 50) if db_data else 50
        
        # Calculate indicators
        closes = [c.close for c in candles]
        ema_9 = self.calculate_ema(closes, 9)
        ema_21 = self.calculate_ema(closes, 21)
        sma_50 = self.calculate_sma(closes, 50)
        rsi = self.calculate_rsi(candles)
        
        # Find support/resistance
        supports, resistances = self.find_support_resistance(candles)
        
        # Determine trend
        trend = self.determine_trend(candles, ema_9, ema_21)
        
        # Calculate volatility
        volatility = self.calculate_volatility(candles)
        
        # Create analysis object
        analysis = ChartAnalysis(
            contract_address=contract_address,
            pair_address=pair_address,
            timeframe="1h",
            candles=candles,
            current_price=current_price,
            price_change_24h=price_change_24h,
            support_levels=supports,
            resistance_levels=resistances,
            ema_9=ema_9,
            ema_21=ema_21,
            sma_50=sma_50,
            rsi=rsi,
            trend=trend,
            volatility=volatility
        )
        
        # Generate signals
        analysis.signals = self.generate_scalp_signals(analysis, risk_score)
        
        # Generate recommendation
        analysis.scalp_recommendation = self._generate_recommendation(analysis, risk_score)
        
        return analysis
    
    def _generate_recommendation(self, analysis: ChartAnalysis, risk_score: int) -> str:
        """Generate overall scalp trading recommendation."""
        if risk_score > 40:
            return "AVOID - Risk too high for scalp trading"
        
        if analysis.volatility > 50:
            return "HIGH VOLATILITY - Use smaller position sizes"
        
        if analysis.trend == "bullish":
            return "FAVORABLE - Bullish trend, look for long entries"
        elif analysis.trend == "bearish":
            return "CAUTION - Bearish trend, wait for reversal or short"
        else:
            return "NEUTRAL - Range bound, trade support/resistance"

def print_chart_analysis(analysis: ChartAnalysis, risk_score: int, risk_rating: str):
    """Print formatted chart analysis."""
    print("\n" + "=" * 70)
    print(f"📊 CHART ANALYSIS - {analysis.contract_address[:20]}...")
    print("=" * 70)
    
    print(f"\n💰 Current Price: ${analysis.current_price:.6f}")
    print(f"📈 24h Change: {analysis.price_change_24h:+.2f}%")
    print(f"📊 Risk Score: {risk_score}/100 ({risk_rating})")
    print(f"🎯 Trend: {analysis.trend.upper()}")
    print(f"📉 Volatility: {analysis.volatility:.2f}%")
    
    if analysis.rsi is not None:
        rsi_status = "OVERSOLD" if analysis.rsi < 30 else "OVERBOUGHT" if analysis.rsi > 70 else "NEUTRAL"
        print(f"📊 RSI: {analysis.rsi:.1f} ({rsi_status})")
    
    if analysis.ema_9:
        print(f"\n📈 Moving Averages:")
        print(f"  EMA9:  ${analysis.ema_9:.6f}")
        if analysis.ema_21:
            print(f"  EMA21: ${analysis.ema_21:.6f}")
            cross = "BULLISH" if analysis.ema_9 > analysis.ema_21 else "BEARISH"
            print(f"  Signal: {cross} crossover")
        if analysis.sma_50:
            print(f"  SMA50: ${analysis.sma_50:.6f}")
    
    if analysis.support_levels:
        print(f"\n🟢 Support Levels:")
        for s in analysis.support_levels[:3]:
            print(f"  ${s.level:.6f} ({s.strength}, {s.touches} touches)")
    
    if analysis.resistance_levels:
        print(f"\n🔴 Resistance Levels:")
        for r in analysis.resistance_levels[:3]:
            print(f"  ${r.level:.6f} ({r.strength}, {r.touches} touches)")
    
    if analysis.signals:
        print(f"\n🎯 TRADING SIGNALS:")
        for i, signal in enumerate(analysis.signals[:3], 1):
            print(f"\n  Signal #{i}: {signal.action}")
            print(f"    Entry: ${signal.entry_price:.6f}")
            if signal.stop_loss > 0:
                print(f"    Stop Loss: ${signal.stop_loss:.6f} ({((signal.stop_loss/signal.entry_price)-1)*100:+.1f}%)")
            if signal.take_profit > 0:
                print(f"    Take Profit: ${signal.take_profit:.6f} ({((signal.take_profit/signal.entry_price)-1)*100:+.1f}%)")
            print(f"    R:R Ratio: 1:{signal.risk_reward:.1f}" if signal.risk_reward > 0 else "    R:R Ratio: N/A")
            print(f"    Confidence: {signal.confidence.upper()}")
            print(f"    Reason: {signal.reason}")
    
    print(f"\n💡 SCALP RECOMMENDATION:")
    print(f"  {analysis.scalp_recommendation}")
    
    # Risk-adjusted position sizing
    print(f"\n📋 RISK-ADJUSTED POSITION SIZING:")
    if risk_score <= 30:
        print(f"  ✅ Low Risk - Can use standard position size (2-3% of portfolio)")
    elif risk_score <= 40:
        print(f"  ⚠️  Medium Risk - Reduce position (1-2% of portfolio)")
    else:
        print(f"  🔴 High Risk - Minimal position only (0.5-1% of portfolio)")
    
    print("=" * 70)

async def analyze_multiple(contracts: List[str]):
    """Analyze multiple contracts and compare."""
    async with ChartAnalyzer() as analyzer:
        analyses = []
        
        for contract in contracts:
            analysis = await analyzer.analyze_contract(contract)
            
            # Get risk data from database
            db_data = analyzer.db.get_analysis(contract)
            risk_score = db_data.get("overall_risk_score", 50) if db_data else 50
            risk_rating = db_data.get("risk_rating", "UNKNOWN") if db_data else "UNKNOWN"
            
            analyses.append((analysis, risk_score, risk_rating))
            print_chart_analysis(analysis, risk_score, risk_rating)
        
        # Print comparison summary
        print("\n" + "=" * 100)
        print("📊 SCALP TRADING COMPARISON - ALL CONTRACTS")
        print("=" * 100)
        print(f"{'Contract':<24}{'Price':<12}{'Risk':<8}{'Trend':<10}{'RSI':<8}{'Volatility':<12}{'Best Signal':<15}")
        print("-" * 100)
        
        for analysis, risk_score, risk_rating in analyses:
            short_addr = f"{analysis.contract_address[:20]}..."
            price = f"${analysis.current_price:.6f}"
            risk = f"{risk_score}/100"
            trend = analysis.trend.upper()
            rsi = f"{analysis.rsi:.0f}" if analysis.rsi else "N/A"
            vol = f"{analysis.volatility:.1f}%"
            
            best_signal = "WAIT"
            if analysis.signals:
                buy_signals = [s for s in analysis.signals if s.action == "BUY"]
                if buy_signals:
                    best_signal = f"BUY ({buy_signals[0].confidence})"
            
            print(f"{short_addr:<24}{price:<12}{risk:<8}{trend:<10}{rsi:<8}{vol:<12}{best_signal:<15}")
        
        print("=" * 100)
        
        # Best scalp opportunity
        print("\n🏆 TOP SCALP OPPORTUNITIES:")
        
        # Sort by risk score and best signals
        ranked = []
        for analysis, risk_score, risk_rating in analyses:
            has_buy = any(s.action == "BUY" for s in analysis.signals)
            confidence_score = 0
            if has_buy:
                buy_signal = [s for s in analysis.signals if s.action == "BUY"][0]
                confidence_score = 3 if buy_signal.confidence == "high" else 2 if buy_signal.confidence == "medium" else 1
            
            # Lower risk score is better, higher confidence is better
            score = (100 - risk_score) + (confidence_score * 10)
            ranked.append((analysis, risk_score, risk_rating, score))
        
        ranked.sort(key=lambda x: x[3], reverse=True)
        
        for i, (analysis, risk_score, risk_rating, score) in enumerate(ranked[:3], 1):
            buy_signals = [s for s in analysis.signals if s.action == "BUY"]
            if buy_signals:
                signal = buy_signals[0]
                print(f"\n  {i}. {analysis.contract_address[:20]}...")
                print(f"     Risk: {risk_score}/100 | Entry: ${signal.entry_price:.6f}")
                print(f"     Target: ${signal.take_profit:.6f} | Stop: ${signal.stop_loss:.6f}")
                print(f"     R:R = 1:{signal.risk_reward:.1f}")

async def main():
    """Main entry point."""
    # Default: analyze all contracts in database
    db = ContractDatabase()
    contracts = [c["contract_address"] for c in db.get_all_contracts(limit=20)]
    
    if not contracts:
        print("No contracts in database. Please run analyze_contract.py first.")
        return
    
    print(f"📊 Analyzing {len(contracts)} contracts for scalp opportunities...")
    await analyze_multiple(contracts)

if __name__ == "__main__":
    asyncio.run(main())
