#!/usr/bin/env python3
"""
Show Ready-to-Trade Setups
Displays all 7 qualified tokens with exact entry/exit levels
"""

import json
from database import ContractDatabase
from datetime import datetime

class ReadyTrades:
    def __init__(self):
        self.db = ContractDatabase()
        
    def get_qualified_tokens(self):
        """Get the 7 qualified tokens for trading."""
        all_contracts = self.db.get_all_contracts(limit=100)
        qualified = []
        
        for contract in all_contracts:
            analysis = self.db.get_analysis(contract["contract_address"])
            if not analysis:
                continue
            
            risk = analysis.get("overall_risk_score", 100)
            liq = analysis.get("liquidity_usd", 0)
            mc = analysis.get("market_cap", 0)
            vol = analysis.get("volume_24h", 0)
            
            # Relaxed criteria for ready trades
            if risk <= 40 and liq >= 100000 and mc >= 100000:
                qualified.append(analysis)
        
        # Sort by risk score (best first)
        qualified.sort(key=lambda x: x.get("overall_risk_score", 50))
        return qualified[:7]
    
    def calculate_trade_levels(self, analysis):
        """Calculate entry, stop, and target levels."""
        price = analysis.get("current_price", 0)
        risk = analysis.get("overall_risk_score", 50)
        
        if price <= 0:
            return None
        
        # Determine parameters based on risk
        if risk <= 28:
            stop_pct = 0.015  # 1.5%
            target_pct = 0.03  # 3%
            position = 2.5
            confidence = "HIGH"
            win_rate = 65
        elif risk <= 32:
            stop_pct = 0.018  # 1.8%
            target_pct = 0.03  # 3%
            position = 2.5
            confidence = "HIGH"
            win_rate = 62
        elif risk <= 35:
            stop_pct = 0.02  # 2%
            target_pct = 0.03  # 3%
            position = 2.0
            confidence = "MEDIUM"
            win_rate = 58
        else:
            stop_pct = 0.025  # 2.5%
            target_pct = 0.03  # 3%
            position = 1.5
            confidence = "MEDIUM"
            win_rate = 55
        
        entry = price
        stop = price * (1 - stop_pct)
        target = price * (1 + target_pct)
        rr = target_pct / stop_pct
        
        # Calculate potential profit/loss on $10K portfolio
        portfolio = 10000
        position_size = portfolio * (position / 100)
        potential_profit = position_size * target_pct
        potential_loss = position_size * stop_pct
        
        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "stop_pct": stop_pct * 100,
            "target_pct": target_pct * 100,
            "rr": rr,
            "position": position,
            "confidence": confidence,
            "win_rate": win_rate,
            "position_size_usd": position_size,
            "potential_profit": potential_profit,
            "potential_loss": potential_loss
        }
    
    def print_trade_card(self, analysis, setup, rank):
        """Print a formatted trade card."""
        addr = analysis.get("contract_address", "")
        symbol = analysis.get("token_symbol", "UNKNOWN")
        risk = analysis.get("overall_risk_score", 50)
        liq = analysis.get("liquidity_usd", 0)
        mc = analysis.get("market_cap", 0)
        vol = analysis.get("volume_24h", 0)
        price_change = analysis.get("price_change_24h", 0)
        
        # Tier emoji
        if risk <= 28:
            tier = "💎 S-TIER"
        elif risk <= 32:
            tier = "🥇 A-TIER"
        elif risk <= 35:
            tier = "🥈 A-TIER"
        else:
            tier = "🥉 B-TIER"
        
        print(f"\n{'='*80}")
        print(f"TRADE #{rank}: {tier} | {symbol}")
        print(f"{'='*80}")
        print(f"Contract: {addr}")
        print(f"Risk Score: {risk}/100 | Confidence: {setup['confidence']} | Est. Win Rate: {setup['win_rate']}%")
        
        print(f"\n📊 Market Data:")
        print(f"  Current Price: ${analysis.get('current_price', 0):.6f}")
        print(f"  24h Change: {price_change:+.2f}%")
        print(f"  Market Cap: ${mc:,.2f}")
        print(f"  Liquidity: ${liq:,.2f}")
        print(f"  24h Volume: ${vol:,.2f}")
        
        print(f"\n🎯 Trade Levels:")
        print(f"  🚪 ENTRY:  ${setup['entry']:.6f}")
        print(f"  🛑 STOP:   ${setup['stop']:.6f} (-{setup['stop_pct']:.1f}%)")
        print(f"  ✅ TARGET: ${setup['target']:.6f} (+{setup['target_pct']:.1f}%)")
        print(f"  📈 R:R Ratio: 1:{setup['rr']:.1f}")
        
        print(f"\n💰 Position Sizing ($10K Portfolio):")
        print(f"  Position Size: {setup['position']}% = ${setup['position_size_usd']:.2f}")
        print(f"  Potential Profit: +${setup['potential_profit']:.2f}")
        print(f"  Max Loss: -${setup['potential_loss']:.2f}")
        
        # Green/red flags
        green_flags = json.loads(analysis.get("green_flags", "[]"))
        red_flags = json.loads(analysis.get("red_flags", "[]"))
        
        print(f"\n✅ Safety Checks ({len(green_flags)} green flags):")
        for flag in green_flags[:3]:
            print(f"  ✓ {flag}")
        
        if red_flags:
            print(f"\n⚠️  Risks ({len(red_flags)} red flags):")
            for flag in red_flags:
                print(f"  ! {flag}")
        
        print(f"\n📝 Execution Plan:")
        print(f"  1. Enter at ${setup['entry']:.6f}")
        print(f"  2. Set stop loss at ${setup['stop']:.6f} immediately")
        print(f"  3. Set take profit at ${setup['target']:.6f}")
        print(f"  4. If price reaches ${(setup['entry'] + setup['target'])/2:.6f}, move stop to breakeven")
        print(f"  5. Close position if target hit OR max 4-6 hours")
        
        print(f"\n⏰ Best Time to Trade:")
        if price_change < -5:
            print(f"  🟢 GOOD: Price is down {abs(price_change):.1f}% - potential bounce")
        elif price_change > 10:
            print(f"  🟡 CAUTION: Price up {price_change:.1f}% - wait for pullback")
        else:
            print(f"  🟢 GOOD: Price stable ({price_change:+.1f}%) - good entry zone")

def main():
    print("="*80)
    print("🚀 READY TO TRADE - LIVE SETUPS")
    print("="*80)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⚠️  These are real market prices - verify before trading!")
    print()
    
    trades = ReadyTrades()
    tokens = trades.get_qualified_tokens()
    
    if not tokens:
        print("❌ No qualified tokens found")
        return
    
    print(f"✅ Found {len(tokens)} tokens ready for trading\n")
    
    # Print each trade
    for i, token in enumerate(tokens, 1):
        setup = trades.calculate_trade_levels(token)
        if setup:
            trades.print_trade_card(token, setup, i)
    
    # Summary table
    print("\n" + "="*100)
    print("📊 QUICK REFERENCE TABLE")
    print("="*100)
    print(f"{'#':<4}{'Token':<12}{'Risk':<8}{'Entry':<14}{'Stop':<14}{'Target':<14}{'R:R':<8}{'Size':<8}{'P/L':<20}")
    print("-"*100)
    
    for i, token in enumerate(tokens, 1):
        setup = trades.calculate_trade_levels(token)
        if not setup:
            continue
        
        symbol = token.get("token_symbol", "UNK")[:10]
        risk = f"{token.get('overall_risk_score')}/100"
        entry = f"${setup['entry']:.6f}"
        stop = f"${setup['stop']:.6f}"
        target = f"${setup['target']:.6f}"
        rr = f"1:{setup['rr']:.1f}"
        size = f"{setup['position']}%"
        pl = f"+${setup['potential_profit']:.0f}/-${setup['potential_loss']:.0f}"
        
        print(f"{i:<4}{symbol:<12}{risk:<8}{entry:<14}{stop:<14}{target:<14}{rr:<8}{size:<8}{pl:<20}")
    
    print("="*100)
    
    # Priority ranking
    print("\n" + "="*80)
    print("🎯 TRADE PRIORITY RANKING")
    print("="*80)
    print("\n1️⃣  START WITH THESE (Highest Confidence):")
    for i, token in enumerate(tokens[:2], 1):
        risk = token.get("overall_risk_score", 50)
        print(f"   {i}. {token.get('token_symbol', 'UNKNOWN')} (Risk: {risk}) - Safest setups")
    
    print("\n2️⃣  ADD THESE NEXT (Good Opportunities):")
    for i, token in enumerate(tokens[2:5], 1):
        risk = token.get("overall_risk_score", 50)
        print(f"   {i}. {token.get('token_symbol', 'UNKNOWN')} (Risk: {risk})")
    
    print("\n3️⃣  USE WITH CAUTION (Higher Risk):")
    for i, token in enumerate(tokens[5:], 1):
        risk = token.get("overall_risk_score", 50)
        print(f"   {i}. {token.get('token_symbol', 'UNKNOWN')} (Risk: {risk}) - Smaller size")
    
    # Daily schedule
    print("\n" + "="*80)
    print("📅 SUGGESTED DAILY SCHEDULE")
    print("="*80)
    print("""
MORNING (9-11 AM EST):
  • Check overnight price action
  • Set alerts for entry prices
  • Review any news

MIDDAY (12-2 PM EST):
  • Look for entry setups
  • Enter 1-2 positions max
  • Set stops immediately

AFTERNOON (3-4 PM EST):
  • Manage open positions
  • Move stops to breakeven if profitable
  • Close positions approaching target

EVENING (5-6 PM EST):
  • Close all positions (don't hold overnight)
  • Review day's trades
  • Plan tomorrow's setups
    """)
    
    print("="*80)
    print("\n💡 Remember:")
    print("  • Never risk more than 2.5% per trade")
    print("  • Always use stop losses")
    print("  • Take profits at target - don't get greedy")
    print("  • Track every trade in a journal")
    print("="*80)

if __name__ == "__main__":
    main()
