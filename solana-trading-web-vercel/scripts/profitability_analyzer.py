#!/usr/bin/env python3
"""
Profitability Analyzer
Analyzes database to find patterns that correlate with profitable tokens
Updates knowledge base with money-making insights
"""

import json
import os
from typing import Dict, List, Tuple
from database import ContractDatabase
from datetime import datetime

class ProfitabilityAnalyzer:
    def __init__(self):
        self.db = ContractDatabase()
        self.analyses = []
        self.profitable_patterns = {}
        self.risk_patterns = {}
    
    def load_all_analyses(self):
        """Load all analyses from database."""
        print("📊 Loading all analyses from database...")
        contracts = self.db.get_all_contracts(limit=1000)
        
        for c in contracts:
            analysis = self.db.get_analysis(c["contract_address"])
            if analysis:
                self.analyses.append(analysis)
        
        print(f"  ✓ Loaded {len(self.analyses)} analyses")
    
    def categorize_by_risk(self) -> Dict[str, List[Dict]]:
        """Categorize tokens by risk level."""
        categories = {
            "low_risk": [],      # ≤30
            "medium_risk": [],   # 31-40
            "high_risk": [],     # 41-60
            "extreme_risk": []   # >60
        }
        
        for a in self.analyses:
            risk = a.get("overall_risk_score", 50)
            if risk <= 30:
                categories["low_risk"].append(a)
            elif risk <= 40:
                categories["medium_risk"].append(a)
            elif risk <= 60:
                categories["high_risk"].append(a)
            else:
                categories["extreme_risk"].append(a)
        
        return categories
    
    def categorize_by_liquidity(self) -> Dict[str, List[Dict]]:
        """Categorize tokens by liquidity."""
        categories = {
            "whale": [],      # >$1M
            "deep": [],       # $500K-$1M
            "healthy": [],    # $100K-$500K
            "moderate": [],   # $50K-$100K
            "shallow": [],    # $10K-$50K
            "micro": []       # <$10K
        }
        
        for a in self.analyses:
            liq = a.get("liquidity_usd", 0)
            if liq > 1000000:
                categories["whale"].append(a)
            elif liq > 500000:
                categories["deep"].append(a)
            elif liq > 100000:
                categories["healthy"].append(a)
            elif liq > 50000:
                categories["moderate"].append(a)
            elif liq > 10000:
                categories["shallow"].append(a)
            else:
                categories["micro"].append(a)
        
        return categories
    
    def analyze_profitable_characteristics(self):
        """Analyze characteristics of potentially profitable tokens."""
        print("\n🔍 Analyzing profitable characteristics...")
        
        # Define "profitable" tokens as low-risk + good liquidity
        profitable = [a for a in self.analyses 
                     if a.get("overall_risk_score", 100) <= 35 
                     and a.get("liquidity_usd", 0) >= 100000]
        
        unprofitable = [a for a in self.analyses 
                       if a.get("overall_risk_score", 100) > 40 
                       or a.get("liquidity_usd", 0) < 50000]
        
        print(f"  📈 Profitable candidates: {len(profitable)}")
        print(f"  📉 Unprofitable candidates: {len(unprofitable)}")
        
        # Analyze patterns
        patterns = {
            "mint_revoked": {"profitable": 0, "unprofitable": 0},
            "freeze_revoked": {"profitable": 0, "unprofitable": 0},
            "healthy_liquidity": {"profitable": 0, "unprofitable": 0},
            "low_vol_liq_ratio": {"profitable": 0, "unprofitable": 0},
            "stable_price": {"profitable": 0, "unprofitable": 0},
            "whale_concentration": {"profitable": 0, "unprofitable": 0},
            "multiple_dex": {"profitable": 0, "unprofitable": 0}
        }
        
        for token in profitable:
            green = json.loads(token.get("green_flags", "[]"))
            red = json.loads(token.get("red_flags", "[]"))
            
            if any("Mint authority revoked" in f for f in green):
                patterns["mint_revoked"]["profitable"] += 1
            if any("Freeze authority revoked" in f for f in green):
                patterns["freeze_revoked"]["profitable"] += 1
            if any("Healthy liquidity" in f for f in green):
                patterns["healthy_liquidity"]["profitable"] += 1
            if any("Listed on multiple DEXs" in f for f in green):
                patterns["multiple_dex"]["profitable"] += 1
            if any("WHALE" in f for f in red):
                patterns["whale_concentration"]["profitable"] += 1
            
            vol = token.get("volume_24h", 0)
            liq = token.get("liquidity_usd", 0)
            if liq > 0 and 0.5 <= vol/liq <= 3:
                patterns["low_vol_liq_ratio"]["profitable"] += 1
            
            if abs(token.get("price_change_24h", 100)) < 30:
                patterns["stable_price"]["profitable"] += 1
        
        for token in unprofitable:
            green = json.loads(token.get("green_flags", "[]"))
            red = json.loads(token.get("red_flags", "[]"))
            
            if any("Mint authority revoked" in f for f in green):
                patterns["mint_revoked"]["unprofitable"] += 1
            if any("Freeze authority revoked" in f for f in green):
                patterns["freeze_revoked"]["unprofitable"] += 1
            if any("Healthy liquidity" in f for f in green):
                patterns["healthy_liquidity"]["unprofitable"] += 1
            if any("Listed on multiple DEXs" in f for f in green):
                patterns["multiple_dex"]["unprofitable"] += 1
            if any("WHALE" in f for f in red):
                patterns["whale_concentration"]["unprofitable"] += 1
            
            vol = token.get("volume_24h", 0)
            liq = token.get("liquidity_usd", 0)
            if liq > 0 and 0.5 <= vol/liq <= 3:
                patterns["low_vol_liq_ratio"]["unprofitable"] += 1
            
            if abs(token.get("price_change_24h", 100)) < 30:
                patterns["stable_price"]["unprofitable"] += 1
        
        return patterns, profitable, unprofitable
    
    def calculate_success_rates(self, patterns: Dict) -> Dict:
        """Calculate success rates for each pattern."""
        rates = {}
        
        for pattern, counts in patterns.items():
            profitable_count = counts["profitable"]
            unprofitable_count = counts["unprofitable"]
            total = profitable_count + unprofitable_count
            
            if total > 0:
                success_rate = (profitable_count / total) * 100
                profitable_pct = (profitable_count / max(len([a for a in self.analyses 
                              if a.get("overall_risk_score", 100) <= 35 and a.get("liquidity_usd", 0) >= 100000]), 1)) * 100
                unprofitable_pct = (unprofitable_count / max(len([a for a in self.analyses 
                                  if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000]), 1)) * 100
                
                rates[pattern] = {
                    "success_rate": success_rate,
                    "profitable_pct": profitable_pct,
                    "unprofitable_pct": unprofitable_pct,
                    "correlation": "POSITIVE" if success_rate > 60 else "NEGATIVE" if success_rate < 40 else "NEUTRAL"
                }
        
        return rates
    
    def generate_money_making_rules(self, rates: Dict) -> List[str]:
        """Generate actionable trading rules."""
        rules = []
        
        # High confidence rules (>70% success rate)
        for pattern, data in rates.items():
            if data["success_rate"] >= 70:
                if pattern == "mint_revoked":
                    rules.append(f"✅ MUST HAVE: Mint authority revoked ({data['success_rate']:.0f}% success rate)")
                elif pattern == "freeze_revoked":
                    rules.append(f"✅ MUST HAVE: Freeze authority revoked ({data['success_rate']:.0f}% success rate)")
                elif pattern == "healthy_liquidity":
                    rules.append(f"✅ MUST HAVE: Liquidity >$100K ({data['success_rate']:.0f}% success rate)")
                elif pattern == "multiple_dex":
                    rules.append(f"✅ PREFER: Listed on multiple DEXs ({data['success_rate']:.0f}% success rate)")
            elif data["success_rate"] <= 40:
                if pattern == "whale_concentration":
                    rules.append(f"⚠️ AVOID IF: Whale concentration >80% (only {data['success_rate']:.0f}% success rate)")
        
        return rules
    
    def update_knowledge_base(self, patterns: Dict, rates: Dict, rules: List[str]):
        """Update the scam patterns JSON with new knowledge."""
        print("\n💾 Updating knowledge base...")
        
        kb_path = os.path.join(
            os.path.dirname(__file__),
            "../references/profitability_patterns.json"
        )
        
        knowledge = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "dataset_stats": {
                "total_tokens_analyzed": len(self.analyses),
                "profitable_candidates": len([a for a in self.analyses if a.get("overall_risk_score", 100) <= 35 and a.get("liquidity_usd", 0) >= 100000]),
                "unprofitable": len([a for a in self.analyses if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000])
            },
            "money_making_rules": rules,
            "pattern_success_rates": rates,
            "profitable_profile": {
                "max_risk_score": 35,
                "min_liquidity": 100000,
                "must_have": ["mint_revoked", "freeze_revoked"],
                "prefer": ["healthy_liquidity", "multiple_dex", "stable_price"],
                "avoid": ["whale_concentration", "high_vol_liq_ratio", "extreme_price_pump"]
            },
            "scalping_best_practices": [
                "Enter on low volatility (price change < 30%)",
                "Use tokens with volume/liquidity ratio 0.5-3x",
                "Prefer tokens with risk score ≤ 35",
                "Scale out: 33% at TP1, 33% at TP2, 34% at TP3",
                "Move stop to breakeven after TP1 hits",
                "Close position if not profitable within max hold time"
            ],
            "position_sizing_guide": {
                "risk_30_and_below": {"size": "3%", "hold_time": "2-6 hours"},
                "risk_31_to_35": {"size": "2.5%", "hold_time": "1-4 hours"},
                "risk_36_to_40": {"size": "2%", "hold_time": "30-90 minutes"},
                "risk_above_40": {"size": "Avoid or 1% max", "hold_time": "15-30 minutes"}
            }
        }
        
        with open(kb_path, 'w') as f:
            json.dump(knowledge, f, indent=2)
        
        print(f"  ✓ Knowledge base saved to {kb_path}")
    
    def print_report(self, patterns: Dict, rates: Dict, rules: List[str], profitable: List[Dict]):
        """Print comprehensive profitability report."""
        print("\n" + "=" * 80)
        print("💰 PROFITABILITY ANALYSIS REPORT")
        print("=" * 80)
        
        # Dataset overview
        risk_cats = self.categorize_by_risk()
        liq_cats = self.categorize_by_liquidity()
        
        print(f"\n📊 DATASET OVERVIEW")
        print(f"   Total Tokens: {len(self.analyses)}")
        print(f"\n   By Risk:")
        for cat, tokens in risk_cats.items():
            print(f"      {cat.replace('_', ' ').title()}: {len(tokens)}")
        print(f"\n   By Liquidity:")
        for cat, tokens in liq_cats.items():
            print(f"      {cat.replace('_', ' ').title()}: {len(tokens)}")
        
        # Pattern analysis
        print(f"\n🔍 PATTERN SUCCESS RATES")
        print("-" * 80)
        print(f"{'Pattern':<25}{'Success Rate':<15}{'Correlation':<15}{'In Profitable':<15}{'In Unprofitable':<15}")
        print("-" * 80)
        
        for pattern, data in sorted(rates.items(), key=lambda x: x[1]["success_rate"], reverse=True):
            print(f"{pattern.replace('_', ' ').title():<25}{data['success_rate']:>6.1f}%{'':<8}{data['correlation']:<15}{data['profitable_pct']:>5.1f}%{'':<9}{data['unprofitable_pct']:>5.1f}%")
        
        # Money making rules
        print(f"\n💎 MONEY-MAKING RULES (From Analysis)")
        print("=" * 80)
        for rule in rules:
            print(f"   {rule}")
        
        # Best candidates
        print(f"\n🏆 TOP PROFITABLE CANDIDATES")
        print("=" * 80)
        print(f"{'Contract':<44}{'Risk':<10}{'Liquidity':<15}{'Price Chg':<12}")
        print("-" * 80)
        
        for token in sorted(profitable, key=lambda x: x.get("overall_risk_score", 50))[:10]:
            addr = token.get("contract_address", "")[:40]
            risk = f"{token.get('overall_risk_score')}/100"
            liq = f"${token.get('liquidity_usd', 0):,.0f}"
            change = f"{token.get('price_change_24h', 0):+.1f}%"
            print(f"{addr:<44}{risk:<10}{liq:<15}{change:<12}")
        
        # Key insights
        print(f"\n📈 KEY INSIGHTS")
        print("=" * 80)
        
        avg_risk_profitable = sum(a.get("overall_risk_score", 0) for a in profitable) / max(len(profitable), 1)
        avg_risk_unprofitable = sum(a.get("overall_risk_score", 0) for a in [a for a in self.analyses if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000]) / max(len([a for a in self.analyses if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000]), 1)
        
        avg_liq_profitable = sum(a.get("liquidity_usd", 0) for a in profitable) / max(len(profitable), 1)
        avg_liq_unprofitable = sum(a.get("liquidity_usd", 0) for a in [a for a in self.analyses if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000]) / max(len([a for a in self.analyses if a.get("overall_risk_score", 100) > 40 or a.get("liquidity_usd", 0) < 50000]), 1)
        
        print(f"   Average Risk (Profitable): {avg_risk_profitable:.1f}/100")
        print(f"   Average Risk (Unprofitable): {avg_risk_unprofitable:.1f}/100")
        print(f"   Average Liquidity (Profitable): ${avg_liq_profitable:,.0f}")
        print(f"   Average Liquidity (Unprofitable): ${avg_liq_unprofitable:,.0f}")
        
        # Recommendations
        print(f"\n💡 STRATEGIC RECOMMENDATIONS")
        print("=" * 80)
        print("   1. Focus on tokens with risk score ≤ 35")
        print("   2. Minimum liquidity: $100,000")
        print("   3. Must have: Mint & Freeze authorities revoked")
        print("   4. Prefer: Volume/Liquidity ratio 0.5-3x")
        print("   5. Avoid: Extreme price pumps (>200% in 24h)")
        print("   6. Use position sizing: 2-3% for low risk, 1-2% for medium risk")
        
        print("=" * 80)

def main():
    analyzer = ProfitabilityAnalyzer()
    analyzer.load_all_analyses()
    
    if len(analyzer.analyses) < 5:
        print("❌ Not enough data for analysis. Need at least 5 tokens.")
        return
    
    patterns, profitable, unprofitable = analyzer.analyze_profitable_characteristics()
    rates = analyzer.calculate_success_rates(patterns)
    rules = analyzer.generate_money_making_rules(rates)
    
    analyzer.print_report(patterns, rates, rules, profitable)
    analyzer.update_knowledge_base(patterns, rates, rules)
    
    print("\n✅ Analysis complete! Knowledge base updated.")

if __name__ == "__main__":
    main()
