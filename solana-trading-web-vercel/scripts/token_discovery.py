#!/usr/bin/env python3
"""
Token Discovery Engine
Finds and analyzes new tokens from multiple sources
"""

import asyncio
import json
import sys
import os
from typing import List, Dict, Optional, Set
from datetime import datetime
import aiohttp
from database import ContractDatabase
from analyze_contract import SolanaContractAnalyzer

# Multiple sources for token discovery
SOURCES = {
    "dexscreener_trending": "https://api.dexscreener.com/token-pairs/v1/solana/trending",
    "dexscreener_latest": "https://api.dexscreener.com/latest/dex/search?q=solana",
    "jupiter_tokens": "https://token.jup.ag/all",
}

# Token filters
EXCLUDED_SYMBOLS = {
    'USDC', 'USDT', 'SOL', 'BTC', 'ETH', 'BONK', 'JUP', 'RAY', 
    'MSOL', 'WSOL', 'STSOL', 'SCNSOL', 'JSOL',
    'DUST', 'SRM', 'FTT', 'COPE', 'STEP', 'MEDIA'
}

MIN_LIQUIDITY = 5000  # $5k minimum
MIN_VOLUME = 1000     # $1k minimum volume

class TokenDiscovery:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.db = ContractDatabase()
        self.discovered_tokens: Set[str] = set()
        self.analyzed_count = 0
        self.success_count = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _api_call(self, url: str) -> Dict:
        """Make API call with error handling."""
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"  ⚠️ API error: {e}")
            return {}
    
    async def fetch_dexscreener_trending(self, limit: int = 30) -> List[Dict]:
        """Fetch trending tokens from DexScreener."""
        print("🔍 Fetching DexScreener trending...")
        data = await self._api_call(SOURCES["dexscreener_trending"])
        
        tokens = []
        if isinstance(data, list):
            for pair in data[:limit]:
                token_addr = pair.get("baseToken", {}).get("address")
                symbol = pair.get("baseToken", {}).get("symbol", "").upper()
                
                if not token_addr or symbol in EXCLUDED_SYMBOLS:
                    continue
                
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                
                if liquidity < MIN_LIQUIDITY or volume < MIN_VOLUME:
                    continue
                
                tokens.append({
                    "address": token_addr,
                    "symbol": symbol,
                    "name": pair.get("baseToken", {}).get("name", "Unknown"),
                    "source": "dexscreener_trending",
                    "liquidity": liquidity,
                    "volume_24h": volume,
                    "price": float(pair.get("priceUsd", 0)),
                    "price_change": float(pair.get("priceChange", {}).get("h24", 0)),
                    "market_cap": float(pair.get("fdv", 0)),
                    "dex": pair.get("dexId", "unknown")
                })
        
        print(f"  ✓ Found {len(tokens)} trending tokens")
        return tokens
    
    async def fetch_dexscreener_latest(self, limit: int = 30) -> List[Dict]:
        """Fetch latest pairs from DexScreener."""
        print("🔍 Fetching DexScreener latest...")
        data = await self._api_call(SOURCES["dexscreener_latest"])
        
        tokens = []
        if data and "pairs" in data:
            seen = set()
            for pair in data["pairs"][:limit]:
                token_addr = pair.get("baseToken", {}).get("address")
                symbol = pair.get("baseToken", {}).get("symbol", "").upper()
                
                if not token_addr or symbol in EXCLUDED_SYMBOLS or token_addr in seen:
                    continue
                
                seen.add(token_addr)
                
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                
                if liquidity < MIN_LIQUIDITY or volume < MIN_VOLUME:
                    continue
                
                tokens.append({
                    "address": token_addr,
                    "symbol": symbol,
                    "name": pair.get("baseToken", {}).get("name", "Unknown"),
                    "source": "dexscreener_latest",
                    "liquidity": liquidity,
                    "volume_24h": volume,
                    "price": float(pair.get("priceUsd", 0)),
                    "price_change": float(pair.get("priceChange", {}).get("h24", 0)),
                    "market_cap": float(pair.get("fdv", 0)),
                    "dex": pair.get("dexId", "unknown")
                })
        
        print(f"  ✓ Found {len(tokens)} latest tokens")
        return tokens
    
    async def fetch_jupiter_tokens(self, limit: int = 30) -> List[Dict]:
        """Fetch tokens from Jupiter."""
        print("🔍 Fetching Jupiter token list...")
        data = await self._api_call(SOURCES["jupiter_tokens"])
        
        tokens = []
        if isinstance(data, list):
            # Sort by tags (prioritize verified)
            verified = [t for t in data if "verified" in t.get("tags", [])]
            unverified = [t for t in data if "verified" not in t.get("tags", [])]
            
            selected = (verified + unverified)[:limit]
            
            for token in selected:
                symbol = token.get("symbol", "").upper()
                if symbol in EXCLUDED_SYMBOLS:
                    continue
                
                tokens.append({
                    "address": token.get("address"),
                    "symbol": symbol,
                    "name": token.get("name", "Unknown"),
                    "source": "jupiter",
                    "verified": "verified" in token.get("tags", []),
                    "liquidity": 0,  # Will be fetched during analysis
                    "volume_24h": 0,
                    "price": 0,
                    "price_change": 0,
                    "market_cap": 0,
                    "dex": "unknown"
                })
        
        print(f"  ✓ Found {len(tokens)} Jupiter tokens")
        return tokens
    
    async def discover_tokens(self, target_count: int = 15) -> List[Dict]:
        """Discover tokens from all sources."""
        print("\n" + "=" * 80)
        print("🚀 TOKEN DISCOVERY ENGINE")
        print("=" * 80)
        print(f"\n🎯 Target: {target_count} new tokens")
        print(f"📊 Minimum liquidity: ${MIN_LIQUIDITY:,}")
        print(f"📊 Minimum volume: ${MIN_VOLUME:,}")
        print()
        
        all_tokens = []
        
        # Fetch from all sources
        trending = await self.fetch_dexscreener_trending(limit=25)
        latest = await self.fetch_dexscreener_latest(limit=25)
        jupiter = await self.fetch_jupiter_tokens(limit=20)
        
        # Combine and deduplicate
        seen_addresses = set()
        
        for token_list in [trending, latest, jupiter]:
            for token in token_list:
                addr = token.get("address")
                if addr and addr not in seen_addresses:
                    # Check if already in database
                    if not self.db.get_analysis(addr):
                        seen_addresses.add(addr)
                        all_tokens.append(token)
        
        print(f"\n📦 Total unique new tokens: {len(all_tokens)}")
        
        # Limit to target count
        return all_tokens[:target_count]
    
    async def analyze_token(self, token: Dict) -> Optional[Dict]:
        """Analyze a single token."""
        addr = token.get("address")
        symbol = token.get("symbol", "UNKNOWN")
        
        print(f"\n  [{self.analyzed_count + 1}] Analyzing {symbol}...")
        
        try:
            async with SolanaContractAnalyzer() as analyzer:
                result = await analyzer.analyze(addr)
                self.success_count += 1
                
                # Get from database
                return self.db.get_analysis(addr)
        except Exception as e:
            print(f"    ❌ Analysis failed: {e}")
            return None
    
    async def mass_analyze(self, tokens: List[Dict]) -> List[Dict]:
        """Analyze all discovered tokens."""
        print("\n" + "=" * 80)
        print("🔬 MASS ANALYSIS")
        print("=" * 80)
        
        results = []
        
        for token in tokens:
            self.analyzed_count += 1
            analysis = await self.analyze_token(token)
            
            if analysis:
                results.append(analysis)
                risk = analysis.get("overall_risk_score", 50)
                rating = analysis.get("risk_rating", "UNKNOWN")
                print(f"    ✅ Risk: {risk}/100 ({rating})")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return results
    
    def generate_insights(self, analyses: List[Dict]):
        """Generate insights from analyzed tokens."""
        print("\n" + "=" * 80)
        print("📊 DISCOVERY INSIGHTS")
        print("=" * 80)
        
        if not analyses:
            print("No tokens analyzed")
            return
        
        # Statistics
        total = len(analyses)
        low_risk = sum(1 for a in analyses if a.get("overall_risk_score", 50) <= 30)
        medium_risk = sum(1 for a in analyses if 30 < a.get("overall_risk_score", 50) <= 40)
        high_risk = sum(1 for a in analyses if a.get("overall_risk_score", 50) > 40)
        
        avg_liquidity = sum(a.get("liquidity_usd", 0) for a in analyses) / total
        avg_volume = sum(a.get("volume_24h", 0) for a in analyses) / total
        
        mint_revoked = sum(1 for a in analyses 
                          if any("Mint authority revoked" in f 
                                for f in json.loads(a.get("green_flags", "[]"))))
        freeze_revoked = sum(1 for a in analyses 
                            if any("Freeze authority revoked" in f 
                                  for f in json.loads(a.get("green_flags", "[]"))))
        
        print(f"\n📈 Analysis Statistics:")
        print(f"   Total Analyzed: {total}")
        print(f"   Successful: {self.success_count}")
        print(f"   Success Rate: {(self.success_count/self.analyzed_count)*100:.1f}%")
        
        print(f"\n🎯 Risk Distribution:")
        print(f"   Low Risk (≤30): {low_risk} ({low_risk/total*100:.1f}%)")
        print(f"   Medium Risk (31-40): {medium_risk} ({medium_risk/total*100:.1f}%)")
        print(f"   High Risk (>40): {high_risk} ({high_risk/total*100:.1f}%)")
        
        print(f"\n💰 Averages:")
        print(f"   Avg Liquidity: ${avg_liquidity:,.2f}")
        print(f"   Avg Volume: ${avg_volume:,.2f}")
        
        print(f"\n🔒 Security:")
        print(f"   Mint Revoked: {mint_revoked}/{total} ({mint_revoked/total*100:.1f}%)")
        print(f"   Freeze Revoked: {freeze_revoked}/{total} ({freeze_revoked/total*100:.1f}%)")
        
        # Find gems
        gems = [a for a in analyses 
                if a.get("overall_risk_score", 100) <= 35 
                and a.get("liquidity_usd", 0) >= 100000]
        
        print(f"\n💎 Gems Found: {len(gems)}")
        for gem in sorted(gems, key=lambda x: x.get("overall_risk_score", 50)):
            print(f"   • {gem.get('contract_address')[:20]}... | Risk: {gem.get('overall_risk_score')}/100 | Liq: ${gem.get('liquidity_usd'):,.0f}")

async def main():
    target = 10
    if len(sys.argv) > 1:
        try:
            target = int(sys.argv[1])
        except ValueError:
            pass
    
    async with TokenDiscovery() as discovery:
        # Discover tokens
        tokens = await discovery.discover_tokens(target_count=target)
        
        if not tokens:
            print("\n❌ No new tokens found")
            return
        
        # Analyze them
        results = await discovery.mass_analyze(tokens)
        
        # Generate insights
        discovery.generate_insights(results)
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ DISCOVERY COMPLETE")
        print("=" * 80)
        print(f"\n📊 Database now contains {len(discovery.db.get_all_contracts(limit=1000))} tokens")
        print("\n💡 Run 'python scripts/pumpfun_screener.py' to find the best gems")
        print("💡 Run 'python scripts/scalp_strategy.py' to get trading setups")

if __name__ == "__main__":
    asyncio.run(main())
