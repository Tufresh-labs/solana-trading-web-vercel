#!/usr/bin/env python3
"""
🤖 Auto Scanner
Automated token discovery and opportunity detection for the 1 SOL/day system

This script:
1. Scans for new tokens from various sources
2. Analyzes them for risk
3. Generates trade signals
4. Saves opportunities for manual review
"""

import json
import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Set
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import ContractDatabase
from scripts.analyze_contract import ContractAnalyzer
from scripts.profit_system import ProfitSystem, TradeSignal


class AutoScanner:
    """Automated token scanner and opportunity finder."""
    
    # Known sources for token discovery
    DEXSCREENER_TRENDING = "https://api.dexscreener.com/token-boosts/top/v1"
    DEXSCREENER_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    def __init__(self):
        self.db = ContractDatabase()
        self.analyzer = ContractAnalyzer()
        self.profit_system = ProfitSystem()
        
        self.data_dir = Path(__file__).parent.parent / "data" / "profit_system"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Tracking
        self.scanned_today: Set[str] = set()
        self.new_opportunities: List[Dict] = []
        
    async def fetch_dexscreener_trending(self) -> List[Dict]:
        """Fetch trending tokens from DexScreener."""
        print("📡 Fetching trending tokens from DexScreener...")
        
        tokens = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.DEXSCREENER_TRENDING, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            token_address = item.get("tokenAddress", "")
                            if token_address and len(token_address) == 44:
                                tokens.append({
                                    "address": token_address,
                                    "source": "dexscreener_trending",
                                    "description": item.get("description", ""),
                                    "totalAmount": item.get("totalAmount", 0)
                                })
                        print(f"  ✓ Found {len(tokens)} trending tokens")
                    else:
                        print(f"  ✗ API returned status {resp.status}")
        except Exception as e:
            print(f"  ✗ Error fetching trending: {e}")
        
        return tokens
    
    async def fetch_dexscreener_latest(self) -> List[Dict]:
        """Fetch latest token profiles from DexScreener."""
        print("📡 Fetching latest tokens from DexScreener...")
        
        tokens = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.DEXSCREENER_LATEST, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            token_address = item.get("tokenAddress", "")
                            if token_address and len(token_address) == 44:
                                tokens.append({
                                    "address": token_address,
                                    "source": "dexscreener_latest",
                                    "description": item.get("description", ""),
                                    "icon": item.get("icon", "")
                                })
                        print(f"  ✓ Found {len(tokens)} new tokens")
                    else:
                        print(f"  ✗ API returned status {resp.status}")
        except Exception as e:
            print(f"  ✗ Error fetching latest: {e}")
        
        return tokens
    
    def get_manual_watchlist(self) -> List[str]:
        """Get manually tracked tokens."""
        watchlist_file = self.data_dir / "watchlist.txt"
        if watchlist_file.exists():
            with open(watchlist_file) as f:
                return [line.strip() for line in f if line.strip()]
        return []
    
    async def scan_all_sources(self) -> List[str]:
        """Scan all token sources and return unique addresses."""
        print("\n🔍 Starting token discovery scan...")
        print("=" * 80)
        
        all_tokens = []
        
        # Fetch from sources
        trending = await self.fetch_dexscreener_trending()
        latest = await self.fetch_dexscreener_latest()
        manual = self.get_manual_watchlist()
        
        all_tokens.extend([t["address"] for t in trending])
        all_tokens.extend([t["address"] for t in latest])
        all_tokens.extend(manual)
        
        # Get existing database contracts
        existing = self.db.get_all_contracts(limit=1000)
        existing_addresses = {c["contract_address"] for c in existing}
        
        # Combine and deduplicate
        all_addresses = list(set(all_tokens) | existing_addresses)
        
        print(f"\n📊 Token Sources:")
        print(f"   Trending: {len(trending)}")
        print(f"   Latest: {len(latest)}")
        print(f"   Manual watchlist: {len(manual)}")
        print(f"   Existing DB: {len(existing_addresses)}")
        print(f"   Total unique: {len(all_addresses)}")
        
        return all_addresses
    
    def analyze_token(self, address: str) -> Optional[Dict]:
        """Analyze a single token."""
        try:
            # Check if already analyzed recently
            existing = self.db.get_analysis(address)
            if existing:
                # Check age of analysis
                analyzed_at = existing.get("analyzed_at", "")
                if analyzed_at:
                    try:
                        from datetime import datetime
                        analysis_time = datetime.fromisoformat(analyzed_at)
                        if datetime.now() - analysis_time < timedelta(hours=6):
                            return existing  # Use cached analysis
                    except:
                        pass
            
            # Run fresh analysis
            result = self.analyzer.analyze(address)
            if result:
                self.db.save_analysis(address, result)
                return result
                
        except Exception as e:
            print(f"   ✗ Error analyzing {address[:20]}...: {e}")
        
        return None
    
    def scan_and_analyze(self, max_tokens: int = 100) -> List[TradeSignal]:
        """Main scanning routine."""
        print("\n" + "=" * 80)
        print("🤖 AUTO SCANNER - Finding 1 SOL/DAY Opportunities")
        print("=" * 80)
        print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run async discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        addresses = loop.run_until_complete(self.scan_all_sources())
        loop.close()
        
        # Limit for analysis
        addresses = addresses[:max_tokens]
        
        print(f"\n🔬 Analyzing {len(addresses)} tokens...")
        print("-" * 80)
        
        analyzed = []
        for i, address in enumerate(addresses, 1):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(addresses)}...")
            
            result = self.analyze_token(address)
            if result:
                analyzed.append(result)
        
        print(f"\n✓ Analyzed {len(analyzed)} tokens successfully")
        
        # Generate signals
        print("\n🎯 Generating trade signals...")
        signals = []
        
        for analysis in analyzed:
            try:
                addr = analysis.get("contract_address", "")
                if addr:
                    signal = self.profit_system.generate_signal(addr, portfolio_sol=50.0)
                    if signal:
                        signals.append(signal)
            except Exception as e:
                continue
        
        print(f"✓ Generated {len(signals)} qualified signals")
        
        # Save results
        self._save_scan_results(signals)
        
        return signals
    
    def _save_scan_results(self, signals: List[TradeSignal]):
        """Save scan results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.data_dir / f"scan_{timestamp}.json"
        
        data = []
        for s in signals:
            data.append({
                "contract_address": s.contract_address,
                "token_symbol": s.token_symbol,
                "risk_score": s.risk_score,
                "confidence": s.confidence,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "position_size_sol": s.position_size_sol,
                "potential_profit_sol": s.potential_profit_sol,
                "risk_reward_ratio": s.risk_reward_ratio,
                "setup_type": s.setup_type
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
    
    def print_opportunities(self, signals: List[TradeSignal]):
        """Print formatted opportunities."""
        if not signals:
            print("\n❌ No opportunities found")
            return
        
        print("\n" + "=" * 80)
        print("🚀 TOP OPPORTUNITIES")
        print("=" * 80)
        
        for i, signal in enumerate(signals[:10], 1):
            tier = "💎" if signal.risk_score <= 25 else "🥇" if signal.risk_score <= 30 else "🥈"
            progress = (signal.potential_profit_sol / 1.0) * 100
            
            print(f"\n{i}. {tier} {signal.token_symbol}")
            print(f"   Address: {signal.contract_address}")
            print(f"   Risk: {signal.risk_score}/100 | Confidence: {signal.confidence}")
            print(f"   Entry: ${signal.entry_price:.6f}")
            print(f"   Target: ${signal.take_profit:.6f} (+{((signal.take_profit/signal.entry_price)-1)*100:.1f}%)")
            print(f"   Potential: +{signal.potential_profit_sol:.3f} SOL ({progress:.0f}% of daily target)")
            print(f"   R:R: 1:{signal.risk_reward_ratio:.1f}")
    
    def run_scheduled_scan(self):
        """Run a scheduled scan (for cron jobs)."""
        signals = self.scan_and_analyze(max_tokens=50)
        
        # Print summary
        self.print_opportunities(signals)
        
        # Generate summary report
        print("\n" + "=" * 80)
        print("📋 SCAN SUMMARY")
        print("=" * 80)
        print(f"\n   Total opportunities: {len(signals)}")
        
        if signals:
            total_potential = sum(s.potential_profit_sol for s in signals[:5])
            print(f"   Top 5 potential: {total_potential:.3f} SOL")
            print(f"   Target coverage: {(total_potential/1.0)*100:.0f}% of 1 SOL goal")
            
            # Best pick
            best = signals[0]
            print(f"\n   🏆 Best opportunity: {best.token_symbol}")
            print(f"      Risk: {best.risk_score}/100")
            print(f"      Profit potential: +{best.potential_profit_sol:.3f} SOL")
        
        return signals


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Scanner for 1 SOL/day system")
    parser.add_argument("--max-tokens", "-m", type=int, default=100,
                       help="Maximum tokens to analyze (default: 100)")
    parser.add_argument("--scheduled", "-s", action="store_true",
                       help="Run in scheduled mode (for cron)")
    
    args = parser.parse_args()
    
    scanner = AutoScanner()
    
    if args.scheduled:
        scanner.run_scheduled_scan()
    else:
        signals = scanner.scan_and_analyze(max_tokens=args.max_tokens)
        scanner.print_opportunities(signals)
        
        print("\n" + "=" * 80)
        print("✅ Scan complete!")
        print("=" * 80)
        print("\n💡 Next steps:")
        print("   1. Review opportunities above")
        print("   2. Run: python profit_system.py")
        print("   3. Execute via trading bot")


if __name__ == "__main__":
    main()
