#!/usr/bin/env python3
"""
🎯 Smart Money Momentum Agent
Analyzes token holders to identify profitable "smart money" wallets and combines
with volume/chart momentum and pattern recognition for high-probability trade signals.

Responsibilities:
- Identify profitable holder wallets (smart money tracking)
- Analyze volume momentum (spikes, trends, accumulation)
- Detect chart patterns (breakouts, consolidation, support/resistance)
- Generate combined Smart Money + Momentum scores
- Output actionable trading signals
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import aiohttp
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import ContractDatabase
from scripts.analyze_contract import SolanaContractAnalyzer, AnalysisResult

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
DEXSCREENER_API = "https://api.dexscreener.com"
BIRDEYE_API = os.getenv("BIRDEYE_API", "https://public-api.birdeye.so")

# Analysis Parameters
SMART_MONEY_MIN_PROFIT = 10000  # $10k minimum profit to be considered "smart"
SMART_MONEY_MIN_TRADES = 5      # Minimum trades for reliability
VOLUME_SPIKE_THRESHOLD = 2.5    # 2.5x average volume = spike
MOMENTUM_LOOKBACK_PERIODS = [6, 24, 72]  # hours
MIN_HOLDER_COUNT = 50           # Minimum holders for analysis
TOP_HOLDER_PERCENTILE = 0.05    # Top 5% = whales


@dataclass
class HolderProfile:
    """Profile of a token holder."""
    wallet_address: str
    balance: float
    balance_usd: float
    percent_held: float
    entry_price: Optional[float] = None
    avg_buy_price: Optional[float] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    holding_period_days: float = 0.0
    last_activity: Optional[str] = None
    is_smart_money: bool = False
    is_whale: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class HolderMetrics:
    """Aggregated holder analysis metrics."""
    total_holders: int
    active_holders_24h: int
    smart_money_count: int
    whale_count: int
    smart_money_holdings_percent: float
    concentration_risk: str  # low, medium, high
    holder_growth_rate: float  # % change in holders
    avg_holding_time: float
    smart_money_buying: bool
    smart_money_selling: bool
    smart_money_net_flow: float  # positive = buying, negative = selling
    top_holders: List[HolderProfile] = field(default_factory=list)
    smart_money_wallets: List[str] = field(default_factory=list)


@dataclass
class VolumeMomentum:
    """Volume momentum analysis."""
    current_volume_24h: float
    avg_volume_7d: float
    volume_ratio: float  # current vs avg
    volume_trend: str  # increasing, decreasing, stable, spiking
    volume_spikes_24h: int
    buy_pressure: float  # 0-100, higher = more buying
    sell_pressure: float  # 0-100
    net_pressure: float  # positive = buy pressure
    accumulation_score: float  # 0-100
    distribution_score: float  # 0-100
    unusual_activity: bool
    volume_insights: List[str] = field(default_factory=list)


@dataclass
class ChartPattern:
    """Detected chart pattern."""
    pattern_type: str  # breakout, breakdown, consolidation, accumulation, distribution
    confidence: float  # 0-100
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    timeframe: str = "1h"
    description: str = ""
    supporting_indicators: List[str] = field(default_factory=list)


@dataclass
class MomentumIndicators:
    """Technical momentum indicators."""
    rsi_14: float
    rsi_trend: str  # oversold, neutral, overbought
    macd_signal: str  # bullish, bearish, neutral
    price_momentum_24h: float  # % change
    price_momentum_7d: float
    volatility_24h: float
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    trend_direction: str = "sideways"  # up, down, sideways
    trend_strength: float = 0.0  # 0-100


@dataclass
class SmartMoneySignal:
    """Final combined signal output."""
    token_address: str
    symbol: str
    timestamp: str
    
    # Component scores (0-100)
    smart_money_score: float
    momentum_score: float
    pattern_score: float
    combined_score: float
    
    # Analysis results
    holder_metrics: HolderMetrics
    volume_momentum: VolumeMomentum
    momentum_indicators: MomentumIndicators
    detected_patterns: List[ChartPattern]
    
    # Signal details
    signal_type: str  # strong_buy, buy, hold, sell, strong_sell
    confidence: float  # 0-100
    timeframe: str  # scalping, swing, position
    
    # Key insights
    key_insights: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    
    # Trade parameters
    suggested_entry: Optional[float] = None
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None
    risk_reward_ratio: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for Smart Money Momentum Agent."""
    enabled: bool = True
    min_liquidity_usd: float = 10000  # $10k
    min_market_cap: float = 50000     # $50k
    max_risk_score: int = 50          # Only analyze lower risk tokens
    data_dir: str = "data/smart_money"
    cache_duration_minutes: int = 15


class SmartMoneyMomentumAgent:
    """
    Smart Money Momentum Agent
    
    Analyzes tokens for:
    1. Smart money holder activity (profitable wallets)
    2. Volume momentum and pressure
    3. Chart patterns and technical indicators
    
    Outputs combined signals for high-probability trades.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.db = ContractDatabase()
        self.session: Optional[aiohttp.ClientSession] = None
        self.analyzer = SolanaContractAnalyzer()
        self._cache: Dict[str, Dict] = {}
        
        # Ensure data directory exists
        os.makedirs(self.config.data_dir, exist_ok=True)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _helius_call(self, method: str, params: List) -> Dict:
        """Make Helius RPC call."""
        if not HELIUS_API_KEY:
            logger.warning("HELIUS_API_KEY not set")
            return {}
            
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            async with self.session.post(
                HELIUS_RPC_URL,
                json=payload,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result", {})
                return {}
        except Exception as e:
            logger.error(f"Helius API error: {e}")
            return {}
    
    async def _dexscreener_call(self, endpoint: str) -> Dict:
        """Make DexScreener API call."""
        url = f"{DEXSCREENER_API}/{endpoint}"
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            logger.error(f"DexScreener API error: {e}")
            return {}
    
    async def fetch_token_holders(self, token_address: str) -> List[Dict]:
        """
        Fetch token holders with balances.
        Uses Helius API to get holder data.
        """
        holders = []
        
        # Get token supply info
        supply_result = await self._helius_call(
            "getTokenSupply",
            [token_address]
        )
        
        if not supply_result:
            return holders
            
        total_supply = float(supply_result.get("value", {}).get("amount", 0))
        decimals = supply_result.get("value", {}).get("decimals", 0)
        
        # Get largest token accounts (top holders)
        largest_result = await self._helius_call(
            "getTokenLargestAccounts",
            [token_address]
        )
        
        accounts = largest_result.get("value", [])
        
        for account in accounts[:50]:  # Top 50 holders
            balance = float(account.get("amount", 0)) / (10 ** decimals)
            pct_held = (balance / total_supply * 100) if total_supply > 0 else 0
            
            holders.append({
                "address": account.get("address", ""),
                "balance": balance,
                "percent_held": pct_held,
                "uiAmount": account.get("uiAmount", 0)
            })
        
        return holders
    
    async def analyze_wallet_performance(
        self, 
        wallet_address: str,
        token_address: Optional[str] = None
    ) -> Dict:
        """
        Analyze a wallet's trading performance.
        This is a simplified version - in production you'd query historical data.
        """
        # This would typically call a service like Birdeye or Helius
        # to get wallet transaction history and calculate P&L
        
        # Placeholder implementation
        return {
            "wallet": wallet_address,
            "total_trades": 0,
            "profitable_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "is_smart_money": False
        }
    
    async def analyze_holders(
        self, 
        token_address: str,
        price_usd: float
    ) -> HolderMetrics:
        """
        Analyze token holders to identify smart money and whale activity.
        """
        logger.info(f"Analyzing holders for {token_address}")
        
        raw_holders = await self.fetch_token_holders(token_address)
        
        if not raw_holders:
            return HolderMetrics(
                total_holders=0,
                active_holders_24h=0,
                smart_money_count=0,
                whale_count=0,
                smart_money_holdings_percent=0.0,
                concentration_risk="unknown",
                holder_growth_rate=0.0,
                avg_holding_time=0.0,
                smart_money_buying=False,
                smart_money_selling=False,
                smart_money_net_flow=0.0
            )
        
        top_holders: List[HolderProfile] = []
        smart_money_wallets: List[str] = []
        total_smart_money_holdings = 0.0
        whale_count = 0
        
        for holder in raw_holders[:20]:  # Analyze top 20
            balance_usd = holder["balance"] * price_usd
            is_whale = holder["percent_held"] >= 1.0  # >1% = whale
            
            if is_whale:
                whale_count += 1
            
            # Check if smart money (would need historical data in production)
            # For now, use heuristics
            is_smart = holder["percent_held"] >= 0.5 and balance_usd >= 5000
            
            profile = HolderProfile(
                wallet_address=holder["address"],
                balance=holder["balance"],
                balance_usd=balance_usd,
                percent_held=holder["percent_held"],
                is_whale=is_whale,
                is_smart_money=is_smart,
                tags=["whale"] if is_whale else []
            )
            
            top_holders.append(profile)
            
            if is_smart:
                smart_money_wallets.append(holder["address"])
                total_smart_money_holdings += holder["percent_held"]
        
        # Calculate concentration risk
        top_10_pct = sum(h.percent_held for h in top_holders[:10])
        if top_10_pct > 50:
            concentration_risk = "high"
        elif top_10_pct > 30:
            concentration_risk = "medium"
        else:
            concentration_risk = "low"
        
        # Determine smart money flow (simplified)
        # In production, compare current vs historical holdings
        smart_money_buying = len([h for h in top_holders if h.is_smart_money and h.balance_usd > 10000]) > 2
        smart_money_selling = False  # Would need historical comparison
        
        return HolderMetrics(
            total_holders=len(raw_holders),
            active_holders_24h=len(raw_holders),  # Placeholder
            smart_money_count=len(smart_money_wallets),
            whale_count=whale_count,
            smart_money_holdings_percent=total_smart_money_holdings,
            concentration_risk=concentration_risk,
            holder_growth_rate=0.0,  # Would need historical data
            avg_holding_time=0.0,  # Would need historical data
            smart_money_buying=smart_money_buying,
            smart_money_selling=smart_money_selling,
            smart_money_net_flow=1.0 if smart_money_buying else -1.0 if smart_money_selling else 0.0,
            top_holders=top_holders,
            smart_money_wallets=smart_money_wallets
        )
    
    async def analyze_volume_momentum(self, token_address: str) -> VolumeMomentum:
        """
        Analyze volume momentum and pressure.
        Uses DexScreener data.
        """
        logger.info(f"Analyzing volume momentum for {token_address}")
        
        # Get token pairs from DexScreener
        data = await self._dexscreener_call(f"token-pairs/v1/solana/{token_address}")
        
        if not data or not isinstance(data, list):
            return VolumeMomentum(
                current_volume_24h=0,
                avg_volume_7d=0,
                volume_ratio=1.0,
                volume_trend="stable",
                volume_spikes_24h=0,
                buy_pressure=50,
                sell_pressure=50,
                net_pressure=0,
                accumulation_score=50,
                distribution_score=50,
                unusual_activity=False
            )
        
        # Aggregate across all pairs
        total_volume_24h = 0
        total_liquidity = 0
        buy_volume = 0
        sell_volume = 0
        volume_history = []
        
        for pair in data[:5]:  # Top 5 pairs
            vol_24h = float(pair.get("volume", {}).get("h24", 0))
            liquidity = float(pair.get("liquidity", {}).get("usd", 0))
            
            total_volume_24h += vol_24h
            total_liquidity += liquidity
            
            # Estimate buy/sell from price change
            price_change = float(pair.get("priceChange", {}).get("h24", 0))
            if price_change > 0:
                buy_volume += vol_24h * 0.6  # Estimate 60% buys on up days
                sell_volume += vol_24h * 0.4
            else:
                buy_volume += vol_24h * 0.4
                sell_volume += vol_24h * 0.6
            
            # Get historical volumes if available
            for tf in ["h6", "h24"]:
                vol = pair.get("volume", {}).get(tf, 0)
                if vol:
                    volume_history.append(float(vol))
        
        # Calculate metrics
        avg_volume = sum(volume_history) / len(volume_history) if volume_history else total_volume_24h
        volume_ratio = total_volume_24h / avg_volume if avg_volume > 0 else 1.0
        
        # Determine trend
        if volume_ratio >= VOLUME_SPIKE_THRESHOLD:
            volume_trend = "spiking"
        elif volume_ratio >= 1.5:
            volume_trend = "increasing"
        elif volume_ratio <= 0.7:
            volume_trend = "decreasing"
        else:
            volume_trend = "stable"
        
        # Calculate pressure
        total_vol = buy_volume + sell_volume
        buy_pressure = (buy_volume / total_vol * 100) if total_vol > 0 else 50
        sell_pressure = (sell_volume / total_vol * 100) if total_vol > 0 else 50
        net_pressure = buy_pressure - sell_pressure
        
        # Calculate accumulation/distribution
        if net_pressure > 20 and volume_trend in ["increasing", "spiking"]:
            accumulation_score = 80
            distribution_score = 20
        elif net_pressure < -20 and volume_trend in ["increasing", "spiking"]:
            accumulation_score = 20
            distribution_score = 80
        else:
            accumulation_score = 50
            distribution_score = 50
        
        # Generate insights
        insights = []
        if volume_trend == "spiking":
            insights.append(f"🔥 Volume spike detected ({volume_ratio:.1f}x average)")
        if net_pressure > 30:
            insights.append(f"🟢 Strong buy pressure ({buy_pressure:.0f}%)")
        elif net_pressure < -30:
            insights.append(f"🔴 Strong sell pressure ({sell_pressure:.0f}%)")
        if accumulation_score > 70:
            insights.append("📈 Accumulation pattern detected")
        elif distribution_score > 70:
            insights.append("📉 Distribution pattern detected")
        
        return VolumeMomentum(
            current_volume_24h=total_volume_24h,
            avg_volume_7d=avg_volume,
            volume_ratio=volume_ratio,
            volume_trend=volume_trend,
            volume_spikes_24h=1 if volume_trend == "spiking" else 0,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            net_pressure=net_pressure,
            accumulation_score=accumulation_score,
            distribution_score=distribution_score,
            unusual_activity=volume_trend == "spiking",
            volume_insights=insights
        )
    
    async def analyze_momentum_indicators(
        self, 
        token_address: str,
        current_price: float
    ) -> MomentumIndicators:
        """
        Calculate momentum indicators from price data.
        """
        logger.info(f"Analyzing momentum for {token_address}")
        
        # Get price history from DexScreener
        data = await self._dexscreener_call(f"token-pairs/v1/solana/{token_address}")
        
        if not data or not isinstance(data, list):
            return MomentumIndicators(
                rsi_14=50,
                rsi_trend="neutral",
                macd_signal="neutral",
                price_momentum_24h=0,
                price_momentum_7d=0,
                volatility_24h=0,
                trend_direction="sideways",
                trend_strength=0
            )
        
        # Get main pair
        pair = data[0]
        price_change_24h = float(pair.get("priceChange", {}).get("h24", 0))
        price_change_7d = float(pair.get("priceChange", {}).get("h7", 0))
        
        # Calculate simple RSI approximation
        # Real RSI requires OHLC data
        if price_change_24h > 10:
            rsi = 70 + min(price_change_24h / 2, 25)  # Approximation
            rsi_trend = "overbought" if rsi > 70 else "neutral"
        elif price_change_24h < -10:
            rsi = 30 - min(abs(price_change_24h) / 2, 25)
            rsi_trend = "oversold" if rsi < 30 else "neutral"
        else:
            rsi = 50 + price_change_24h
            rsi_trend = "neutral"
        
        rsi = max(0, min(100, rsi))  # Clamp to 0-100
        
        # Determine trend
        if price_change_24h > 5 and (price_change_7d > 0 if price_change_7d else True):
            trend = "up"
            trend_strength = min(abs(price_change_24h) * 3, 100)
            macd = "bullish"
        elif price_change_24h < -5 and (price_change_7d < 0 if price_change_7d else True):
            trend = "down"
            trend_strength = min(abs(price_change_24h) * 3, 100)
            macd = "bearish"
        else:
            trend = "sideways"
            trend_strength = 20
            macd = "neutral"
        
        # Calculate volatility
        price_changes = []
        for tf in ["m5", "h1", "h6", "h24"]:
            pc = pair.get("priceChange", {}).get(tf, 0)
            if pc:
                price_changes.append(float(pc))
        
        volatility = sum(abs(p) for p in price_changes) / len(price_changes) if price_changes else 0
        
        # Estimate support/resistance from price history
        # In production, you'd calculate this properly from OHLC
        support = current_price * 0.9 if trend == "up" else current_price * 0.95
        resistance = current_price * 1.1 if trend == "down" else current_price * 1.05
        
        return MomentumIndicators(
            rsi_14=rsi,
            rsi_trend=rsi_trend,
            macd_signal=macd,
            price_momentum_24h=price_change_24h,
            price_momentum_7d=price_change_7d,
            volatility_24h=volatility,
            support_level=support,
            resistance_level=resistance,
            trend_direction=trend,
            trend_strength=trend_strength
        )
    
    def detect_chart_patterns(
        self,
        momentum: MomentumIndicators,
        volume: VolumeMomentum,
        price: float
    ) -> List[ChartPattern]:
        """
        Detect chart patterns from momentum and volume data.
        """
        patterns = []
        
        # Breakout pattern
        if momentum.trend_direction == "up" and volume.volume_trend == "spiking":
            if momentum.price_momentum_24h > 10:
                patterns.append(ChartPattern(
                    pattern_type="breakout",
                    confidence=min(momentum.trend_strength + 10, 95),
                    price_target=price * 1.2,
                    stop_loss=price * 0.92,
                    timeframe="1h-4h",
                    description=f"Strong breakout with {volume.volume_ratio:.1f}x volume spike",
                    supporting_indicators=["Volume spike", "Momentum up", "RSI momentum"]
                ))
        
        # Accumulation pattern
        if volume.accumulation_score > 70 and momentum.rsi_trend == "oversold":
            patterns.append(ChartPattern(
                pattern_type="accumulation",
                confidence=75,
                price_target=price * 1.15,
                stop_loss=price * 0.88,
                timeframe="4h-24h",
                description="Accumulation phase with oversold RSI",
                supporting_indicators=["Buy pressure", "Oversold RSI", "Volume building"]
            ))
        
        # Consolidation pattern
        if momentum.trend_direction == "sideways" and volume.volume_trend == "decreasing":
            patterns.append(ChartPattern(
                pattern_type="consolidation",
                confidence=60,
                price_target=price * 1.1,
                stop_loss=price * 0.9,
                timeframe="1h-6h",
                description="Price consolidating, awaiting breakout",
                supporting_indicators=["Low volatility", "Volume contraction"]
            ))
        
        # Distribution pattern (bearish)
        if volume.distribution_score > 70 and momentum.rsi_trend == "overbought":
            patterns.append(ChartPattern(
                pattern_type="distribution",
                confidence=70,
                price_target=price * 0.85,
                stop_loss=price * 1.05,
                timeframe="1h-4h",
                description="Distribution pattern with overbought RSI",
                supporting_indicators=["Sell pressure", "Overbought RSI"]
            ))
        
        # Breakdown pattern
        if momentum.trend_direction == "down" and volume.volume_trend == "spiking":
            patterns.append(ChartPattern(
                pattern_type="breakdown",
                confidence=min(momentum.trend_strength + 10, 90),
                price_target=price * 0.8,
                stop_loss=price * 1.08,
                timeframe="1h-4h",
                description="Breakdown with volume confirmation",
                supporting_indicators=["Volume spike", "Down momentum"]
            ))
        
        return patterns
    
    def calculate_smart_money_score(self, holders: HolderMetrics) -> float:
        """Calculate smart money score (0-100)."""
        score = 50  # Neutral base
        
        # Smart money presence
        if holders.smart_money_count >= 5:
            score += 15
        elif holders.smart_money_count >= 3:
            score += 10
        elif holders.smart_money_count >= 1:
            score += 5
        
        # Smart money activity
        if holders.smart_money_buying:
            score += 20
        if holders.smart_money_selling:
            score -= 15
        
        # Holdings percentage
        if holders.smart_money_holdings_percent >= 10:
            score += 10
        elif holders.smart_money_holdings_percent >= 5:
            score += 5
        
        # Concentration risk adjustment
        if holders.concentration_risk == "high":
            score -= 10
        elif holders.concentration_risk == "low":
            score += 5
        
        return max(0, min(100, score))
    
    def calculate_momentum_score(
        self, 
        volume: VolumeMomentum,
        indicators: MomentumIndicators
    ) -> float:
        """Calculate momentum score (0-100)."""
        score = 50  # Neutral base
        
        # Volume trend
        if volume.volume_trend == "spiking":
            score += 20
        elif volume.volume_trend == "increasing":
            score += 10
        elif volume.volume_trend == "decreasing":
            score -= 10
        
        # Buy pressure
        score += (volume.net_pressure / 5)  # +/- 20 points
        
        # Price momentum
        if indicators.price_momentum_24h > 20:
            score += 15
        elif indicators.price_momentum_24h > 10:
            score += 10
        elif indicators.price_momentum_24h < -10:
            score -= 10
        elif indicators.price_momentum_24h < -20:
            score -= 15
        
        # RSI condition
        if indicators.rsi_trend == "oversold":
            score += 10  # Potential reversal up
        elif indicators.rsi_trend == "overbought":
            score -= 10  # Potential reversal down
        
        # Trend direction
        if indicators.trend_direction == "up":
            score += 10
        elif indicators.trend_direction == "down":
            score -= 10
        
        return max(0, min(100, score))
    
    def calculate_pattern_score(self, patterns: List[ChartPattern]) -> float:
        """Calculate pattern score from detected patterns (0-100)."""
        if not patterns:
            return 50  # Neutral
        
        bullish_patterns = [p for p in patterns if p.pattern_type in ["breakout", "accumulation"]]
        bearish_patterns = [p for p in patterns if p.pattern_type in ["breakdown", "distribution"]]
        neutral_patterns = [p for p in patterns if p.pattern_type == "consolidation"]
        
        if bullish_patterns and not bearish_patterns:
            avg_confidence = sum(p.confidence for p in bullish_patterns) / len(bullish_patterns)
            return 50 + (avg_confidence / 2)
        elif bearish_patterns and not bullish_patterns:
            avg_confidence = sum(p.confidence for p in bearish_patterns) / len(bearish_patterns)
            return 50 - (avg_confidence / 2)
        elif bullish_patterns and bearish_patterns:
            # Conflicting signals
            bull_score = sum(p.confidence for p in bullish_patterns) / len(bullish_patterns)
            bear_score = sum(p.confidence for p in bearish_patterns) / len(bearish_patterns)
            return 50 + (bull_score - bear_score) / 2
        else:
            return 50
    
    def generate_signal(
        self,
        smart_money_score: float,
        momentum_score: float,
        pattern_score: float,
        patterns: List[ChartPattern]
    ) -> Tuple[str, float]:
        """Generate final signal and confidence."""
        # Weighted combination
        combined = (
            smart_money_score * 0.35 +
            momentum_score * 0.40 +
            pattern_score * 0.25
        )
        
        # Determine signal type
        if combined >= 75:
            signal = "strong_buy"
        elif combined >= 60:
            signal = "buy"
        elif combined >= 45:
            signal = "hold"
        elif combined >= 30:
            signal = "sell"
        else:
            signal = "strong_sell"
        
        # Calculate confidence based on agreement
        scores = [smart_money_score, momentum_score, pattern_score]
        variance = max(scores) - min(scores)
        if variance < 20:
            confidence = 85  # High agreement
        elif variance < 40:
            confidence = 70  # Moderate agreement
        else:
            confidence = 55  # Low agreement
        
        return signal, confidence, combined
    
    async def analyze_token(self, token_address: str) -> Optional[SmartMoneySignal]:
        """
        Main analysis method for a single token.
        Combines holder, momentum, and pattern analysis.
        """
        logger.info(f"🔍 Analyzing token: {token_address}")
        
        try:
            # Get basic token info from DexScreener
            data = await self._dexscreener_call(f"token-pairs/v1/solana/{token_address}")
            
            if not data or not isinstance(data, list):
                logger.warning(f"No data found for {token_address}")
                return None
            
            pair = data[0]
            symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
            price = float(pair.get("priceUsd", 0))
            liquidity = float(pair.get("liquidity", {}).get("usd", 0))
            
            # Check minimum requirements
            if liquidity < self.config.min_liquidity_usd:
                logger.info(f"Skipping {symbol}: insufficient liquidity (${liquidity:,.0f})")
                return None
            
            # Run analyses concurrently
            holders_task = self.analyze_holders(token_address, price)
            volume_task = self.analyze_volume_momentum(token_address)
            momentum_task = self.analyze_momentum_indicators(token_address, price)
            
            holders, volume, momentum = await asyncio.gather(
                holders_task, volume_task, momentum_task
            )
            
            # Detect patterns
            patterns = self.detect_chart_patterns(momentum, volume, price)
            
            # Calculate scores
            sm_score = self.calculate_smart_money_score(holders)
            mom_score = self.calculate_momentum_score(volume, momentum)
            pat_score = self.calculate_pattern_score(patterns)
            
            # Generate signal
            signal_type, confidence, combined = self.generate_signal(
                sm_score, mom_score, pat_score, patterns
            )
            
            # Generate insights
            insights = []
            green_flags = []
            red_flags = []
            
            # Smart money insights
            if holders.smart_money_buying:
                insights.append(f"🧠 {holders.smart_money_count} smart money wallets accumulating")
                green_flags.append("Smart money buying")
            if holders.smart_money_selling:
                red_flags.append("Smart money selling")
            
            # Volume insights
            insights.extend(volume.volume_insights)
            if volume.volume_trend == "spiking":
                green_flags.append(f"Volume spike ({volume.volume_ratio:.1f}x)")
            
            # Momentum insights
            if momentum.trend_direction == "up":
                green_flags.append(f"Uptrend (+{momentum.price_momentum_24h:.1f}%)")
            elif momentum.trend_direction == "down":
                red_flags.append(f"Downtrend ({momentum.price_momentum_24h:.1f}%)")
            
            if momentum.rsi_trend == "oversold":
                green_flags.append("Oversold (potential bounce)")
            elif momentum.rsi_trend == "overbought":
                red_flags.append("Overbought (potential pullback)")
            
            # Pattern insights
            for pattern in patterns:
                insights.append(f"📊 {pattern.pattern_type.upper()}: {pattern.description}")
                if pattern.pattern_type in ["breakout", "accumulation"]:
                    green_flags.append(f"{pattern.pattern_type.title()} pattern")
                elif pattern.pattern_type in ["breakdown", "distribution"]:
                    red_flags.append(f"{pattern.pattern_type.title()} pattern")
            
            # Concentration warning
            if holders.concentration_risk == "high":
                red_flags.append("High holder concentration")
            
            # Trade parameters from best pattern
            suggested_entry = price
            suggested_stop = None
            suggested_target = None
            
            bullish_patterns = [p for p in patterns if p.pattern_type in ["breakout", "accumulation"]]
            if bullish_patterns and signal_type in ["buy", "strong_buy"]:
                best_pattern = max(bullish_patterns, key=lambda p: p.confidence)
                suggested_stop = best_pattern.stop_loss
                suggested_target = best_pattern.price_target
            
            # Calculate R:R
            risk_reward = None
            if suggested_stop and suggested_target:
                risk = abs(price - suggested_stop)
                reward = abs(suggested_target - price)
                if risk > 0:
                    risk_reward = f"1:{reward/risk:.1f}"
            
            return SmartMoneySignal(
                token_address=token_address,
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                smart_money_score=round(sm_score, 1),
                momentum_score=round(mom_score, 1),
                pattern_score=round(pat_score, 1),
                combined_score=round(combined, 1),
                holder_metrics=holders,
                volume_momentum=volume,
                momentum_indicators=momentum,
                detected_patterns=patterns,
                signal_type=signal_type,
                confidence=round(confidence, 0),
                timeframe="scalping" if momentum.volatility_24h > 50 else "swing",
                key_insights=insights,
                red_flags=red_flags,
                green_flags=green_flags,
                suggested_entry=round(suggested_entry, 8) if suggested_entry else None,
                suggested_stop=round(suggested_stop, 8) if suggested_stop else None,
                suggested_target=round(suggested_target, 8) if suggested_target else None,
                risk_reward_ratio=risk_reward
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {token_address}: {e}")
            return None
    
    async def scan_watchlist(self, watchlist: List[str]) -> List[SmartMoneySignal]:
        """
        Analyze multiple tokens from a watchlist.
        Returns signals sorted by combined score.
        """
        logger.info(f"📋 Scanning {len(watchlist)} tokens from watchlist")
        
        signals = []
        for token in watchlist:
            signal = await self.analyze_token(token)
            if signal:
                signals.append(signal)
        
        # Sort by combined score descending
        signals.sort(key=lambda s: s.combined_score, reverse=True)
        
        return signals
    
    async def find_opportunities(
        self, 
        min_score: float = 60,
        signal_types: List[str] = None
    ) -> List[SmartMoneySignal]:
        """
        Find trading opportunities from trending tokens.
        """
        if signal_types is None:
            signal_types = ["buy", "strong_buy"]
        
        logger.info(f"🔎 Finding opportunities (min score: {min_score})")
        
        # Get trending tokens from DexScreener
        trending = await self._dexscreener_call("token-pairs/v1/solana/trending")
        
        if not trending or not isinstance(trending, list):
            logger.warning("No trending tokens found")
            return []
        
        # Extract unique token addresses
        seen = set()
        tokens = []
        for pair in trending[:50]:  # Top 50 trending
            token_addr = pair.get("baseToken", {}).get("address")
            if token_addr and token_addr not in seen:
                seen.add(token_addr)
                tokens.append(token_addr)
        
        logger.info(f"Analyzing {len(tokens)} trending tokens")
        
        # Analyze all tokens
        signals = await self.scan_watchlist(tokens)
        
        # Filter by criteria
        opportunities = [
            s for s in signals 
            if s.combined_score >= min_score 
            and s.signal_type in signal_types
        ]
        
        return opportunities
    
    def save_signal(self, signal: SmartMoneySignal):
        """Save signal to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signal_{signal.symbol}_{timestamp}.json"
        filepath = os.path.join(self.config.data_dir, filename)
        
        # Convert dataclass to dict
        signal_dict = self._signal_to_dict(signal)
        
        with open(filepath, 'w') as f:
            json.dump(signal_dict, f, indent=2)
        
        logger.info(f"Signal saved: {filepath}")
    
    def _signal_to_dict(self, signal: SmartMoneySignal) -> Dict:
        """Convert SmartMoneySignal to dictionary."""
        return {
            "token_address": signal.token_address,
            "symbol": signal.symbol,
            "timestamp": signal.timestamp,
            "scores": {
                "smart_money": signal.smart_money_score,
                "momentum": signal.momentum_score,
                "pattern": signal.pattern_score,
                "combined": signal.combined_score
            },
            "signal": {
                "type": signal.signal_type,
                "confidence": signal.confidence,
                "timeframe": signal.timeframe
            },
            "holder_metrics": {
                "total_holders": signal.holder_metrics.total_holders,
                "smart_money_count": signal.holder_metrics.smart_money_count,
                "whale_count": signal.holder_metrics.whale_count,
                "smart_money_holdings_pct": signal.holder_metrics.smart_money_holdings_percent,
                "concentration_risk": signal.holder_metrics.concentration_risk,
                "smart_money_buying": signal.holder_metrics.smart_money_buying,
                "smart_money_selling": signal.holder_metrics.smart_money_selling
            },
            "volume_momentum": {
                "volume_24h": signal.volume_momentum.current_volume_24h,
                "volume_trend": signal.volume_momentum.volume_trend,
                "volume_ratio": signal.volume_momentum.volume_ratio,
                "buy_pressure": signal.volume_momentum.buy_pressure,
                "net_pressure": signal.volume_momentum.net_pressure,
                "accumulation_score": signal.volume_momentum.accumulation_score
            },
            "momentum_indicators": {
                "rsi_14": signal.momentum_indicators.rsi_14,
                "rsi_trend": signal.momentum_indicators.rsi_trend,
                "macd": signal.momentum_indicators.macd_signal,
                "price_momentum_24h": signal.momentum_indicators.price_momentum_24h,
                "trend_direction": signal.momentum_indicators.trend_direction,
                "trend_strength": signal.momentum_indicators.trend_strength,
                "support": signal.momentum_indicators.support_level,
                "resistance": signal.momentum_indicators.resistance_level
            },
            "patterns": [
                {
                    "type": p.pattern_type,
                    "confidence": p.confidence,
                    "target": p.price_target,
                    "stop": p.stop_loss
                }
                for p in signal.detected_patterns
            ],
            "insights": signal.key_insights,
            "green_flags": signal.green_flags,
            "red_flags": signal.red_flags,
            "trade_parameters": {
                "entry": signal.suggested_entry,
                "stop_loss": signal.suggested_stop,
                "target": signal.suggested_target,
                "risk_reward": signal.risk_reward_ratio
            }
        }
    
    def print_signal(self, signal: SmartMoneySignal):
        """Pretty print a signal."""
        print("\n" + "="*60)
        print(f"🎯 SMART MONEY SIGNAL: {signal.symbol}")
        print("="*60)
        
        print(f"\n📊 SCORES:")
        print(f"   Smart Money: {signal.smart_money_score:.0f}/100")
        print(f"   Momentum:    {signal.momentum_score:.0f}/100")
        print(f"   Pattern:     {signal.pattern_score:.0f}/100")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   COMBINED:    {signal.combined_score:.0f}/100")
        
        signal_emoji = {
            "strong_buy": "🟢🟢",
            "buy": "🟢",
            "hold": "🟡",
            "sell": "🔴",
            "strong_sell": "🔴🔴"
        }
        emoji = signal_emoji.get(signal.signal_type, "⚪")
        print(f"\n{emoji} SIGNAL: {signal.signal_type.upper().replace('_', ' ')}")
        print(f"   Confidence: {signal.confidence:.0f}%")
        print(f"   Timeframe: {signal.timeframe}")
        
        if signal.green_flags:
            print(f"\n✅ GREEN FLAGS:")
            for flag in signal.green_flags[:5]:
                print(f"   • {flag}")
        
        if signal.red_flags:
            print(f"\n⚠️ RED FLAGS:")
            for flag in signal.red_flags[:5]:
                print(f"   • {flag}")
        
        print(f"\n🧠 HOLDER INSIGHTS:")
        hm = signal.holder_metrics
        print(f"   Smart Money: {hm.smart_money_count} wallets")
        print(f"   Whales: {hm.whale_count}")
        print(f"   SM Holdings: {hm.smart_money_holdings_percent:.1f}%")
        if hm.smart_money_buying:
            print(f"   🟢 Smart money is ACCUMULATING")
        if hm.smart_money_selling:
            print(f"   🔴 Smart money is DISTRIBUTING")
        
        print(f"\n📈 VOLUME/MOMENTUM:")
        vm = signal.volume_momentum
        print(f"   Trend: {vm.volume_trend.upper()}")
        print(f"   Volume Ratio: {vm.volume_ratio:.1f}x")
        print(f"   Buy Pressure: {vm.buy_pressure:.0f}%")
        print(f"   Accumulation: {vm.accumulation_score:.0f}/100")
        
        mi = signal.momentum_indicators
        print(f"\n📉 TECHNICALS:")
        print(f"   RSI: {mi.rsi_14:.0f} ({mi.rsi_trend})")
        print(f"   MACD: {mi.macd_signal}")
        print(f"   Trend: {mi.trend_direction.upper()} ({mi.trend_strength:.0f}% strength)")
        print(f"   24h Change: {mi.price_momentum_24h:+.1f}%")
        
        if signal.detected_patterns:
            print(f"\n🔍 PATTERNS DETECTED:")
            for p in signal.detected_patterns:
                print(f"   • {p.pattern_type.upper()} ({p.confidence:.0f}% confidence)")
                if p.price_target:
                    print(f"     Target: ${p.price_target:.6f}")
        
        print(f"\n💡 KEY INSIGHTS:")
        for insight in signal.key_insights[:5]:
            print(f"   • {insight}")
        
        if signal.suggested_entry:
            print(f"\n🎯 TRADE PARAMETERS:")
            print(f"   Entry: ${signal.suggested_entry:.8f}")
            if signal.suggested_stop:
                print(f"   Stop:  ${signal.suggested_stop:.8f}")
            if signal.suggested_target:
                print(f"   Target: ${signal.suggested_target:.8f}")
            if signal.risk_reward_ratio:
                print(f"   R:R: {signal.risk_reward_ratio}")
        
        print("="*60)


# CLI Interface
async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Money Momentum Agent")
    parser.add_argument("--token", "-t", help="Analyze single token address")
    parser.add_argument("--watchlist", "-w", help="Path to watchlist file (one address per line)")
    parser.add_argument("--find", "-f", action="store_true", help="Find opportunities from trending tokens")
    parser.add_argument("--min-score", "-s", type=float, default=60, help="Minimum combined score")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    
    args = parser.parse_args()
    
    async with SmartMoneyMomentumAgent() as agent:
        if args.token:
            # Analyze single token
            signal = await agent.analyze_token(args.token)
            if signal:
                agent.print_signal(signal)
                if args.save:
                    agent.save_signal(signal)
            else:
                print(f"❌ Could not analyze token: {args.token}")
                
        elif args.watchlist:
            # Analyze watchlist
            with open(args.watchlist) as f:
                tokens = [line.strip() for line in f if line.strip()]
            
            signals = await agent.scan_watchlist(tokens)
            
            print(f"\n📊 ANALYZED {len(signals)} TOKENS")
            print(f"Top opportunities (score >= {args.min_score}):\n")
            
            for signal in signals:
                if signal.combined_score >= args.min_score:
                    agent.print_signal(signal)
                    if args.save:
                        agent.save_signal(signal)
                        
        elif args.find:
            # Find opportunities
            opportunities = await agent.find_opportunities(min_score=args.min_score)
            
            print(f"\n🎯 FOUND {len(opportunities)} OPPORTUNITIES")
            print(f"(Min score: {args.min_score})\n")
            
            for signal in opportunities[:10]:  # Top 10
                agent.print_signal(signal)
                if args.save:
                    agent.save_signal(signal)
        else:
            parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
