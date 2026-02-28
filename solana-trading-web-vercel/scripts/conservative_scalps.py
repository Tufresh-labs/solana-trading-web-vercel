#!/usr/bin/env python3
"""
Conservative Scalp Setup Generator
Focuses on high-probability, lower-risk trades
For traders who prioritize capital preservation over aggressive gains
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from database import ContractDatabase

@dataclass
class ConservativeSetup:
    contract_address: str
    symbol: str
    
    # Entry/Exit
    entry_price: float
    stop_loss: float
    take_profit: float
    
    # Risk metrics
    risk_score: int
    risk_amount_pct: float  # How much % we risk
    reward_amount_pct: float  # How much % we target
    risk_reward_ratio: float
    
    # Position sizing
    position_size_pct: float  # % of portfolio
    max_position_usd: float  # Max $ amount
    
    # Trade parameters
    confidence: str  # HIGH, MEDIUM, LOW
    expected_win_rate: float  # Estimated %
    max_hold_time: str
    
    # Rationale
    setup_type: str
    key_factors: List[str]
    warnings: List[str]

class ConservativeScalpGenerator:
    def __init__(self):
        self.db = ContractDatabase()
        self.setups: List[ConservativeSetup] = []
        
        # Conservative criteria
        self.CRITERIA = {
            "max_risk_score": 32,  # Very strict
            "min_liquidity": 200000,  # $200K minimum
            "min_volume_24h": 50000,  # $50K daily volume
            "max_volatility": 25,  # Max 25% price swing
            "max_vol_liq_ratio": 5,  # Avoid wash trading
            "min_green_flags": 3,
            "max_red_flags": 1,
        }
    
    def qualifies_for_conservative(self, analysis: Dict) -> Tuple[bool, str]:
        """Check if token qualifies for conservative scalping."""
        risk = analysis.get("overall_risk_score", 100)
        if risk > self.CRITERIA["max_risk_score"]:
            return False, f"Risk too high ({risk} > {self.CRITERIA['max_risk_score']})"
        
        liq = analysis.get("liquidity_usd", 0)
        if liq < self.CRITERIA["min_liquidity"]:
            return False, f"Liquidity too low (${liq:,.0f} < ${self.CRITERIA['min_liquidity']:,})"
        
        vol = analysis.get("volume_24h", 0)
        if vol < self.CRITERIA["min_volume_24h"]:
            return False, f"Volume too low (${vol:,.0f} < ${self.CRITERIA['min_volume_24h']:,})"
        
        price_change = abs(analysis.get("price_change_24h", 100))
        if price_change > self.CRITERIA["max_volatility"]:
            return False, f"Too volatile ({price_change:.1f}% > {self.CRITERIA['max_volatility']}% max)"
        
        vol_liq = vol / liq if liq > 0 else 100
        if vol_liq > self.CRITERIA["max_vol_liq_ratio"]:
            return False, f"Suspicious volume ({vol_liq:.1f}x > {self.CRITERIA['max_vol_liq_ratio']}x max)"
        
        green_flags = json.loads(analysis.get("green_flags", "[]"))
        if len(green_flags) < self.CRITERIA["min_green_flags"]:
            return False, f"Not enough green flags ({len(green_flags)} < {self.CRITERIA['min_green_flags']})"
        
        red_flags = json.loads(analysis.get("red_flags", "[]"))
        if len(red_flags) > self.CRITERIA["max_red_flags"]:
            return False, f"Too many red flags ({len(red_flags)} > {self.CRITERIA['max_red_flags']})"
        
        return True, "Qualifies"
    
    def calculate_conservative_levels(self, analysis: Dict) -> Dict:
        """Calculate conservative entry/stop/target levels."""
        price = analysis.get("current_price", 0)
        risk_score = analysis.get("overall_risk_score", 50)
        price_change = analysis.get("price_change_24h", 0)
        
        if price <= 0:
            return {}
        
        # Determine setup type
        if price_change < -5:
            setup_type = "dip_buy"
            # Buy the dip - wider stop, higher target
            stop_pct = 0.025  # 2.5% stop
            target_pct = 0.04  # 4% target
        elif price_change > 5:
            setup_type = "momentum"
            # Ride momentum - tight stop, modest target
            stop_pct = 0.02  # 2% stop
            target_pct = 0.035  # 3.5% target
        else:
            setup_type = "range_play"
            # Range bound - tightest parameters
            stop_pct = 0.015  # 1.5% stop
            target_pct = 0.03  # 3% target
        
        # Adjust for risk score
        if risk_score <= 28:
            # Very low risk - can be slightly more aggressive
            position_size = 2.5  # 2.5% of portfolio
            confidence = "HIGH"
            win_rate = 65  # Estimated 65% win rate
            max_hold = "3-6 hours"
        elif risk_score <= 32:
            # Medium-low risk
            position_size = 2.0  # 2% of portfolio
            confidence = "MEDIUM"
            win_rate = 55
            max_hold = "2-4 hours"
        else:
            position_size = 1.5
            confidence = "LOW"
            win_rate = 50
            max_hold = "1-3 hours"
        
        entry = price
        stop = price * (1 - stop_pct)
        target = price * (1 + target_pct)
        
        risk_amount = stop_pct * 100
        reward_amount = target_pct * 100
        rr = target_pct / stop_pct if stop_pct > 0 else 0
        
        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "stop_pct": stop_pct * 100,
            "target_pct": target_pct * 100,
            "risk_amount": risk_amount,
            "reward_amount": reward_amount,
            "rr": rr,
            "position_size": position_size,
            "confidence": confidence,
            "win_rate": win_rate,
            "max_hold": max_hold,
            "setup_type": setup_type
        }
    
    def generate_setup(self, analysis: Dict) -> Optional[ConservativeSetup]:
        """Generate a conservative scalp setup."""
        qualifies, reason = self.qualifies_for_conservative(analysis)
        if not qualifies:
            return None
        
        levels = self.calculate_conservative_levels(analysis)
        if not levels:
            return None
        
        # Calculate max position in USD (assume $10K portfolio for example)
        portfolio_size = 10000  # $10K example
        max_position_usd = portfolio_size * (levels["position_size"] / 100)
        
        # Key factors
        key_factors = []
        green_flags = json.loads(analysis.get("green_flags", "[]"))
        
        if any("Mint authority revoked" in f for f in green_flags):
            key_factors.append("✅ Supply is fixed (mint revoked)")
        if any("Freeze authority revoked" in f for f in green_flags):
            key_factors.append("✅ Transfers cannot be frozen")
        if any("Healthy liquidity" in f for f in green_flags):
            key_factors.append("✅ Deep liquidity for easy exit")
        if any("Listed on multiple DEXs" in f for f in green_flags):
            key_factors.append("✅ DEX diversification reduces risk")
        
        # Add market factors
        liq = analysis.get("liquidity_usd", 0)
        if liq > 500000:
            key_factors.append(f"✅ Whale liquidity (${liq:,.0f})")
        
        price_change = analysis.get("price_change_24h", 0)
        if abs(price_change) < 5:
            key_factors.append("✅ Stable price action (low volatility)")
        elif -10 < price_change < -2:
            key_factors.append("✅ Mild dip = good entry opportunity")
        
        # Warnings
        warnings = []
        red_flags = json.loads(analysis.get("red_flags", "[]"))
        for flag in red_flags:
            if "WHALE" in flag:
                warnings.append("⚠️ Whale concentration - use smaller size")
            elif "LIQUIDITY" in flag:
                warnings.append("⚠️ Monitor liquidity for slippage")
        
        return ConservativeSetup(
            contract_address=analysis.get("contract_address", ""),
            symbol=analysis.get("token_symbol", "UNKNOWN"),
            entry_price=levels["entry"],
            stop_loss=levels["stop"],
            take_profit=levels["target"],
            risk_score=analysis.get("overall_risk_score", 50),
            risk_amount_pct=levels["risk_amount"],
            reward_amount_pct=levels["reward_amount"],
            risk_reward_ratio=levels["rr"],
            position_size_pct=levels["position_size"],
            max_position_usd=max_position_usd,
            confidence=levels["confidence"],
            expected_win_rate=levels["win_rate"],
            max_hold_time=levels["max_hold"],
            setup_type=levels["setup_type"],
            key_factors=key_factors,
            warnings=warnings
        )
    
    def generate_all_setups(self) -> List[ConservativeSetup]:
        """Generate conservative setups for all qualifying tokens."""
        print("=" * 80)
        print("🛡️ CONSERVATIVE SCALP SETUP GENERATOR")
        print("=" * 80)
        print("\n📋 Conservative Criteria:")
        print(f"   • Max Risk Score: {self.CRITERIA['max_risk_score']}/100")
        print(f"   • Min Liquidity: ${self.CRITERIA['min_liquidity']:,}")
        print(f"   • Min 24h Volume: ${self.CRITERIA['min_volume_24h']:,}")
        print(f"   • Max Volatility: {self.CRITERIA['max_volatility']}%")
        print(f"   • Max Vol/Liq Ratio: {self.CRITERIA['max_vol_liq_ratio']}x")
        print(f"   • Min Green Flags: {self.CRITERIA['min_green_flags']}")
        print(f"   • Max Red Flags: {self.CRITERIA['max_red_flags']}")
        print()
        
        all_contracts = self.db.get_all_contracts(limit=1000)
        setups = []
        
        print(f"🔍 Screening {len(all_contracts)} tokens...")
        
        for contract in all_contracts:
            analysis = self.db.get_analysis(contract["contract_address"])
            if not analysis:
                continue
            
            qualifies, reason = self.qualifies_for_conservative(analysis)
            if qualifies:
                setup = self.generate_setup(analysis)
                if setup:
                    setups.append(setup)
            else:
                print(f"   ✗ {contract['contract_address'][:20]}... - {reason}")
        
        # Sort by risk score (lowest first), then by liquidity (highest first)
        setups.sort(key=lambda x: (x.risk_score, -x.max_position_usd))
        
        return setups

def print_conservative_setup(setup: ConservativeSetup, rank: int):
    """Print a conservative setup."""
    print(f"\n{'=' * 80}")
    print(f"🛡️ CONSERVATIVE SETUP #{rank}: {setup.symbol}")
    print(f"   {setup.contract_address}")
    print(f"{'=' * 80}")
    
    # Risk/Confidence
    risk_emoji = "🟢" if setup.risk_score <= 28 else "🟡"
    print(f"\n{risk_emoji} Risk Score: {setup.risk_score}/100")
    print(f"📊 Confidence: {setup.confidence} (Est. Win Rate: {setup.expected_win_rate}%)")
    print(f"🎯 Setup Type: {setup.setup_type.replace('_', ' ').title()}")
    
    # Trade Levels
    print(f"\n💰 Trade Levels:")
    print(f"   🚪 Entry: ${setup.entry_price:.6f}")
    print(f"   🛑 Stop Loss: ${setup.stop_loss:.6f} (-{setup.risk_amount_pct:.1f}%)")
    print(f"   🎯 Take Profit: ${setup.take_profit:.6f} (+{setup.reward_amount_pct:.1f}%)")
    print(f"   📈 Risk/Reward: 1:{setup.risk_reward_ratio:.1f}")
    
    # Position Sizing
    print(f"\n💼 Position Sizing (Conservative):")
    print(f"   Portfolio Allocation: {setup.position_size_pct}%")
    print(f"   Example ($10K port): ${setup.max_position_usd:.2f} max")
    print(f"   Risk per trade: {setup.risk_amount_pct:.1f}% of position")
    print(f"   Max Hold Time: {setup.max_hold_time}")
    
    # Key Factors
    print(f"\n✅ Why This Setup Works:")
    for factor in setup.key_factors:
        print(f"   {factor}")
    
    # Warnings
    if setup.warnings:
        print(f"\n⚠️ Cautions:")
        for warning in setup.warnings:
            print(f"   {warning}")
    
    # Execution Plan
    print(f"\n📝 Conservative Execution Plan:")
    print(f"   1. Enter at ${setup.entry_price:.6f} with {setup.position_size_pct}% position")
    print(f"   2. Set stop loss at ${setup.stop_loss:.6f} immediately")
    print(f"   3. Set take profit at ${setup.take_profit:.6f}")
    print(f"   4. If price moves halfway to target, move stop to breakeven")
    print(f"   5. Close position if not profitable within {setup.max_hold_time}")
    print(f"   6. Take profit at target - DON'T GET GREEDY")
    print(f"\n   💡 Expected: Win {setup.expected_win_rate}% of these trades")
    print(f"      With 1:{setup.risk_reward_ratio:.1f} R:R, profitable if win rate > {100/(setup.risk_reward_ratio+1):.0f}%")

def main():
    generator = ConservativeScalpGenerator()
    setups = generator.generate_all_setups()
    
    if not setups:
        print("\n❌ No tokens meet conservative criteria")
        print("\n💡 Try relaxing criteria or analyze more tokens")
        return
    
    print(f"\n✅ Found {len(setups)} conservative setups\n")
    
    # Print detailed setups
    for i, setup in enumerate(setups, 1):
        print_conservative_setup(setup, i)
    
    # Summary table
    print("\n" + "=" * 100)
    print("📊 CONSERVATIVE SETUPS SUMMARY")
    print("=" * 100)
    print(f"{'Rank':<6}{'Symbol':<12}{'Risk':<8}{'Entry':<14}{'Stop':<14}{'Target':<14}{'R:R':<8}{'Conf':<10}{'Size':<8}")
    print("-" * 100)
    
    for i, setup in enumerate(setups, 1):
        print(f"{i:<6}{setup.symbol:<12}{setup.risk_score:<8}${setup.entry_price:.6f}{'':<7}${setup.stop_loss:.6f}{'':<7}${setup.take_profit:.6f}{'':<7}1:{setup.risk_reward_ratio:<5.1f}{setup.confidence:<10}{setup.position_size_pct}%")
    
    print("=" * 100)
    
    # Quick reference card
    print("\n" + "=" * 80)
    print("📋 CONSERVATIVE TRADER'S QUICK REFERENCE")
    print("=" * 80)
    
    if setups:
        best = setups[0]
        print(f"\n🏆 BEST SETUP:")
        print(f"   Token: {best.symbol}")
        print(f"   Entry: ${best.entry_price:.6f}")
        print(f"   Stop: ${best.stop_loss:.6f}")
        print(f"   Target: ${best.take_profit:.6f}")
        print(f"   Risk/Reward: 1:{best.risk_reward_ratio:.1f}")
        print(f"   Position: {best.position_size_pct}%")
        print(f"   Expected Win Rate: {best.expected_win_rate}%")
        
        print(f"\n📈 ALL SETUPS:")
        for i, setup in enumerate(setups[:5], 1):
            print(f"   {i}. {setup.symbol} | Risk: {setup.risk_score} | R:R: 1:{setup.risk_reward_ratio:.1f} | {setup.confidence}")
    
    print("\n🛡️ Conservative Trading Rules:")
    print("   1. Only trade setups with Risk Score ≤ 32")
    print("   2. Max position: 2.5% of portfolio")
    print("   3. Always use stop loss (max 2.5% risk)")
    print("   4. Target 1:1.5 to 1:2 R:R minimum")
    print("   5. Take profits at target - no greed")
    print("   6. Move stop to breakeven when halfway to target")
    print("   7. Close if not profitable within max hold time")
    print("=" * 80)

if __name__ == "__main__":
    main()
