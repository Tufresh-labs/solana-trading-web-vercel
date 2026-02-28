#!/usr/bin/env python3
"""
Pump.fun Token Screener
Filters and ranks Pump.fun tokens by success potential
"""

import asyncio
import json
import sys
from typing import List, Dict, Optional
from database import ContractDatabase
from analyze_contract import SolanaContractAnalyzer

# Success criteria based on top performers
SUCCESS_CRITERIA = {
    "max_risk_score": 40,
    "min_liquidity": 100000,
    "min_market_cap": 100000,
    "must_have_mint_revoked": True,
    "must_have_freeze_revoked": True,
    "max_red_flags": 2
}

class PumpFunScreener:
    def __init__(self):
        self.db = ContractDatabase()
    
    def is_potential_gem(self, analysis: Dict) -> bool:
        """Check if token matches gem criteria."""
        # Check risk score
        if analysis.get("overall_risk_score", 100) > SUCCESS_CRITERIA["max_risk_score"]:
            return False
        
        # Check liquidity
        if analysis.get("liquidity_usd", 0) < SUCCESS_CRITERIA["min_liquidity"]:
            return False
        
        # Check market cap
        if analysis.get("market_cap", 0) < SUCCESS_CRITERIA["min_market_cap"]:
            return False
        
        # Check authorities
        green_flags = json.loads(analysis.get("green_flags", "[]"))
        
        if SUCCESS_CRITERIA["must_have_mint_revoked"]:
            if not any("Mint authority revoked" in f for f in green_flags):
                return False
        
        if SUCCESS_CRITERIA["must_have_freeze_revoked"]:
            if not any("Freeze authority revoked" in f for f in green_flags):
                return False
        
        # Check red flags
        red_flags = json.loads(analysis.get("red_flags", "[]"))
        if len(red_flags) > SUCCESS_CRITERIA["max_red_flags"]:
            return False
        
        return True
    
    def calculate_gem_score(self, analysis: Dict) -> float:
        """Calculate a gem score (higher = better)."""
        score = 0.0
        
        # Risk score contribution (lower is better)
        risk = analysis.get("overall_risk_score", 50)
        score += (50 - risk) * 2  # Max 100 points
        
        # Liquidity contribution (higher is better, up to $2M)
        liquidity = analysis.get("liquidity_usd", 0)
        score += min(liquidity / 20000, 100)  # Max 100 points for $2M+ liq
        
        # Volume/Liquidity ratio contribution (1-3x is ideal)
        volume = analysis.get("volume_24h", 0)
        vol_liq = volume / liquidity if liquidity > 0 else 0
        if 1 <= vol_liq <= 3:
            score += 50  # Ideal range
        elif vol_liq < 1:
            score += vol_liq * 50  # Less points for low volume
        else:
            score += max(0, 50 - (vol_liq - 3) * 10)  # Penalty for very high
        
        # Price stability contribution (moderate change is good)
        price_change = abs(analysis.get("price_change_24h", 0))
        if price_change < 10:
            score += 50  # Stable
        elif price_change < 50:
            score += 30  # Some movement
        elif price_change < 100:
            score += 10  # High volatility
        else:
            score += 0  # Extreme volatility
        
        # Market cap contribution
        mcap = analysis.get("market_cap", 0)
        if 100000 <= mcap <= 10000000:  # $100K - $10M sweet spot
            score += 50
        elif mcap > 10000000:
            score += 30  # Large cap, less explosive potential
        
        return score
    
    def screen_database(self) -> List[Dict]:
        """Screen all tokens in database for gems."""
        print("🔍 Screening database for Pump.fun gems...")
        
        all_contracts = self.db.get_all_contracts(limit=100)
        gems = []
        
        for contract in all_contracts:
            analysis = self.db.get_analysis(contract["contract_address"])
            if not analysis:
                continue
            
            if self.is_potential_gem(analysis):
                gem_score = self.calculate_gem_score(analysis)
                gems.append({
                    "analysis": analysis,
                    "gem_score": gem_score
                })
        
        # Sort by gem score
        gems.sort(key=lambda x: x["gem_score"], reverse=True)
        
        return gems
    
    def compare_to_originals(self, analysis: Dict, original_5: List[str]) -> Dict:
        """Compare token to our original 5 successful tokens."""
        comparisons = {}
        
        for addr in original_5:
            orig = self.db.get_analysis(addr)
            if not orig:
                continue
            
            # Calculate similarity
            similarity = 0
            
            # Risk score similarity
            risk_diff = abs(analysis.get("overall_risk_score", 50) - orig.get("overall_risk_score", 50))
            similarity += max(0, 30 - risk_diff)
            
            # Liquidity similarity (within 2x factor)
            liq_ratio = analysis.get("liquidity_usd", 1) / max(orig.get("liquidity_usd", 1), 1)
            if 0.5 <= liq_ratio <= 2:
                similarity += 20
            elif 0.2 <= liq_ratio <= 5:
                similarity += 10
            
            # Volume similarity
            vol_ratio = analysis.get("volume_24h", 1) / max(orig.get("volume_24h", 1), 1)
            if 0.5 <= vol_ratio <= 2:
                similarity += 20
            elif 0.2 <= vol_ratio <= 5:
                similarity += 10
            
            # Green flags similarity
            analysis_green = len(json.loads(analysis.get("green_flags", "[]")))
            orig_green = len(json.loads(orig.get("green_flags", "[]")))
            if analysis_green == orig_green:
                similarity += 15
            elif abs(analysis_green - orig_green) <= 1:
                similarity += 10
            
            # Red flags similarity
            analysis_red = len(json.loads(analysis.get("red_flags", "[]")))
            orig_red = len(json.loads(orig.get("red_flags", "[]")))
            if analysis_red == orig_red:
                similarity += 15
            elif abs(analysis_red - orig_red) <= 1:
                similarity += 10
            
            comparisons[addr[:20]] = similarity
        
        return comparisons

def print_gem_report(gem: Dict, rank: int, comparisons: Dict):
    """Print detailed gem report."""
    analysis = gem["analysis"]
    
    print(f"\n{'=' * 80}")
    print(f"💎 GEM #{rank}: {analysis.get('token_symbol', 'UNKNOWN')}")
    print(f"   {analysis.get('contract_address')}")
    print(f"{'=' * 80}")
    
    print(f"\n⭐ Gem Score: {gem['gem_score']:.0f}/400")
    
    print(f"\n💰 Market Data:")
    print(f"   Price: ${analysis.get('current_price', 0):.6f}")
    print(f"   24h Change: {analysis.get('price_change_24h', 0):+.2f}%")
    print(f"   Market Cap: ${analysis.get('market_cap', 0):,.2f}")
    print(f"   Liquidity: ${analysis.get('liquidity_usd', 0):,.2f}")
    print(f"   24h Volume: ${analysis.get('volume_24h', 0):,.2f}")
    vol_liq = analysis.get('volume_24h', 0) / analysis.get('liquidity_usd', 1)
    print(f"   Vol/Liq Ratio: {vol_liq:.2f}x")
    
    risk = analysis.get('overall_risk_score', 50)
    risk_emoji = "🟢" if risk <= 30 else "🟡" if risk <= 40 else "🟠"
    print(f"\n{risk_emoji} Risk Score: {risk}/100")
    
    green_flags = json.loads(analysis.get('green_flags', '[]'))
    red_flags = json.loads(analysis.get('red_flags', '[]'))
    
    print(f"\n✅ Green Flags ({len(green_flags)}):")
    for flag in green_flags:
        print(f"   • {flag}")
    
    if red_flags:
        print(f"\n⚠️ Red Flags ({len(red_flags)}):")
        for flag in red_flags:
            print(f"   • {flag}")
    
    if comparisons:
        print(f"\n📊 Similarity to Original 5:")
        for addr, sim in sorted(comparisons.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(sim / 5) + "░" * (20 - int(sim / 5))
            print(f"   {addr}...: [{bar}] {sim:.0f}%")

def main():
    # Original 5 contract addresses
    original_5 = [
        "4yDSFNMitxy6waXPTkPyyVvbbQSiqe7zD1VxnzEypump",
        "NV2RYH954cTJ3ckFUpvfqaQXU4ARqqDH3562nFSpump",
        "412zDygnwP9DzitnQVgRKUFFTDmrYScFch6P2k39pump",
        "4fSWEw2wbYEUCcMtitzmeGUfqinoafXxkhqZrA9Gpump",
        "Cm6fNnMk7NfzStP9CZpsQA2v3jjzbcYGAxdJySmHpump"
    ]
    
    screener = PumpFunScreener()
    
    print("=" * 80)
    print("💎 PUMP.FUN GEM SCREENER")
    print("=" * 80)
    print("\n📋 Screening Criteria:")
    print(f"   • Max Risk Score: {SUCCESS_CRITERIA['max_risk_score']}/100")
    print(f"   • Min Liquidity: ${SUCCESS_CRITERIA['min_liquidity']:,.0f}")
    print(f"   • Min Market Cap: ${SUCCESS_CRITERIA['min_market_cap']:,.0f}")
    print(f"   • Mint Authority: Revoked")
    print(f"   • Freeze Authority: Revoked")
    print(f"   • Max Red Flags: {SUCCESS_CRITERIA['max_red_flags']}")
    print()
    
    gems = screener.screen_database()
    
    if not gems:
        print("❌ No gems found matching criteria")
        print("\n💡 Try analyzing more contracts to find gems")
        return
    
    print(f"✅ Found {len(gems)} potential gems\n")
    
    # Print detailed reports for top gems
    for i, gem in enumerate(gems[:10], 1):
        comparisons = screener.compare_to_originals(gem["analysis"], original_5)
        print_gem_report(gem, i, comparisons)
    
    # Summary table
    print("\n" + "=" * 100)
    print("📊 GEM RANKINGS")
    print("=" * 100)
    print(f"{'Rank':<6}{'Symbol':<12}{'Gem Score':<12}{'Risk':<10}{'Liquidity':<15}{'Market Cap':<15}{'24h %':<10}")
    print("-" * 100)
    
    for i, gem in enumerate(gems, 1):
        a = gem["analysis"]
        symbol = a.get('token_symbol', 'UNKNOWN')[:11]
        score = f"{gem['gem_score']:.0f}"
        risk = f"{a.get('overall_risk_score', 0)}/100"
        liq = f"${a.get('liquidity_usd', 0):,.0f}"
        mcap = f"${a.get('market_cap', 0):,.0f}"
        change = f"{a.get('price_change_24h', 0):+.1f}%"
        
        print(f"{i:<6}{symbol:<12}{score:<12}{risk:<10}{liq:<15}{mcap:<15}{change:<10}")
    
    print("=" * 100)
    
    # Best picks
    print("\n" + "=" * 80)
    print("🎯 TOP RECOMMENDATIONS")
    print("=" * 80)
    
    if gems:
        best = gems[0]
        a = best["analysis"]
        print(f"\n🏆 #1 PICK: {a.get('contract_address')}")
        print(f"   Gem Score: {best['gem_score']:.0f}/400")
        print(f"   Risk: {a.get('overall_risk_score')}/100")
        print(f"   Liquidity: ${a.get('liquidity_usd'):,.2f}")
        print(f"   Market Cap: ${a.get('market_cap'):,.2f}")
        print(f"\n   💡 This token has the BEST combination of:")
        print(f"      • Low risk score")
        print(f"      • High liquidity (easy entry/exit)")
        print(f"      • Good market cap")
        print(f"      • Safe contract (authorities revoked)")
        
        if len(gems) >= 3:
            print(f"\n📋 Full Watchlist (Top 3):")
            for i, g in enumerate(gems[:3], 1):
                addr = g["analysis"].get("contract_address", "")[:30]
                print(f"   {i}. {addr}... (Score: {g['gem_score']:.0f})")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
