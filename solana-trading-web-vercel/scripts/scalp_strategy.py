#!/usr/bin/env python3
"""
Scalp Trading Strategy Generator
Generates entry/exit points based on risk scores and current market conditions
"""

import json
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from database import ContractDatabase

@dataclass
class ScalpSetup:
    contract_address: str
    token_symbol: str
    
    # Risk metrics
    risk_score: int
    risk_rating: str
    
    # Market data
    current_price: float
    price_change_24h: float
    liquidity_usd: float
    volume_24h: float
    vol_liq_ratio: float
    
    # Entry/Exit points
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Quick scalp target (1-2%)
    take_profit_2: float  # Extended target (3-5%)
    take_profit_3: float  # Aggressive target (8%+)
    
    # Trade parameters
    position_size_pct: float  # Recommended % of portfolio
    max_hold_time: str  # How long to hold
    confidence: str
    
    # Rationale
    setup_type: str
    reasoning: List[str]
    warnings: List[str]

class ScalpStrategyGenerator:
    def __init__(self):
        self.db = ContractDatabase()
    
    def calculate_vol_liq_ratio(self, volume: float, liquidity: float) -> float:
        """Calculate volume to liquidity ratio."""
        if liquidity <= 0:
            return 0
        return volume / liquidity
    
    def determine_setup_type(self, contract: Dict) -> str:
        """Determine the best scalp setup type based on market conditions."""
        price_change = contract.get("price_change_24h", 0)
        vol_liq = self.calculate_vol_liq_ratio(
            contract.get("volume_24h", 0),
            contract.get("liquidity_usd", 0)
        )
        
        # Pump continuation
        if price_change > 50:
            return "pump_continuation"
        
        # Dip buy
        if price_change < -20:
            return "dip_buy"
        
        # Range play
        if abs(price_change) < 10:
            return "range_play"
        
        # Momentum play
        if vol_liq > 5:
            return "momentum"
        
        return "standard"
    
    def calculate_entry_exit(self, contract: Dict, setup_type: str) -> Dict:
        """Calculate entry, stop loss, and take profit levels."""
        current_price = contract.get("current_price", 0)
        risk_score = contract.get("overall_risk_score", 50)
        price_change = contract.get("price_change_24h", 0)
        
        if current_price <= 0:
            return {}
        
        # Adjust based on setup type and risk
        if setup_type == "pump_continuation":
            # FOMO play - tight stops
            entry = current_price
            stop_loss = current_price * 0.95  # 5% stop
            tp1 = current_price * 1.02  # 2% quick profit
            tp2 = current_price * 1.05  # 5% extended
            tp3 = current_price * 1.10  # 10% moon shot
            
        elif setup_type == "dip_buy":
            # Buy the dip - wider stops, higher targets
            entry = current_price
            stop_loss = current_price * 0.93  # 7% stop (already down)
            tp1 = current_price * 1.03  # 3% bounce
            tp2 = current_price * 1.08  # 8% recovery
            tp3 = current_price * 1.15  # 15% full recovery
            
        elif setup_type == "range_play":
            # Chop play - tight targets
            entry = current_price
            stop_loss = current_price * 0.97  # 3% stop
            tp1 = current_price * 1.015  # 1.5% scalp
            tp2 = current_price * 1.03  # 3% profit
            tp3 = current_price * 1.05  # 5% breakout
            
        elif setup_type == "momentum":
            # High volume play
            entry = current_price
            stop_loss = current_price * 0.96  # 4% stop
            tp1 = current_price * 1.025  # 2.5% quick
            tp2 = current_price * 1.06  # 6% momentum
            tp3 = current_price * 1.12  # 12% run
            
        else:  # standard
            entry = current_price
            stop_loss = current_price * 0.96
            tp1 = current_price * 1.02
            tp2 = current_price * 1.05
            tp3 = current_price * 1.10
        
        # Adjust for risk score
        if risk_score <= 30:
            # Lower risk = can hold longer for bigger targets
            pass
        elif risk_score <= 40:
            # Medium risk = tighten targets
            tp3 = tp2
        else:
            # High risk = scalp only
            tp2 = tp1 * 1.02
            tp3 = tp2
        
        return {
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3
        }
    
    def position_size_by_risk(self, risk_score: int) -> float:
        """Determine position size based on risk score."""
        if risk_score <= 30:
            return 3.0  # 3% of portfolio
        elif risk_score <= 35:
            return 2.5
        elif risk_score <= 40:
            return 2.0
        else:
            return 1.0  # 1% of portfolio max
    
    def max_hold_time(self, risk_score: int, setup_type: str) -> str:
        """Determine maximum hold time."""
        if risk_score <= 30:
            base_time = "2-6 hours"
        elif risk_score <= 40:
            base_time = "1-4 hours"
        else:
            base_time = "30-90 minutes"
        
        if setup_type == "pump_continuation":
            return f"15-45 minutes (pump can reverse fast)"
        elif setup_type == "dip_buy":
            return f"2-8 hours (recovery takes time)"
        else:
            return base_time
    
    def generate_reasoning(self, contract: Dict, setup_type: str) -> List[str]:
        """Generate reasoning for the trade setup."""
        reasoning = []
        
        # Risk-based reasoning
        risk_score = contract.get("overall_risk_score", 50)
        if risk_score <= 30:
            reasoning.append("✅ Low risk score allows for larger position size")
        elif risk_score <= 40:
            reasoning.append("⚠️ Medium risk - use moderate position size")
        else:
            reasoning.append("🔴 Higher risk - minimal position only")
        
        # Liquidity check
        liquidity = contract.get("liquidity_usd", 0)
        if liquidity > 500000:
            reasoning.append("✅ Good liquidity - easy entry/exit")
        elif liquidity > 100000:
            reasoning.append("⚠️ Moderate liquidity - watch slippage")
        else:
            reasoning.append("🔴 Low liquidity - difficult to exit large positions")
        
        # Volume analysis
        volume = contract.get("volume_24h", 0)
        vol_liq = self.calculate_vol_liq_ratio(volume, liquidity)
        if vol_liq > 5:
            reasoning.append("⚠️ High volume/liquidity ratio - possible wash trading")
        elif vol_liq > 2:
            reasoning.append("✅ Good trading activity")
        else:
            reasoning.append("⚠️ Low volume - might be hard to sell")
        
        # Price action
        price_change = contract.get("price_change_24h", 0)
        if price_change > 100:
            reasoning.append("🚀 Extreme pump - high risk of dump")
        elif price_change > 50:
            reasoning.append("📈 Strong momentum - ride the wave with tight stops")
        elif price_change < -30:
            reasoning.append("🔻 Deep dip - potential bounce play")
        elif price_change < -10:
            reasoning.append("📉 Mild correction - possible entry")
        else:
            reasoning.append("➡️ Sideways action - range trade")
        
        # Contract safety
        red_flags = json.loads(contract.get("red_flags", "[]"))
        green_flags = json.loads(contract.get("green_flags", "[]"))
        
        if len(green_flags) >= 3:
            reasoning.append("✅ Multiple green flags - contract is relatively safe")
        if len(red_flags) == 0:
            reasoning.append("✅ No red flags detected")
        elif len(red_flags) == 1 and "WHALE" in red_flags[0]:
            reasoning.append("⚠️ Only risk is whale concentration - use small size")
        else:
            reasoning.append(f"🔴 {len(red_flags)} red flags present")
        
        return reasoning
    
    def generate_warnings(self, contract: Dict) -> List[str]:
        """Generate warnings for the trade."""
        warnings = []
        
        red_flags = json.loads(contract.get("red_flags", "[]"))
        for flag in red_flags:
            if "WHALE" in flag:
                warnings.append("🐋 WHALE ALERT: Top 10 holders control >80% - can dump anytime")
            elif "LIQUIDITY" in flag:
                warnings.append("💧 LOW LIQUIDITY: High slippage expected on entry/exit")
            elif "VOLUME" in flag:
                warnings.append("📊 VOLUME SPIKE: Possible manipulation")
        
        # Price warning
        price_change = contract.get("price_change_24h", 0)
        if abs(price_change) > 200:
            warnings.append("🚨 EXTREME VOLATILITY: Price moved >200% in 24h - highly dangerous")
        elif abs(price_change) > 100:
            warnings.append("⚠️ HIGH VOLATILITY: Major price swing - use tight stops")
        
        # Volume warning
        liquidity = contract.get("liquidity_usd", 0)
        volume = contract.get("volume_24h", 0)
        vol_liq = self.calculate_vol_liq_ratio(volume, liquidity)
        if vol_liq > 10:
            warnings.append("🤖 WASH TRADING SUSPECTED: Volume 10x+ liquidity - artificial activity")
        elif vol_liq > 5:
            warnings.append("⚠️ SUSPICIOUS VOLUME: Unusual volume patterns")
        
        return warnings
    
    def confidence_level(self, contract: Dict, setup_type: str) -> str:
        """Determine confidence level for the setup."""
        score = 0
        
        # Risk score contribution
        risk_score = contract.get("overall_risk_score", 50)
        if risk_score <= 30:
            score += 3
        elif risk_score <= 40:
            score += 2
        else:
            score += 1
        
        # Liquidity contribution
        liquidity = contract.get("liquidity_usd", 0)
        if liquidity > 500000:
            score += 3
        elif liquidity > 200000:
            score += 2
        elif liquidity > 50000:
            score += 1
        
        # Volume contribution
        volume = contract.get("volume_24h", 0)
        vol_liq = self.calculate_vol_liq_ratio(volume, liquidity)
        if 1 < vol_liq < 5:
            score += 2
        elif vol_liq < 10:
            score += 1
        
        # Setup type contribution
        if setup_type in ["dip_buy", "range_play"]:
            score += 2
        elif setup_type == "standard":
            score += 1
        
        # Red flags penalty
        red_flags = json.loads(contract.get("red_flags", "[]"))
        score -= len(red_flags)
        
        if score >= 7:
            return "HIGH"
        elif score >= 5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_setup(self, contract_address: str) -> Optional[ScalpSetup]:
        """Generate a complete scalp setup for a contract."""
        contract = self.db.get_analysis(contract_address)
        if not contract:
            return None
        
        setup_type = self.determine_setup_type(contract)
        levels = self.calculate_entry_exit(contract, setup_type)
        
        if not levels:
            return None
        
        liquidity = contract.get("liquidity_usd", 0)
        volume = contract.get("volume_24h", 0)
        
        return ScalpSetup(
            contract_address=contract_address,
            token_symbol=contract.get("token_symbol", "UNKNOWN"),
            risk_score=contract.get("overall_risk_score", 50),
            risk_rating=contract.get("risk_rating", "UNKNOWN"),
            current_price=contract.get("current_price", 0),
            price_change_24h=contract.get("price_change_24h", 0),
            liquidity_usd=liquidity,
            volume_24h=volume,
            vol_liq_ratio=self.calculate_vol_liq_ratio(volume, liquidity),
            entry_price=levels["entry"],
            stop_loss=levels["stop_loss"],
            take_profit_1=levels["tp1"],
            take_profit_2=levels["tp2"],
            take_profit_3=levels["tp3"],
            position_size_pct=self.position_size_by_risk(contract.get("overall_risk_score", 50)),
            max_hold_time=self.max_hold_time(
                contract.get("overall_risk_score", 50),
                setup_type
            ),
            confidence=self.confidence_level(contract, setup_type),
            setup_type=setup_type,
            reasoning=self.generate_reasoning(contract, setup_type),
            warnings=self.generate_warnings(contract)
        )
    
    def print_setup(self, setup: ScalpSetup):
        """Print a formatted scalp setup."""
        print("\n" + "=" * 80)
        print(f"🎯 SCALP SETUP: {setup.token_symbol}")
        print(f"   {setup.contract_address}")
        print("=" * 80)
        
        # Risk info
        risk_emoji = "🟢" if setup.risk_score <= 30 else "🟡" if setup.risk_score <= 40 else "🟠"
        print(f"\n{risk_emoji} Risk: {setup.risk_score}/100 ({setup.risk_rating}) | Confidence: {setup.confidence}")
        
        # Market data
        print(f"\n📊 Market Data:")
        print(f"   Current Price: ${setup.current_price:.6f}")
        change_emoji = "🟢" if setup.price_change_24h > 0 else "🔴"
        print(f"   24h Change: {change_emoji} {setup.price_change_24h:+.2f}%")
        print(f"   Liquidity: ${setup.liquidity_usd:,.2f}")
        print(f"   24h Volume: ${setup.volume_24h:,.2f}")
        print(f"   Vol/Liq Ratio: {setup.vol_liq_ratio:.2f}x")
        
        # Trade levels
        print(f"\n💰 Trade Levels ({setup.setup_type.replace('_', ' ').title()}):")
        print(f"   🚪 Entry: ${setup.entry_price:.6f}")
        print(f"   🛑 Stop Loss: ${setup.stop_loss:.6f} ({((setup.stop_loss/setup.entry_price)-1)*100:+.1f}%)")
        print(f"   🎯 TP1 (Quick): ${setup.take_profit_1:.6f} ({((setup.take_profit_1/setup.entry_price)-1)*100:+.1f}%)")
        print(f"   🎯 TP2 (Extended): ${setup.take_profit_2:.6f} ({((setup.take_profit_2/setup.entry_price)-1)*100:+.1f}%)")
        print(f"   🎯 TP3 (Aggressive): ${setup.take_profit_3:.6f} ({((setup.take_profit_3/setup.entry_price)-1)*100:+.1f}%)")
        
        # R:R Ratios
        risk = abs(setup.entry_price - setup.stop_loss)
        print(f"\n📈 Risk/Reward Ratios:")
        if risk > 0:
            print(f"   TP1 R:R = 1:{abs(setup.take_profit_1 - setup.entry_price) / risk:.1f}")
            print(f"   TP2 R:R = 1:{abs(setup.take_profit_2 - setup.entry_price) / risk:.1f}")
            print(f"   TP3 R:R = 1:{abs(setup.take_profit_3 - setup.entry_price) / risk:.1f}")
        
        # Position sizing
        print(f"\n💼 Position Sizing:")
        print(f"   Recommended: {setup.position_size_pct}% of portfolio")
        print(f"   Max Hold Time: {setup.max_hold_time}")
        
        # Reasoning
        print(f"\n✅ Reasoning:")
        for reason in setup.reasoning:
            print(f"   {reason}")
        
        # Warnings
        if setup.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in setup.warnings:
                print(f"   {warning}")
        
        # Execution plan
        print(f"\n📝 Execution Plan:")
        print(f"   1. Enter at ${setup.entry_price:.6f} with {setup.position_size_pct}% position")
        print(f"   2. Set stop loss at ${setup.stop_loss:.6f}")
        print(f"   3. Scale out: 33% at TP1, 33% at TP2, 34% at TP3")
        print(f"   4. Move stop to breakeven after TP1 hits")
        print(f"   5. Close entire position if not profitable within {setup.max_hold_time}")
        
        print("=" * 80)

def main():
    """Generate scalp setups for all contracts in database."""
    generator = ScalpStrategyGenerator()
    
    # Get all contracts
    contracts = generator.db.get_all_contracts(limit=20)
    
    if not contracts:
        print("No contracts in database. Run analyze_contract.py first.")
        return
    
    print("=" * 80)
    print("🎯 SCALP TRADING STRATEGIES - ALL CONTRACTS")
    print("=" * 80)
    
    setups = []
    for contract in contracts:
        setup = generator.generate_setup(contract["contract_address"])
        if setup:
            setups.append(setup)
            generator.print_setup(setup)
    
    # Rank setups
    print("\n" + "=" * 80)
    print("🏆 RANKED SCALP OPPORTUNITIES (Best to Worst)")
    print("=" * 80)
    
    # Sort by risk score and confidence
    def sort_key(s):
        confidence_score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s.confidence, 0)
        return (s.risk_score, -confidence_score)
    
    setups.sort(key=sort_key)
    
    print(f"\n{'Rank':<6}{'Contract':<24}{'Risk':<10}{'Conf':<10}{'Setup':<18}{'Entry':<14}{'R:R':<10}")
    print("-" * 100)
    
    for i, setup in enumerate(setups, 1):
        short_addr = f"{setup.contract_address[:20]}..."
        risk = f"{setup.risk_score}/100"
        conf = setup.confidence
        setup_type = setup.setup_type.replace('_', ' ').title()
        entry = f"${setup.current_price:.6f}"
        
        # Calculate best R:R
        risk_amt = abs(setup.entry_price - setup.stop_loss)
        rr = "N/A"
        if risk_amt > 0:
            rr = f"1:{abs(setup.take_profit_2 - setup.entry_price) / risk_amt:.1f}"
        
        print(f"{i:<6}{short_addr:<24}{setup.risk_score:<10}{conf:<10}{setup_type:<18}{entry:<14}{rr:<10}")
    
    print("\n" + "=" * 80)
    print("📋 QUICK REFERENCE - TOP 3 PICKS")
    print("=" * 80)
    
    for i, setup in enumerate(setups[:3], 1):
        print(f"\n#{i}: {setup.contract_address}")
        print(f"   Entry: ${setup.entry_price:.6f} | Stop: ${setup.stop_loss:.6f} | TP: ${setup.take_profit_2:.6f}")
        print(f"   Position: {setup.position_size_pct}% | Hold: {setup.max_hold_time}")

if __name__ == "__main__":
    main()
