#!/usr/bin/env python3
"""
Pump.fun Token Scanner
Identifies tokens with similar characteristics to successful tokens
Analyzes new/pumping tokens and ranks them by success potential
"""

import asyncio
import json
import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import aiohttp
from database import ContractDatabase
from analyze_contract import SolanaContractAnalyzer

# Success profiles from our top 3 tokens
SUCCESS_PROFILES = {
    "stable_winner": {
        "name": "Stable Winner (like Cm6fNn...)",
        "risk_score_range": (20, 35),
        "liquidity_min": 400000,
        "vol_liq_range": (1.0, 3.0),
        "price_change_range": (-20, 20),
        "must_have": ["mint_revoked", "freeze_revoked"],
        "red_flags_max": 1,
        "green_flags_min": 3
    },
    "pump_continuation": {
        "name": "Pump Continuation (like 412zDy...)",
        "risk_score_range": (30, 40),
        "liquidity_min": 300000,
        "vol_liq_range": (1.0, 5.0),
        "price_change_range": (50, 500),
        "must_have": ["mint_revoked", "freeze_revoked"],
        "red_flags_max": 2,
        "green_flags_min": 3
    },
    "dip_recovery": {
        "name": "Dip Recovery (like NV2RYH...)",
        "risk_score_range": (30, 40),
        "liquidity_min": 400000,
        "vol_liq_range": (1.0, 10.0),
        "price_change_range": (-40, -10),
        "must_have": ["mint_revoked", "freeze_revoked"],
        "red_flags_max": 2,
        "green_flags_min": 3
    }
}

@dataclass
class TokenMatch:
    contract_address: str
    token_name: str
    token_symbol: str
    
    # Analysis data
    risk_score: int
    risk_rating: str
    current_price: float
    price_change_24h: float
    liquidity_usd: float
    volume_24h: float
    market_cap: float
    pairs_count: int
    dex_platform: str
    
    # Flags
    red_flags: List[str]
    green_flags: List[str]
    
    # Similarity scores
    stable_winner_score: float
    pump_continuation_score: float
    dip_recovery_score: float
    overall_similarity: float
    
    # Recommendation
    matched_profile: str
    confidence: str
    recommendation: str

class PumpFunScanner:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.db = ContractDatabase()
        self.dexscreener_api = "https://api.dexscreener.com"
        self.jupiter_api = "https://price.jup.ag/v4"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _dexscreener_call(self, endpoint: str) -> Dict:
        """Make DexScreener API call."""
        url = f"{self.dexscreener_api}{endpoint}"
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"  ⚠️ API error: {e}")
            return {}
    
    async def fetch_trending_solana_tokens(self, limit: int = 50) -> List[Dict]:
        """Fetch trending tokens on Solana."""
        print("🔍 Fetching trending Solana tokens...")
        
        # Get top trending pairs from DexScreener
        data = await self._dexscreener_call("/token-pairs/v1/solana/trending")
        
        if not data or not isinstance(data, list):
            print("  ⚠️ No trending data available")
            return []
        
        # Filter and deduplicate
        seen_addresses = set()
        tokens = []
        
        for pair in data[:limit]:
            token_address = pair.get("baseToken", {}).get("address")
            if not token_address or token_address in seen_addresses:
                continue
            
            seen_addresses.add(token_address)
            
            # Skip known stablecoins and major tokens
            symbol = pair.get("baseToken", {}).get("symbol", "").upper()
            if symbol in ["USDC", "USDT", "SOL", "BTC", "ETH", "BONK", "JUP", "RAY"]:
                continue
            
            tokens.append({
                "address": token_address,
                "symbol": symbol,
                "name": pair.get("baseToken", {}).get("name", "Unknown"),
                "price": float(pair.get("priceUsd", 0)),
                "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                "price_change": float(pair.get("priceChange", {}).get("h24", 0)),
                "market_cap": float(pair.get("fdv", 0)),
                "dex": pair.get("dexId", "unknown"),
                "pair_count": 1  # Will be updated
            })
        
        print(f"  ✓ Found {len(tokens)} potential tokens")
        return tokens
    
    async def fetch_new_launches(self, limit: int = 30) -> List[Dict]:
        """Fetch recently launched tokens."""
        print("🆕 Fetching new token launches...")
        
        # Get recent pairs sorted by creation time
        data = await self._dexscreener_call("/latest/dex/search?q=pump")
        
        if not data or "pairs" not in data:
            return []
        
        seen_addresses = set()
        tokens = []
        
        for pair in data["pairs"][:limit]:
            token_address = pair.get("baseToken", {}).get("address")
            if not token_address or token_address in seen_addresses:
                continue
            
            # Only include pump.fun tokens or similar micro-caps
            symbol = pair.get("baseToken", {}).get("symbol", "").upper()
            if symbol in ["USDC", "USDT", "SOL", "BTC", "ETH"]:
                continue
            
            seen_addresses.add(token_address)
            
            tokens.append({
                "address": token_address,
                "symbol": symbol,
                "name": pair.get("baseToken", {}).get("name", "Unknown"),
                "price": float(pair.get("priceUsd", 0)),
                "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                "price_change": float(pair.get("priceChange", {}).get("h24", 0)),
                "market_cap": float(pair.get("fdv", 0)),
                "dex": pair.get("dexId", "unknown"),
                "pair_count": len(data["pairs"])
            })
        
        print(f"  ✓ Found {len(tokens)} new launches")
        return tokens
    
    async def analyze_token(self, token_address: str) -> Optional[Dict]:
        """Perform full risk analysis on a token."""
        # Check if already in database
        existing = self.db.get_analysis(token_address)
        if existing:
            return existing
        
        # Run fresh analysis
        try:
            async with SolanaContractAnalyzer() as analyzer:
                result = await analyzer.analyze(token_address)
                return self.db.get_analysis(token_address)
        except Exception as e:
            print(f"  ⚠️ Analysis failed for {token_address[:15]}...: {e}")
            return None
    
    def calculate_similarity_score(self, analysis: Dict, profile: Dict) -> float:
        """Calculate how similar a token is to a success profile."""
        score = 0.0
        max_score = 0.0
        
        # Risk score match (25% weight)
        risk = analysis.get("overall_risk_score", 50)
        risk_min, risk_max = profile["risk_score_range"]
        if risk_min <= risk <= risk_max:
            score += 25
        else:
            distance = min(abs(risk - risk_min), abs(risk - risk_max))
            score += max(0, 25 - distance * 2)
        max_score += 25
        
        # Liquidity match (20% weight)
        liquidity = analysis.get("liquidity_usd", 0)
        if liquidity >= profile["liquidity_min"]:
            score += 20
        else:
            score += (liquidity / profile["liquidity_min"]) * 20
        max_score += 20
        
        # Volume/Liquidity ratio (15% weight)
        volume = analysis.get("volume_24h", 0)
        vol_liq = volume / liquidity if liquidity > 0 else 0
        vol_min, vol_max = profile["vol_liq_range"]
        if vol_min <= vol_liq <= vol_max:
            score += 15
        else:
            score += 5  # Partial credit
        max_score += 15
        
        # Price change match (15% weight)
        price_change = analysis.get("price_change_24h", 0)
        pc_min, pc_max = profile["price_change_range"]
        if pc_min <= price_change <= pc_max:
            score += 15
        else:
            distance = min(abs(price_change - pc_min), abs(price_change - pc_max))
            score += max(0, 15 - distance * 0.5)
        max_score += 15
        
        # Authority checks (15% weight)
        red_flags = json.loads(analysis.get("red_flags", "[]"))
        green_flags = json.loads(analysis.get("green_flags", "[]"))
        
        mint_revoked = any("Mint authority revoked" in f for f in green_flags)
        freeze_revoked = any("Freeze authority revoked" in f for f in green_flags)
        
        if mint_revoked:
            score += 7.5
        if freeze_revoked:
            score += 7.5
        max_score += 15
        
        # Red flags penalty (10% weight)
        if len(red_flags) <= profile["red_flags_max"]:
            score += 10
        else:
            score += max(0, 10 - (len(red_flags) - profile["red_flags_max"]) * 3)
        max_score += 10
        
        # Calculate percentage
        return (score / max_score) * 100 if max_score > 0 else 0
    
    def determine_best_profile(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """Determine which profile matches best."""
        best_profile = max(scores, key=scores.get)
        best_score = scores[best_profile]
        
        if best_score >= 70:
            confidence = "HIGH"
        elif best_score >= 50:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return SUCCESS_PROFILES[best_profile]["name"], confidence
    
    def generate_recommendation(self, analysis: Dict, profile_name: str, confidence: str) -> str:
        """Generate trading recommendation based on profile match."""
        risk_score = analysis.get("overall_risk_score", 50)
        price_change = analysis.get("price_change_24h", 0)
        
        if confidence == "LOW":
            return "PASS - Doesn't match success patterns well"
        
        if "Stable Winner" in profile_name:
            return "BUY - Good fundamentals, stable price, hold 2-6 hours"
        elif "Pump Continuation" in profile_name:
            if price_change > 200:
                return "CAUTION - Already pumped heavily, use tight stops, 15-30 min max"
            else:
                return "BUY - Early pump stage, ride momentum with stops"
        elif "Dip Recovery" in profile_name:
            return "BUY - Oversold, expect bounce, hold 2-8 hours"
        
        return "NEUTRAL - Monitor for better entry"
    
    async def scan_and_rank(self, max_tokens: int = 20) -> List[TokenMatch]:
        """Scan tokens and rank by similarity to success profiles."""
        print("\n" + "=" * 80)
        print("🚀 PUMP.FUN SUCCESS PATTERN SCANNER")
        print("=" * 80)
        print("\n📊 Looking for tokens similar to our top performers:")
        print("   1. Stable Winner (28/100 risk) - Stable, good liquidity")
        print("   2. Pump Continuation (33/100 risk) - Strong momentum")
        print("   3. Dip Recovery (35/100 risk) - Oversold bounce potential")
        print()
        
        # Fetch tokens
        trending = await self.fetch_trending_solana_tokens(limit=30)
        new_launches = await self.fetch_new_launches(limit=20)
        
        # Combine and deduplicate
        all_tokens = {t["address"]: t for t in trending + new_launches}
        token_list = list(all_tokens.values())[:max_tokens]
        
        print(f"\n🔬 Analyzing {len(token_list)} unique tokens...")
        
        matches = []
        
        for i, token in enumerate(token_list, 1):
            print(f"\n  [{i}/{len(token_list)}] Analyzing {token['symbol']}...")
            
            # Skip if already analyzed recently
            existing = self.db.get_analysis(token["address"])
            if existing:
                print(f"    ✓ Using cached analysis")
                analysis = existing
            else:
                # Run fresh analysis
                analysis = await self.analyze_token(token["address"])
                if not analysis:
                    continue
                print(f"    ✓ Analysis complete")
            
            # Calculate similarity scores
            stable_score = self.calculate_similarity_score(analysis, SUCCESS_PROFILES["stable_winner"])
            pump_score = self.calculate_similarity_score(analysis, SUCCESS_PROFILES["pump_continuation"])
            dip_score = self.calculate_similarity_score(analysis, SUCCESS_PROFILES["dip_recovery"])
            
            overall = max(stable_score, pump_score, dip_score)
            
            # Skip if no good match
            if overall < 40:
                print(f"    ✗ Low similarity ({overall:.0f}%) - skipping")
                continue
            
            # Determine best match
            scores = {
                "stable_winner": stable_score,
                "pump_continuation": pump_score,
                "dip_recovery": dip_score
            }
            best_profile, confidence = self.determine_best_profile(scores)
            
            red_flags = json.loads(analysis.get("red_flags", "[]"))
            green_flags = json.loads(analysis.get("green_flags", "[]"))
            
            match = TokenMatch(
                contract_address=token["address"],
                token_name=analysis.get("token_name", "Unknown"),
                token_symbol=analysis.get("token_symbol", "UNKNOWN"),
                risk_score=analysis.get("overall_risk_score", 50),
                risk_rating=analysis.get("risk_rating", "UNKNOWN"),
                current_price=analysis.get("current_price", 0),
                price_change_24h=analysis.get("price_change_24h", 0),
                liquidity_usd=analysis.get("liquidity_usd", 0),
                volume_24h=analysis.get("volume_24h", 0),
                market_cap=analysis.get("market_cap", 0),
                pairs_count=analysis.get("pairs_count", 0),
                dex_platform=analysis.get("dex_platform", "unknown"),
                red_flags=red_flags,
                green_flags=green_flags,
                stable_winner_score=stable_score,
                pump_continuation_score=pump_score,
                dip_recovery_score=dip_score,
                overall_similarity=overall,
                matched_profile=best_profile,
                confidence=confidence,
                recommendation=self.generate_recommendation(analysis, best_profile, confidence)
            )
            
            matches.append(match)
            print(f"    ✓ MATCH: {best_profile} ({overall:.0f}% similarity) - {confidence} confidence")
        
        # Sort by overall similarity
        matches.sort(key=lambda x: x.overall_similarity, reverse=True)
        
        return matches

def print_match_report(match: TokenMatch, rank: int):
    """Print detailed report for a matched token."""
    print(f"\n{'=' * 80}")
    print(f"🏆 RANK #{rank}: {match.token_symbol} - {match.matched_profile}")
    print(f"   {match.contract_address}")
    print(f"{'=' * 80}")
    
    # Similarity scores
    print(f"\n📊 Similarity Scores:")
    print(f"   Overall Match: {match.overall_similarity:.1f}%")
    print(f"   vs Stable Winner: {match.stable_winner_score:.1f}%")
    print(f"   vs Pump Continuation: {match.pump_continuation_score:.1f}%")
    print(f"   vs Dip Recovery: {match.dip_recovery_score:.1f}%")
    print(f"   Confidence: {match.confidence}")
    
    # Market data
    print(f"\n💰 Market Data:")
    print(f"   Price: ${match.current_price:.6f}")
    change_emoji = "🟢" if match.price_change_24h > 0 else "🔴"
    print(f"   24h Change: {change_emoji} {match.price_change_24h:+.2f}%")
    print(f"   Market Cap: ${match.market_cap:,.2f}")
    print(f"   Liquidity: ${match.liquidity_usd:,.2f}")
    print(f"   24h Volume: ${match.volume_24h:,.2f}")
    vol_liq = match.volume_24h / match.liquidity_usd if match.liquidity_usd > 0 else 0
    print(f"   Vol/Liq Ratio: {vol_liq:.2f}x")
    print(f"   DEX Platform: {match.dex_platform}")
    print(f"   Trading Pairs: {match.pairs_count}")
    
    # Risk
    risk_emoji = "🟢" if match.risk_score <= 30 else "🟡" if match.risk_score <= 40 else "🟠"
    print(f"\n{risk_emoji} Risk Score: {match.risk_score}/100 ({match.risk_rating})")
    
    # Flags
    if match.green_flags:
        print(f"\n✅ Green Flags ({len(match.green_flags)}):")
        for flag in match.green_flags[:4]:
            print(f"   • {flag}")
    
    if match.red_flags:
        print(f"\n⚠️ Red Flags ({len(match.red_flags)}):")
        for flag in match.red_flags:
            print(f"   • {flag}")
    
    # Recommendation
    print(f"\n💡 Recommendation:")
    print(f"   {match.recommendation}")

def main():
    """Main entry point."""
    import sys
    
    max_tokens = 20
    if len(sys.argv) > 1:
        try:
            max_tokens = int(sys.argv[1])
        except ValueError:
            pass
    
    async def run():
        async with PumpFunScanner() as scanner:
            matches = await scanner.scan_and_rank(max_tokens=max_tokens)
            
            if not matches:
                print("\n❌ No tokens matched success patterns well")
                return
            
            # Print detailed reports for top matches
            print("\n" + "=" * 80)
            print("📋 DETAILED ANALYSIS - TOP MATCHES")
            print("=" * 80)
            
            for i, match in enumerate(matches[:10], 1):
                print_match_report(match, i)
            
            # Summary table
            print("\n" + "=" * 100)
            print("📊 SUMMARY - ALL MATCHED TOKENS")
            print("=" * 100)
            print(f"{'Rank':<6}{'Symbol':<12}{'Match %':<10}{'Profile':<25}{'Risk':<8}{'Price':<12}{'24h %':<10}{'Conf':<8}")
            print("-" * 100)
            
            for i, match in enumerate(matches, 1):
                symbol = match.token_symbol[:11]
                match_pct = f"{match.overall_similarity:.0f}%"
                profile = match.matched_profile[:24]
                risk = f"{match.risk_score}/100"
                price = f"${match.current_price:.6f}"
                change = f"{match.price_change_24h:+.1f}%"
                conf = match.confidence
                
                print(f"{i:<6}{symbol:<12}{match_pct:<10}{profile:<25}{risk:<8}{price:<12}{change:<10}{conf:<8}")
            
            print("=" * 100)
            
            # Best picks by category
            print("\n" + "=" * 80)
            print("🎯 BEST PICKS BY CATEGORY")
            print("=" * 80)
            
            # Best stable winner
            stable_matches = [m for m in matches if m.stable_winner_score > 50]
            if stable_matches:
                best = max(stable_matches, key=lambda x: x.stable_winner_score)
                print(f"\n🛡️ Best Stable Winner:")
                print(f"   {best.token_symbol} ({best.contract_address[:20]}...)")
                print(f"   Similarity: {best.stable_winner_score:.1f}% | Risk: {best.risk_score}/100")
            
            # Best pump continuation
            pump_matches = [m for m in matches if m.pump_continuation_score > 50]
            if pump_matches:
                best = max(pump_matches, key=lambda x: x.pump_continuation_score)
                print(f"\n🚀 Best Pump Continuation:")
                print(f"   {best.token_symbol} ({best.contract_address[:20]}...)")
                print(f"   Similarity: {best.pump_continuation_score:.1f}% | 24h: {best.price_change_24h:+.1f}%")
            
            # Best dip recovery
            dip_matches = [m for m in matches if m.dip_recovery_score > 50]
            if dip_matches:
                best = max(dip_matches, key=lambda x: x.dip_recovery_score)
                print(f"\n📉 Best Dip Recovery:")
                print(f"   {best.token_symbol} ({best.contract_address[:20]}...)")
                print(f"   Similarity: {best.dip_recovery_score:.1f}% | 24h: {best.price_change_24h:+.1f}%")
            
            print("\n" + "=" * 80)
    
    asyncio.run(run())

if __name__ == "__main__":
    main()
