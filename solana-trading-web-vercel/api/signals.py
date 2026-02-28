"""
1SOL Trader API - Smart Money Signals (Real Data)
Vercel Serverless Function with Helius Integration
"""

import os
import sys
import asyncio
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

# Import Smart Money Agent
try:
    from smart_money_momentum_agent import SmartMoneyMomentumAgent, AgentConfig
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Smart Money Agent: {e}")
    AGENT_AVAILABLE = False

# Set Helius API Key
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', 'cfb197fe-7adf-4a30-a2f0-9dfdbb5924dd')
os.environ['HELIUS_API_KEY'] = HELIUS_API_KEY

# Cache for signals (to reduce API calls)
_signals_cache = None
_cache_time = 0
CACHE_DURATION = 30  # seconds

async def get_signals_with_agent(min_score=60, limit=10):
    """Get signals using Smart Money Agent."""
    if not AGENT_AVAILABLE:
        return []
    
    try:
        agent = SmartMoneyMomentumAgent(AgentConfig())
        
        async with agent:
            signals = await agent.find_opportunities(min_score=min_score)
            return signals[:limit]
    except Exception as e:
        print(f"Error getting signals: {e}")
        return []

def signal_to_dict(signal):
    """Convert signal to dictionary."""
    return {
        "id": hash(signal.token_address) % 10000,
        "token_address": signal.token_address,
        "symbol": signal.symbol,
        "name": signal.symbol,
        "signal_type": signal.signal_type,
        "confidence": signal.confidence,
        "combined_score": signal.combined_score,
        "smart_money_score": signal.smart_money_score,
        "momentum_score": signal.momentum_score,
        "pattern_score": signal.pattern_score,
        "smart_money_count": signal.holder_metrics.smart_money_count,
        "whale_count": signal.holder_metrics.whale_count,
        "smart_money_holdings_pct": signal.holder_metrics.smart_money_holdings_percent,
        "smart_money_buying": signal.holder_metrics.smart_money_buying,
        "smart_money_selling": signal.holder_metrics.smart_money_selling,
        "volume_trend": signal.volume_momentum.volume_trend,
        "volume_ratio": signal.volume_momentum.volume_ratio,
        "buy_pressure": signal.volume_momentum.buy_pressure,
        "net_pressure": signal.volume_momentum.net_pressure,
        "accumulation_score": signal.volume_momentum.accumulation_score,
        "price_momentum_24h": signal.momentum_indicators.price_momentum_24h,
        "rsi": signal.momentum_indicators.rsi_14,
        "rsi_trend": signal.momentum_indicators.rsi_trend,
        "macd": signal.momentum_indicators.macd_signal,
        "trend_direction": signal.momentum_indicators.trend_direction,
        "trend_strength": signal.momentum_indicators.trend_strength,
        "support_level": signal.momentum_indicators.support_level,
        "resistance_level": signal.momentum_indicators.resistance_level,
        "current_price": signal.suggested_entry,
        "suggested_entry": signal.suggested_entry,
        "suggested_stop": signal.suggested_stop,
        "suggested_target": signal.suggested_target,
        "risk_reward": signal.risk_reward_ratio,
        "timeframe": signal.timeframe,
        "green_flags": signal.green_flags,
        "red_flags": signal.red_flags,
        "key_insights": signal.key_insights,
        "patterns": [
            {
                "type": p.pattern_type,
                "confidence": p.confidence,
                "target": p.price_target,
                "stop": p.stop_loss
            }
            for p in signal.detected_patterns
        ],
        "timestamp": signal.timestamp
    }

# Mock signals as fallback
MOCK_SIGNALS = [
    {
        "id": 1,
        "token_address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "symbol": "BONK",
        "name": "Bonk",
        "signal_type": "strong_buy",
        "confidence": 85,
        "combined_score": 82,
        "smart_money_score": 78,
        "momentum_score": 85,
        "pattern_score": 80,
        "smart_money_count": 7,
        "whale_count": 3,
        "smart_money_buying": True,
        "smart_money_selling": False,
        "volume_trend": "spiking",
        "volume_ratio": 3.2,
        "buy_pressure": 68,
        "net_pressure": 28,
        "accumulation_score": 85,
        "price_momentum_24h": 15.4,
        "rsi": 62,
        "trend_direction": "up",
        "current_price": 0.00001234,
        "suggested_entry": 0.00001234,
        "suggested_stop": 0.00001135,
        "suggested_target": 0.00001481,
        "risk_reward": "1:2.5",
        "green_flags": ["Smart money buying", "Volume spike (3.2x)", "Uptrend (+15.4%)", "Breakout pattern"],
        "red_flags": [],
        "key_insights": ["🔥 Volume spike detected (3.2x average)", "🟢 Strong buy pressure (68%)", "📈 Accumulation pattern detected"]
    },
    {
        "id": 2,
        "token_address": "So11111111111111111111111111111111111111112",
        "symbol": "SOL",
        "name": "Wrapped SOL",
        "signal_type": "strong_buy",
        "confidence": 88,
        "combined_score": 85,
        "smart_money_score": 82,
        "momentum_score": 88,
        "pattern_score": 83,
        "smart_money_count": 12,
        "whale_count": 5,
        "smart_money_buying": True,
        "smart_money_selling": False,
        "volume_trend": "spiking",
        "volume_ratio": 2.8,
        "buy_pressure": 72,
        "net_pressure": 35,
        "accumulation_score": 80,
        "price_momentum_24h": 8.2,
        "rsi": 58,
        "trend_direction": "up",
        "current_price": 142.50,
        "suggested_entry": 142.50,
        "suggested_stop": 138.00,
        "suggested_target": 155.00,
        "risk_reward": "1:2.9",
        "green_flags": ["Smart money accumulating", "Strong uptrend", "High volume", "Breakout confirmed"],
        "red_flags": [],
        "key_insights": ["🚀 SOL breaking resistance", "🐋 5 whales accumulating", "📈 Volume 2.8x average"]
    },
    {
        "id": 3,
        "token_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "symbol": "PEPE",
        "name": "Pepe",
        "signal_type": "buy",
        "confidence": 72,
        "combined_score": 76,
        "smart_money_score": 80,
        "momentum_score": 70,
        "pattern_score": 75,
        "smart_money_count": 5,
        "whale_count": 2,
        "smart_money_buying": True,
        "smart_money_selling": False,
        "volume_trend": "increasing",
        "volume_ratio": 1.8,
        "buy_pressure": 60,
        "net_pressure": 15,
        "accumulation_score": 70,
        "price_momentum_24h": 8.5,
        "rsi": 45,
        "trend_direction": "up",
        "current_price": 0.00000890,
        "suggested_entry": 0.00000890,
        "suggested_stop": 0.00000820,
        "suggested_target": 0.00001050,
        "risk_reward": "1:2.3",
        "green_flags": ["Smart money accumulating", "Oversold RSI (45)", "Volume increasing"],
        "red_flags": [],
        "key_insights": ["📊 ACCUMULATION: Oversold bounce setup", "🧠 5 smart money wallets accumulating"]
    },
    {
        "id": 4,
        "token_address": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "symbol": "JUP",
        "name": "Jupiter",
        "signal_type": "buy",
        "confidence": 75,
        "combined_score": 74,
        "smart_money_score": 76,
        "momentum_score": 72,
        "pattern_score": 71,
        "smart_money_count": 4,
        "whale_count": 2,
        "smart_money_buying": True,
        "smart_money_selling": False,
        "volume_trend": "increasing",
        "volume_ratio": 1.5,
        "buy_pressure": 58,
        "net_pressure": 12,
        "accumulation_score": 65,
        "price_momentum_24h": 5.8,
        "rsi": 52,
        "trend_direction": "up",
        "current_price": 0.85,
        "suggested_entry": 0.85,
        "suggested_stop": 0.80,
        "suggested_target": 0.98,
        "risk_reward": "1:2.6",
        "green_flags": ["DEX token strength", "Smart money interest", "Growing volume"],
        "red_flags": [],
        "key_insights": ["📊 DEX sector momentum", "🧠 Smart money rotating to DEX tokens"]
    }
]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        import time
        global _signals_cache, _cache_time
        
        # Parse query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        min_score = float(params.get('min_score', [60])[0])
        limit = int(params.get('limit', [10])[0])
        
        signals_data = []
        using_real_data = False
        
        # Try to get real signals if cache is stale
        current_time = time.time()
        if _signals_cache is None or (current_time - _cache_time) > CACHE_DURATION:
            try:
                if AGENT_AVAILABLE:
                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    real_signals = loop.run_until_complete(get_signals_with_agent(min_score, limit))
                    loop.close()
                    
                    if real_signals:
                        signals_data = [signal_to_dict(s) for s in real_signals]
                        _signals_cache = signals_data
                        _cache_time = current_time
                        using_real_data = True
            except Exception as e:
                print(f"Error fetching real signals: {e}")
        
        # Fallback to cache or mock data
        if not signals_data:
            if _signals_cache:
                signals_data = _signals_cache
            else:
                signals_data = [s for s in MOCK_SIGNALS if s['combined_score'] >= min_score]
        
        signals_data = signals_data[:limit]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "count": len(signals_data),
            "using_real_data": using_real_data,
            "signals": signals_data
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
