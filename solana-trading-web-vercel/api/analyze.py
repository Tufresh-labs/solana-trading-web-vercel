"""
1SOL Trader API - Analyze Token (Real Data)
Vercel Serverless Function with Helius Integration
"""

import os
import sys
import asyncio
import json
from http.server import BaseHTTPRequestHandler

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

async def analyze_with_agent(token_address):
    """Analyze token using Smart Money Agent."""
    if not AGENT_AVAILABLE:
        return None
    
    try:
        agent = SmartMoneyMomentumAgent(AgentConfig())
        
        async with agent:
            signal = await agent.analyze_token(token_address)
            return signal
    except Exception as e:
        print(f"Error analyzing token: {e}")
        return None

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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Extract token address from path
        path_parts = self.path.split('/')
        token_address = path_parts[-1] if path_parts[-1] != 'analyze' else None
        
        if not token_address or len(token_address) < 30:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": "Invalid token address"
            }).encode())
            return
        
        using_real_data = False
        signal_data = None
        
        # Try to get real analysis
        try:
            if AGENT_AVAILABLE:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                signal = loop.run_until_complete(analyze_with_agent(token_address))
                loop.close()
                
                if signal:
                    signal_data = signal_to_dict(signal)
                    using_real_data = True
        except Exception as e:
            print(f"Error in real analysis: {e}")
        
        # Fallback to mock data
        if not signal_data:
            signal_data = {
                "id": hash(token_address) % 10000,
                "token_address": token_address,
                "symbol": "ANALYZED",
                "name": "Analyzed Token",
                "signal_type": "hold",
                "confidence": 50,
                "combined_score": 55,
                "smart_money_score": 52,
                "momentum_score": 58,
                "pattern_score": 50,
                "smart_money_count": 2,
                "whale_count": 1,
                "smart_money_buying": False,
                "smart_money_selling": False,
                "volume_trend": "stable",
                "volume_ratio": 1.1,
                "buy_pressure": 50,
                "net_pressure": 0,
                "accumulation_score": 50,
                "price_momentum_24h": 2.5,
                "rsi": 48,
                "rsi_trend": "neutral",
                "macd": "neutral",
                "trend_direction": "sideways",
                "trend_strength": 25,
                "current_price": 0.001,
                "suggested_entry": 0.001,
                "suggested_stop": 0.0009,
                "suggested_target": 0.0012,
                "risk_reward": "1:2.0",
                "green_flags": ["Token analyzed"],
                "red_flags": ["Limited historical data available"],
                "key_insights": ["⚠️ Using fallback analysis. Set HELIUS_API_KEY for full analysis."]
            }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "using_real_data": using_real_data,
            "signal": signal_data
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
