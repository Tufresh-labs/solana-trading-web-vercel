#!/usr/bin/env python3
"""
Batch Solana Contract Analysis
Compare multiple contracts and rank them by risk score.
"""

import asyncio
import json
import sys
from typing import List, Dict
from analyze_contract import SolanaContractAnalyzer, print_analysis, AnalysisResult


class BatchAnalyzer:
    def __init__(self):
        self.results: List[AnalysisResult] = []
    
    async def analyze_multiple(self, addresses: List[str]) -> List[AnalysisResult]:
        """Analyze multiple contracts and return sorted results."""
        async with SolanaContractAnalyzer() as analyzer:
            tasks = [analyzer.analyze(addr) for addr in addresses]
            self.results = await asyncio.gather(*tasks)
        
        # Sort by risk score (lower is better)
        return sorted(self.results, key=lambda x: x.overall_risk_score)
    
    def print_comparison(self):
        """Print comparison table of all analyzed contracts."""
        if not self.results:
            print("No contracts analyzed.")
            return
        
        print("\n" + "=" * 100)
        print("📊 BATCH ANALYSIS COMPARISON")
        print("=" * 100)
        print(f"{'Rank':<6}{'Contract':<44}{'Risk Score':<12}{'Rating':<10}{'Red Flags':<12}")
        print("-" * 100)
        
        for i, result in enumerate(self.results, 1):
            emoji = "🟢" if result.risk_rating == "LOW" else \
                    "🟡" if result.risk_rating == "MEDIUM" else \
                    "🟠" if result.risk_rating == "HIGH" else "🔴"
            
            short_addr = f"{result.contract_address[:40]}..."
            print(f"{i:<6}{short_addr:<44}{result.overall_risk_score:<12}{emoji} {result.risk_rating:<8}{len(result.red_flags):<12}")
        
        print("=" * 100)
        
        # Best options
        print("\n🏆 TOP RECOMMENDATIONS (Lowest Risk)")
        low_risk = [r for r in self.results if r.risk_rating in ["LOW", "MEDIUM"]][:3]
        if low_risk:
            for i, result in enumerate(low_risk, 1):
                print(f"  {i}. {result.token_metadata.name} ({result.token_metadata.symbol})")
                print(f"     Address: {result.contract_address}")
                print(f"     Risk Score: {result.overall_risk_score}/100 - {result.risk_rating}")
                print(f"     Risk/Reward: {result.risk_reward_ratio}")
                print()
        else:
            print("  ⚠️ No low-risk contracts found in this batch.")
        
        # High risk warnings
        high_risk = [r for r in self.results if r.risk_rating in ["HIGH", "EXTREME"]]
        if high_risk:
            print("\n⚠️  HIGH RISK CONTRACTS TO AVOID")
            for result in high_risk[:5]:
                print(f"  • {result.contract_address} - Score: {result.overall_risk_score}/100")
    
    def save_report(self, filename: str = "batch_analysis_report.json"):
        """Save batch analysis report."""
        report = {
            "timestamp": self.results[0].timestamp if self.results else "",
            "contracts_analyzed": len(self.results),
            "contracts": [{
                "address": r.contract_address,
                "name": r.token_metadata.name,
                "symbol": r.token_metadata.symbol,
                "risk_score": r.overall_risk_score,
                "risk_rating": r.risk_rating,
                "red_flags": r.red_flags,
                "green_flags": r.green_flags,
                "recommendation": r.recommendation,
                "risk_reward": r.risk_reward_ratio
            } for r in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Full report saved to: {filename}")


def load_contracts_from_file(filepath: str) -> List[str]:
    """Load contract addresses from file."""
    addresses = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                addresses.append(line)
    return addresses


async def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_analyze.py <contract1> <contract2> ...")
        print("   or: python batch_analyze.py --file <contracts.txt>")
        print("\nExample:")
        print("  python batch_analyze.py addr1 addr2 addr3")
        print("  python batch_analyze.py --file my_contracts.txt")
        sys.exit(1)
    
    if sys.argv[1] == '--file':
        if len(sys.argv) < 3:
            print("Please provide a file path")
            sys.exit(1)
        addresses = load_contracts_from_file(sys.argv[2])
    else:
        addresses = sys.argv[1:]
    
    print(f"🔍 Analyzing {len(addresses)} contracts...")
    
    analyzer = BatchAnalyzer()
    await analyzer.analyze_multiple(addresses)
    analyzer.print_comparison()
    analyzer.save_report()


if __name__ == "__main__":
    asyncio.run(main())
