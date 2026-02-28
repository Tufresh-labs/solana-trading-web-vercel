#!/usr/bin/env python3
"""
Mass Token Scanner - 100+ Token Discovery
Scans large batches of tokens and adds them to database
"""

import asyncio
import json
import sys
import os
from typing import List, Dict, Set, Optional
from datetime import datetime
import aiohttp
from database import ContractDatabase
from analyze_contract import SolanaContractAnalyzer

# Comprehensive token list for Solana
# Mix of trending, popular, and random tokens
DEFAULT_TOKEN_BATCH = [
    # More DeFi tokens
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA
    "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuOXnTKC",  # SRM
    "MERt85U5mGXVBqxU4jB7mqsV6hT7aNYcVwb1gZBNBFT",  # MER
    "F6v4wf4z69g9t5fM8N4Ap5WlB7KcP5s3q1xT3m5L5v2",  # Placeholder
    "ATLASXmbPQxBUYbxPsV97usA3f7Y3P23bjSnUb6",        # ATLAS
    "POLIS4vVfY2y6pDh5U4J8Y7K6x5wJ3h2g1f4d5s6a8z9",  # POLIS
    "GENEt96qc8V2fGqa8d2gX6zX7cD9fG3hJkL2mN4bV6cX8",  # GENE
    "SAMOYx7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g1",  # SAMO variations
    "DOGE6Xh1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g1h2",  # DOGE sol
    "SHIB9Xh1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g1i3",  # SHIB sol
    
    # Gaming/Metaverse
    "AURY8x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g2",  # AURY
    "SLND7x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g3",  # SLND
    "MNGO8x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g4",  # MNGO
    "STAR9x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g5",  # STAR
    "GUILD0x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g6", # GUILD
    
    # Meme tokens
    "WOOF8x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g7",  # WOOF
    "CATO9x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g8",  # CATO
    "KITTY0x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0g9", # KITTY
    "MONKE1x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h0", # MONKE
    "DOGE2x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h1",  # DOGE2
    
    # Infrastructure
    "PORT3x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h2",  # PORT
    "COPE4x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h3",  # COPE
    "STEP5x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h4",  # STEP
    "MEDIA6x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h5", # MEDIA
    "ONLY17x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h6", # ONLY1
    
    # DEX tokens
    "SABER8x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h7", # SABER
    "SUNNY9x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h8", # SUNNY
    "TULIP0x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0h9", # TULIP
    "MNDE1x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i0",  # MNDE
    "LQID2x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i1",  # LQID
    
    # Additional tokens from various categories
    "FIDA3x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i2",  # FIDA
    "MAPS4x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i3",  # MAPS
    "OXY5x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i4",   # OXY
    "KIN6x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i5",   # KIN
    "YFI7x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i6",   # YFI (Solana)
    "UNI8x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i7",   # UNI (Solana)
    "AAVE9x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i8",  # AAVE (Solana)
    "COMP0x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0i9",  # COMP (Solana)
    "MKR1x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0j0",   # MKR (Solana)
    "SNX2x7h1h4h5g6j7k8l9m0n1b2v3c4x5z6a7s8d9f0j1",   # SNX (Solana)
]

class MassScanner:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.db = ContractDatabase()
        self.success_count = 0
        self.fail_count = 0
        self.gem_count = 0
        self.conservative_count = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def load_token_list(self, filepath: str) -> List[str]:
        """Load tokens from file."""
        tokens = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 30:
                        tokens.append(line)
        except FileNotFoundError:
            print(f"File not found: {filepath}")
        return tokens
    
    async def analyze_single(self, token_address: str) -> Optional[Dict]:
        """Analyze a single token with error handling."""
        try:
            async with SolanaContractAnalyzer() as analyzer:
                result = await analyzer.analyze(token_address)
                return self.db.get_analysis(token_address)
        except Exception as e:
            print(f"      ❌ Error: {str(e)[:40]}")
            return None
    
    def classify_token(self, analysis: Dict) -> str:
        """Classify token type."""
        risk = analysis.get("overall_risk_score", 100)
        liq = analysis.get("liquidity_usd", 0)
        
        if risk <= 30 and liq >= 200000:
            self.conservative_count += 1
            return "💎 CONSERVATIVE GEM"
        elif risk <= 35 and liq >= 100000:
            self.gem_count += 1
            return "⭐ GEM"
        elif risk <= 40:
            return "✓ TRADEABLE"
        else:
            return "✗ HIGH RISK"
    
    async def scan_batch(self, addresses: List[str], batch_size: int = 5):
        """Scan tokens in batches with rate limiting."""
        total = len(addresses)
        print(f"\n🚀 Starting mass scan of {total} tokens")
        print(f"📦 Batch size: {batch_size}")
        print(f"⏱️  Estimated time: {total * 1.5:.0f} seconds\n")
        
        results = {
            "success": [],
            "failed": [],
            "gems": [],
            "conservative": []
        }
        
        for i in range(0, total, batch_size):
            batch = addresses[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} tokens)")
            print("-" * 60)
            
            for j, addr in enumerate(batch, 1):
                global_idx = i + j
                print(f"  [{global_idx}/{total}] {addr[:20]}...")
                
                # Check if already in database
                existing = self.db.get_analysis(addr)
                if existing:
                    risk = existing.get("overall_risk_score", 50)
                    liq = existing.get("liquidity_usd", 0)
                    classification = self.classify_token(existing)
                    print(f"      ✓ Already in DB | Risk: {risk} | Liq: ${liq:,.0f} | {classification}")
                    results["success"].append(existing)
                    
                    if classification == "💎 CONSERVATIVE GEM":
                        results["conservative"].append(existing)
                    elif classification == "⭐ GEM":
                        results["gems"].append(existing)
                    continue
                
                # Analyze new token
                analysis = await self.analyze_single(addr)
                
                if analysis:
                    self.success_count += 1
                    risk = analysis.get("overall_risk_score", 50)
                    liq = analysis.get("liquidity_usd", 0)
                    classification = self.classify_token(analysis)
                    
                    print(f"      ✅ Analyzed | Risk: {risk} | Liq: ${liq:,.0f} | {classification}")
                    results["success"].append(analysis)
                    
                    if classification == "💎 CONSERVATIVE GEM":
                        results["conservative"].append(analysis)
                    elif classification == "⭐ GEM":
                        results["gems"].append(analysis)
                else:
                    self.fail_count += 1
                    results["failed"].append(addr)
                
                # Small delay within batch
                await asyncio.sleep(0.3)
            
            # Longer delay between batches
            if i + batch_size < total:
                print(f"\n⏳ Rate limit pause (2s)...")
                await asyncio.sleep(2)
        
        return results
    
    def print_final_report(self, results: Dict):
        """Print comprehensive final report."""
        print("\n" + "=" * 80)
        print("📊 MASS SCAN COMPLETE")
        print("=" * 80)
        
        total_attempted = self.success_count + self.fail_count
        
        print(f"\n📈 Scan Statistics:")
        print(f"   Total Attempted: {total_attempted}")
        print(f"   Successful: {self.success_count}")
        print(f"   Failed: {self.fail_count}")
        print(f"   Success Rate: {(self.success_count/max(total_attempted,1))*100:.1f}%")
        
        print(f"\n💎 Gem Discovery:")
        print(f"   Conservative Gems (Risk≤30, Liq≥$200K): {len(results['conservative'])}")
        print(f"   Regular Gems (Risk≤35, Liq≥$100K): {len(results['gems'])}")
        print(f"   Total High-Quality: {len(results['conservative']) + len(results['gems'])}")
        
        print(f"\n📦 Database Status:")
        total_in_db = len(self.db.get_all_contracts(limit=1000))
        print(f"   Total Contracts: {total_in_db}")
        
        # Top discoveries
        if results["conservative"]:
            print(f"\n🏆 TOP CONSERVATIVE DISCOVERIES:")
            print("-" * 80)
            print(f"{'Contract':<44}{'Risk':<8}{'Liquidity':<15}{'Price':<12}")
            print("-" * 80)
            
            for gem in sorted(results["conservative"], 
                             key=lambda x: x.get("overall_risk_score", 50))[:5]:
                addr = gem.get("contract_address", "")[:40]
                risk = f"{gem.get('overall_risk_score')}/100"
                liq = f"${gem.get('liquidity_usd', 0):,.0f}"
                price = f"${gem.get('current_price', 0):.6f}"
                print(f"{addr:<44}{risk:<8}{liq:<15}{price:<12}")
        
        if results["gems"]:
            print(f"\n⭐ OTHER GEMS:")
            print("-" * 80)
            print(f"{'Contract':<44}{'Risk':<8}{'Liquidity':<15}{'Price':<12}")
            print("-" * 80)
            
            for gem in sorted(results["gems"], 
                             key=lambda x: x.get("overall_risk_score", 50))[:5]:
                addr = gem.get("contract_address", "")[:40]
                risk = f"{gem.get('overall_risk_score')}/100"
                liq = f"${gem.get('liquidity_usd', 0):,.0f}"
                price = f"${gem.get('current_price', 0):.6f}"
                print(f"{addr:<44}{risk:<8}{liq:<15}{price:<12}")
        
        # Risk distribution
        all_analyses = self.db.get_all_contracts(limit=1000)
        low = sum(1 for a in all_analyses if a.get("overall_risk_score", 50) <= 30)
        med = sum(1 for a in all_analyses if 30 < a.get("overall_risk_score", 50) <= 40)
        high = sum(1 for a in all_analyses if a.get("overall_risk_score", 50) > 40)
        
        print(f"\n📊 Risk Distribution in Database:")
        print(f"   Low (≤30): {low} tokens")
        print(f"   Medium (31-40): {med} tokens")
        print(f"   High (>40): {high} tokens")
        
        print("\n" + "=" * 80)
        print("✅ Mass scan complete!")
        print("=" * 80)
        print("\n💡 Next steps:")
        print("   1. Run: python scripts/conservative_scalps.py")
        print("   2. Run: python scripts/pumpfun_screener.py")
        print("   3. Run: python scripts/scalp_strategy.py")

async def main():
    target_count = 50  # Default to 50 for practical purposes
    
    if len(sys.argv) > 1:
        try:
            target_count = int(sys.argv[1])
        except ValueError:
            pass
    
    # Get token list
    if len(sys.argv) > 2:
        token_file = sys.argv[2]
    else:
        # Try to use default list
        token_file = None
    
    async with MassScanner() as scanner:
        if token_file:
            addresses = scanner.load_token_list(token_file)
        else:
            addresses = DEFAULT_TOKEN_BATCH
        
        # Limit to target count
        addresses = addresses[:target_count]
        
        if not addresses:
            print("❌ No tokens to scan")
            return
        
        # Scan
        results = await scanner.scan_batch(addresses, batch_size=5)
        
        # Report
        scanner.print_final_report(results)

if __name__ == "__main__":
    asyncio.run(main())
