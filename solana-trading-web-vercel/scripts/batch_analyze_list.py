#!/usr/bin/env python3
"""
Batch analyze a list of token addresses
"""

import asyncio
import sys
from typing import List
from analyze_contract import SolanaContractAnalyzer
from database import ContractDatabase

# Known active Solana tokens to analyze
TOKEN_LIST = [
    # Popular meme tokens
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # SAMO
    "kinXdEcpDQeHPEuQnqmUgtYykqKGVFq6CeVX5iAHJq6",   # KIN
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC (for comparison)
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY
    "HZ1J1NiDd7hnc7Gs6JZxZTXCTL9YBm42K8kFHnX1WKM2",  # DUST
    "7i5KKsX2weiTkry7jA4ZwSuXGhsSnzQNRYp78pcRCa77",  # PUFF
    "7x8yXZ8Q3QJ5z7Q8z9Q0Q1Q2Q3Q4Q5Q6Q7Q8Q9Q0Q1Q2",  # Placeholder - will skip
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP
    "hntYVBjnqUrWyLgM6R4fA9kdePYt3wzP9Y7kKQyDkPb",  # HNT
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",  # RNDR
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "bSo13r4TkiE4xumwojst13ERQpA7jZo3r1PTN2eNcvk",  # bSOL
    "FwEHyy9eeS3D9j1nD6e5q3L3K3K3K3K3K3K3K3K3K3K3",  # Will skip
]

# Alternative: Read from file
def load_token_list(filepath: str) -> List[str]:
    """Load token addresses from file."""
    tokens = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    tokens.append(line)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    return tokens

async def analyze_tokens(addresses: List[str]):
    """Analyze multiple tokens."""
    db = ContractDatabase()
    
    print("=" * 80)
    print("🚀 BATCH TOKEN ANALYSIS")
    print("=" * 80)
    print(f"\n📊 Analyzing {len(addresses)} tokens...\n")
    
    results = {
        "success": [],
        "failed": [],
        "gems": []
    }
    
    async with SolanaContractAnalyzer() as analyzer:
        for i, addr in enumerate(addresses, 1):
            print(f"[{i}/{len(addresses)}] Analyzing {addr[:20]}...")
            
            # Skip if already in database
            existing = db.get_analysis(addr)
            if existing:
                print(f"    ✓ Already in database (Risk: {existing.get('overall_risk_score')}/100)")
                results["success"].append(existing)
                
                # Check if gem
                if existing.get("overall_risk_score", 100) <= 35 and existing.get("liquidity_usd", 0) >= 100000:
                    results["gems"].append(existing)
                continue
            
            try:
                result = await analyzer.analyze(addr)
                
                # Get from database
                analysis = db.get_analysis(addr)
                if analysis:
                    results["success"].append(analysis)
                    risk = analysis.get("overall_risk_score", 50)
                    liq = analysis.get("liquidity_usd", 0)
                    print(f"    ✅ Success! Risk: {risk}/100 | Liquidity: ${liq:,.0f}")
                    
                    # Check if gem
                    if risk <= 35 and liq >= 100000:
                        results["gems"].append(analysis)
                        print(f"    💎 GEM FOUND!")
                else:
                    results["failed"].append(addr)
                    print(f"    ⚠️ Not saved to database")
                    
            except Exception as e:
                results["failed"].append(addr)
                print(f"    ❌ Failed: {str(e)[:50]}")
            
            # Delay to avoid rate limiting
            await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"\n✅ Successful: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"💎 Gems Found: {len(results['gems'])}")
    
    if results["gems"]:
        print("\n🏆 TOP GEMS:")
        for gem in sorted(results["gems"], key=lambda x: x.get("overall_risk_score", 50)):
            print(f"   • {gem.get('contract_address')[:25]}... | Risk: {gem.get('overall_risk_score')}/100 | Liq: ${gem.get('liquidity_usd'):,.0f}")
    
    print(f"\n📦 Total tokens in database: {len(db.get_all_contracts(limit=1000))}")
    
    return results

def main():
    # Use command line args or default list
    if len(sys.argv) > 1:
        # Check if it's a file
        if sys.argv[1].endswith('.txt'):
            addresses = load_token_list(sys.argv[1])
        else:
            addresses = sys.argv[1:]
    else:
        addresses = TOKEN_LIST
    
    if not addresses:
        print("No token addresses provided")
        print("Usage: python batch_analyze_list.py <address1> <address2> ...")
        print("   or: python batch_analyze_list.py tokens.txt")
        return
    
    asyncio.run(analyze_tokens(addresses))

if __name__ == "__main__":
    main()
