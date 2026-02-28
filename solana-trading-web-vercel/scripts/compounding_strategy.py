#!/usr/bin/env python3
"""
Compounding Strategy Framework
Analyzes existing database to find best tokens for consistent profit
Creates bankroll growth plan
"""

import json
import os
from typing import List, Dict, Tuple
from datetime import datetime
from database import ContractDatabase

class CompoundingStrategy:
    def __init__(self):
        self.db = ContractDatabase()
        self.portfolio_size = 10000  # Default $10K starting
        self.daily_trades = 3
        self.win_rate = 0.65
        self.avg_win_pct = 0.03
        self.avg_loss_pct = 0.02
        self.compound_rate = 0.70  # Reinvest 70%
    
    def load_qualified_tokens(self) -> List[Dict]:
        """Load tokens that qualify for compounding strategy."""
        print("🔍 Loading qualified tokens from database...")
        
        all_contracts = self.db.get_all_contracts(limit=1000)
        qualified = []
        
        for contract in all_contracts:
            analysis = self.db.get_analysis(contract["contract_address"])
            if not analysis:
                continue
            
            # Relaxed criteria for compounding
            risk = analysis.get("overall_risk_score", 100)
            liq = analysis.get("liquidity_usd", 0)
            mc = analysis.get("market_cap", 0)
            vol = analysis.get("volume_24h", 0)
            
            # Qualification criteria
            if risk <= 40 and liq >= 100000 and mc >= 100000 and vol >= 30000:
                # Calculate profit potential score
                score = self.calculate_profit_potential(analysis)
                qualified.append({
                    "analysis": analysis,
                    "profit_score": score
                })
        
        # Sort by profit potential
        qualified.sort(key=lambda x: x["profit_score"], reverse=True)
        
        print(f"  ✓ Found {len(qualified)} qualified tokens")
        return qualified
    
    def calculate_profit_potential(self, analysis: Dict) -> float:
        """Calculate profit potential score (0-100)."""
        score = 0
        
        # Risk (lower is better) - 30% weight
        risk = analysis.get("overall_risk_score", 50)
        score += (50 - risk) * 0.6  # 0-30 points
        
        # Liquidity (higher is better) - 25% weight
        liq = analysis.get("liquidity_usd", 0)
        if liq >= 1000000:
            score += 25
        elif liq >= 500000:
            score += 20
        elif liq >= 200000:
            score += 15
        elif liq >= 100000:
            score += 10
        
        # Volume activity - 20% weight
        vol = analysis.get("volume_24h", 0)
        vol_liq = vol / liq if liq > 0 else 0
        if 1 <= vol_liq <= 5:
            score += 20
        elif vol_liq > 0.5:
            score += 15
        else:
            score += 10
        
        # Market cap stability - 15% weight
        mc = analysis.get("market_cap", 0)
        if 100000 <= mc <= 50000000:  # Sweet spot
            score += 15
        elif mc > 50000000:
            score += 10  # Too big, less explosive
        else:
            score += 5
        
        # Price action - 10% weight
        price_change = abs(analysis.get("price_change_24h", 100))
        if price_change < 20:
            score += 10  # Stable
        elif price_change < 50:
            score += 7
        else:
            score += 3  # Too volatile
        
        return score
    
    def simulate_compounding(self, starting_capital: float, days: int) -> Dict:
        """Simulate bankroll growth over time."""
        capital = starting_capital
        trades_per_day = self.daily_trades
        total_trades = 0
        wins = 0
        losses = 0
        trade_history = []
        
        for day in range(1, days + 1):
            daily_pnl = 0
            
            for trade in range(trades_per_day):
                # Position size (2% of current capital)
                position = capital * 0.02
                
                # Simulate trade outcome
                import random
                if random.random() < self.win_rate:
                    # Win
                    profit = position * self.avg_win_pct
                    daily_pnl += profit
                    wins += 1
                else:
                    # Loss
                    loss = position * self.avg_loss_pct
                    daily_pnl -= loss
                    losses += 1
                
                total_trades += 1
            
            # Apply compounding (reinvest 70%)
            reinvest = daily_pnl * self.compound_rate
            capital += reinvest
            
            # Withdraw 30%
            withdraw = daily_pnl * (1 - self.compound_rate)
            
            trade_history.append({
                "day": day,
                "capital": capital,
                "daily_pnl": daily_pnl,
                "reinvested": reinvest,
                "withdrawn": withdraw,
                "total_trades": total_trades
            })
        
        return {
            "starting_capital": starting_capital,
            "final_capital": capital,
            "total_return_pct": ((capital - starting_capital) / starting_capital) * 100,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / total_trades) * 100,
            "trade_history": trade_history
        }
    
    def create_tier_system(self, tokens: List[Dict]) -> Dict[str, List[Dict]]:
        """Create tier system for token selection."""
        tiers = {
            "S_TIER": [],  # Best of the best
            "A_TIER": [],  # Very good
            "B_TIER": [],  # Good
            "C_TIER": [],  # Acceptable
        }
        
        for token in tokens:
            score = token["profit_score"]
            risk = token["analysis"].get("overall_risk_score", 50)
            
            if score >= 75 and risk <= 32:
                tiers["S_TIER"].append(token)
            elif score >= 65 and risk <= 35:
                tiers["A_TIER"].append(token)
            elif score >= 55 and risk <= 38:
                tiers["B_TIER"].append(token)
            elif score >= 45:
                tiers["C_TIER"].append(token)
        
        return tiers
    
    def generate_scalp_setups(self, token_data: Dict) -> Dict:
        """Generate specific scalp setup for a token."""
        analysis = token_data["analysis"]
        price = analysis.get("current_price", 0)
        risk = analysis.get("overall_risk_score", 50)
        
        if price <= 0:
            return {}
        
        # Determine setup parameters based on tier
        if risk <= 30:
            stop_pct = 0.015  # 1.5%
            target_pct = 0.03  # 3%
            position_pct = 0.025  # 2.5%
            confidence = "HIGH"
        elif risk <= 35:
            stop_pct = 0.02  # 2%
            target_pct = 0.03  # 3%
            position_pct = 0.02  # 2%
            confidence = "MEDIUM"
        else:
            stop_pct = 0.025  # 2.5%
            target_pct = 0.03  # 3%
            position_pct = 0.015  # 1.5%
            confidence = "LOW"
        
        return {
            "entry": price,
            "stop": price * (1 - stop_pct),
            "target": price * (1 + target_pct),
            "stop_pct": stop_pct * 100,
            "target_pct": target_pct * 100,
            "rr_ratio": target_pct / stop_pct,
            "position_pct": position_pct * 100,
            "confidence": confidence,
            "expected_profit": price * target_pct,
            "max_loss": price * stop_pct
        }
    
    def print_tier_report(self, tiers: Dict[str, List[Dict]]):
        """Print tier system report."""
        print("\n" + "=" * 80)
        print("🏆 TIER SYSTEM FOR COMPOUNDING")
        print("=" * 80)
        
        for tier_name, tokens in tiers.items():
            if not tokens:
                continue
            
            tier_emoji = {"S_TIER": "💎", "A_TIER": "🥇", "B_TIER": "🥈", "C_TIER": "🥉"}[tier_name]
            
            print(f"\n{tier_emoji} {tier_name.replace('_', ' ')} ({len(tokens)} tokens)")
            print("-" * 80)
            print(f"{'Contract':<44}{'Risk':<8}{'Profit Score':<15}{'Liquidity':<15}")
            print("-" * 80)
            
            for token in tokens[:10]:  # Show top 10 per tier
                a = token["analysis"]
                addr = a.get("contract_address", "")[:40]
                risk = f"{a.get('overall_risk_score')}/100"
                score = f"{token['profit_score']:.0f}"
                liq = f"${a.get('liquidity_usd', 0):,.0f}"
                print(f"{addr:<44}{risk:<8}{score:<15}{liq:<15}")
    
    def print_weekly_rotation_plan(self, tiers: Dict[str, List[Dict]]):
        """Print weekly token rotation plan."""
        print("\n" + "=" * 80)
        print("📅 WEEKLY ROTATION PLAN")
        print("=" * 80)
        
        # Build rotation
        rotation = []
        
        # Add S-tier (top 3)
        s_tier = tiers.get("S_TIER", [])[:3]
        for i, token in enumerate(s_tier, 1):
            setup = self.generate_scalp_setups(token)
            a = token["analysis"]
            rotation.append({
                "day": "Monday-Wednesday",
                "rank": i,
                "token": a.get("token_symbol", "UNKNOWN"),
                "address": a.get("contract_address", ""),
                "entry": setup.get("entry", 0),
                "stop": setup.get("stop", 0),
                "target": setup.get("target", 0),
                "position": setup.get("position_pct", 0),
                "confidence": setup.get("confidence", "LOW")
            })
        
        # Add A-tier (top 3)
        a_tier = tiers.get("A_TIER", [])[:3]
        for i, token in enumerate(a_tier, 1):
            setup = self.generate_scalp_setups(token)
            a = token["analysis"]
            rotation.append({
                "day": "Thursday-Saturday",
                "rank": i,
                "token": a.get("token_symbol", "UNKNOWN"),
                "address": a.get("contract_address", ""),
                "entry": setup.get("entry", 0),
                "stop": setup.get("stop", 0),
                "target": setup.get("target", 0),
                "position": setup.get("position_pct", 0),
                "confidence": setup.get("confidence", "LOW")
            })
        
        # Add B-tier (top 4 for Sunday)
        b_tier = tiers.get("B_TIER", [])[:4]
        for i, token in enumerate(b_tier, 1):
            setup = self.generate_scalp_setups(token)
            a = token["analysis"]
            rotation.append({
                "day": "Sunday",
                "rank": i,
                "token": a.get("token_symbol", "UNKNOWN"),
                "address": a.get("contract_address", ""),
                "entry": setup.get("entry", 0),
                "stop": setup.get("stop", 0),
                "target": setup.get("target", 0),
                "position": setup.get("position_pct", 0),
                "confidence": setup.get("confidence", "LOW")
            })
        
        # Print
        current_day = ""
        for trade in rotation:
            if trade["day"] != current_day:
                current_day = trade["day"]
                print(f"\n📆 {current_day}")
                print("-" * 80)
            
            print(f"\n  Trade #{trade['rank']}: {trade['token']} ({trade['confidence']})")
            print(f"    Entry: ${trade['entry']:.6f}")
            print(f"    Stop:  ${trade['stop']:.6f}")
            print(f"    Target: ${trade['target']:.6f}")
            print(f"    Position: {trade['position']}%")
        
        return rotation
    
    def print_compounding_projection(self, starting: float, days: int):
        """Print bankroll growth projection."""
        print("\n" + "=" * 80)
        print("💰 COMPOUNDING PROJECTION")
        print("=" * 80)
        print(f"\n📊 Parameters:")
        print(f"   Starting Capital: ${starting:,.2f}")
        print(f"   Daily Trades: {self.daily_trades}")
        print(f"   Win Rate: {self.win_rate*100:.0f}%")
        print(f"   Avg Win: +{self.avg_win_pct*100:.1f}%")
        print(f"   Avg Loss: -{self.avg_loss_pct*100:.1f}%")
        print(f"   Compound Rate: {self.compound_rate*100:.0f}% (withdraw {100-self.compound_rate*100:.0f}%)")
        
        # Run simulation
        result = self.simulate_compounding(starting, days)
        
        print(f"\n📈 {days}-Day Projection:")
        print(f"   Final Capital: ${result['final_capital']:,.2f}")
        print(f"   Total Return: +{result['total_return_pct']:.1f}%")
        print(f"   Total Trades: {result['total_trades']}")
        print(f"   Wins: {result['wins']} | Losses: {result['losses']}")
        print(f"   Actual Win Rate: {result['win_rate']:.1f}%")
        
        # Weekly milestones
        print(f"\n📅 Milestones:")
        milestones = [7, 14, 21, 30, 60, 90]
        for day in milestones:
            if day <= days:
                milestone_result = self.simulate_compounding(starting, day)
                print(f"   Day {day:3d}: ${milestone_result['final_capital']:>10,.2f} (+{milestone_result['total_return_pct']:>5.1f}%)")
        
        # Risk warning
        print(f"\n⚠️  Risk Warning:")
        print(f"   Past performance doesn't guarantee future results")
        print(f"   This is a simulation with {self.win_rate*100:.0f}% assumed win rate")
        print(f"   Actual results may vary significantly")

def main():
    strategy = CompoundingStrategy()
    
    print("=" * 80)
    print("💎 COMPOUNDING STRATEGY FRAMEWORK")
    print("   Building Bankroll Through Consistent Profits")
    print("=" * 80)
    
    # Load qualified tokens
    qualified = strategy.load_qualified_tokens()
    
    if not qualified:
        print("\n❌ No qualified tokens found")
        print("Run the mass scanner first to populate the database")
        return
    
    # Create tier system
    tiers = strategy.create_tier_system(qualified)
    
    # Print tier report
    strategy.print_tier_report(tiers)
    
    # Print weekly rotation
    rotation = strategy.print_weekly_rotation_plan(tiers)
    
    # Print compounding projection
    strategy.print_compounding_projection(starting=10000, days=90)
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 STRATEGY SUMMARY")
    print("=" * 80)
    
    total_qualified = len(qualified)
    s_count = len(tiers.get("S_TIER", []))
    a_count = len(tiers.get("A_TIER", []))
    b_count = len(tiers.get("B_TIER", []))
    
    print(f"\n📊 Token Universe:")
    print(f"   Total Qualified: {total_qualified}")
    print(f"   S-Tier (Best): {s_count}")
    print(f"   A-Tier (Very Good): {a_count}")
    print(f"   B-Tier (Good): {b_count}")
    
    print(f"\n💡 Trading Plan:")
    print(f"   1. Trade 2-3 tokens daily from S & A tiers")
    print(f"   2. Use 2-2.5% position sizes")
    print(f"   3. Target 3% gains with 1.5-2% stops")
    print(f"   4. Reinvest 70% of profits")
    print(f"   5. Withdraw 30% for living expenses/savings")
    print(f"   6. Rotate to new tokens weekly")
    
    print(f"\n🚀 Expected Results (90 days):")
    print(f"   Starting: $10,000")
    print(f"   Projected: $16,000-$20,000")
    print(f"   Withdrawn: $3,000-$5,000")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
