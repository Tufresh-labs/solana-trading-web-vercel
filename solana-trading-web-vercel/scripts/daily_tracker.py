#!/usr/bin/env python3
"""
📊 Daily Profit Tracker
Real-time dashboard for tracking progress toward 1 SOL/day target
"""

import json
import os
import sys
import curses
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class DailyStats:
    """Statistics for a single trading day."""
    date: str
    target_sol: float
    current_pnl: float = 0.0
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    
    @property
    def progress_pct(self) -> float:
        return (self.current_pnl / self.target_sol) * 100 if self.target_sol > 0 else 0
    
    @property
    def target_reached(self) -> bool:
        return self.current_pnl >= self.target_sol
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades_count) * 100 if self.trades_count > 0 else 0


class ProfitTracker:
    """Track and display daily profit progress."""
    
    def __init__(self, target_sol: float = 1.0):
        self.target_sol = target_sol
        self.data_dir = Path(__file__).parent.parent / "data" / "profit_system"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "trade_history.json"
        
        # Load or initialize today's stats
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.stats = self._load_today_stats()
    
    def _load_today_stats(self) -> DailyStats:
        """Load today's trading stats from history."""
        if not self.history_file.exists():
            return DailyStats(date=self.today, target_sol=self.target_sol)
        
        with open(self.history_file) as f:
            history = json.load(f)
        
        # Filter for today
        today_trades = [t for t in history if t.get("timestamp", "").startswith(self.today)]
        
        pnl = sum(t.get("pnl_sol", 0) for t in today_trades)
        wins = sum(1 for t in today_trades if t.get("pnl_sol", 0) > 0)
        losses = len(today_trades) - wins
        
        return DailyStats(
            date=self.today,
            target_sol=self.target_sol,
            current_pnl=pnl,
            trades_count=len(today_trades),
            wins=wins,
            losses=losses
        )
    
    def add_trade(self, pnl_sol: float):
        """Add a trade to today's stats."""
        self.stats.current_pnl += pnl_sol
        self.stats.trades_count += 1
        if pnl_sol > 0:
            self.stats.wins += 1
        else:
            self.stats.losses += 1
    
    def display_dashboard(self):
        """Display the dashboard in terminal."""
        os.system('clear' if os.name != 'nt' else 'cls')
        
        # Header
        print("=" * 80)
        print("📊 1 SOL/DAY PROFIT TRACKER".center(80))
        print("=" * 80)
        
        # Date and time
        now = datetime.now()
        print(f"\n📅 {now.strftime('%A, %B %d, %Y')}")
        print(f"🕐 {now.strftime('%H:%M:%S')}")
        
        # Progress bar
        print("\n" + "=" * 80)
        print("🎯 DAILY TARGET PROGRESS")
        print("=" * 80)
        
        progress = min(self.stats.progress_pct, 100)
        bar_width = 50
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        status_emoji = "🟢" if self.stats.target_reached else "🟡" if progress > 50 else "🔴"
        
        print(f"\n   Target: {self.target_sol:.2f} SOL")
        print(f"   Current: {self.stats.current_pnl:+.3f} SOL")
        print(f"   Progress: [{bar}] {progress:.1f}%")
        
        if self.stats.target_reached:
            print(f"\n   {status_emoji} 🎉 TARGET REACHED! Great work today!")
            excess = self.stats.current_pnl - self.target_sol
            print(f"      Excess profit: +{excess:.3f} SOL")
        else:
            remaining = self.target_sol - self.stats.current_pnl
            print(f"\n   {status_emoji} Need {remaining:.3f} more SOL to reach target")
        
        # Trading stats
        print("\n" + "=" * 80)
        print("📈 TODAY'S TRADING STATS")
        print("=" * 80)
        
        print(f"\n   Total Trades: {self.stats.trades_count}")
        print(f"   Wins: 🟢 {self.stats.wins}")
        print(f"   Losses: 🔴 {self.stats.losses}")
        print(f"   Win Rate: {self.stats.win_rate:.1f}%")
        
        if self.stats.trades_count > 0:
            avg_trade = self.stats.current_pnl / self.stats.trades_count
            print(f"   Avg P&L per trade: {avg_trade:+.3f} SOL")
        
        # Market session info
        print("\n" + "=" * 80)
        print("⏰ MARKET SESSION")
        print("=" * 80)
        
        hour = now.hour
        if 9 <= hour < 12:
            session = "MORNING SESSION (High Activity)"
            session_emoji = "🌅"
        elif 12 <= hour < 15:
            session = "MIDDAY SESSION (Moderate)"
            session_emoji = "☀️"
        elif 15 <= hour < 18:
            session = "AFTERNOON SESSION (High Activity)"
            session_emoji = "🌤️"
        elif 18 <= hour < 22:
            session = "EVENING SESSION (Lower Volume)"
            session_emoji = "🌆"
        else:
            session = "OFF-HOURS (Limited Activity)"
            session_emoji = "🌙"
        
        print(f"\n   {session_emoji} {session}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATIONS")
        print("=" * 80)
        
        if self.stats.target_reached:
            print("\n   ✅ Target achieved!")
            print("   📋 Recommended actions:")
            print("      • Stop trading for the day")
            print("      • Review today's trades")
            print("      • Prepare for tomorrow")
        elif self.stats.current_pnl < -0.5:
            print("\n   🛑 Daily loss limit approaching!")
            print("   📋 Recommended actions:")
            print("      • Consider stopping for the day")
            print("      • Review what went wrong")
            print("      • Come back fresh tomorrow")
        elif progress < 30 and self.stats.trades_count >= 3:
            print("\n   ⚠️  Slow start today")
            print("   📋 Recommended actions:")
            print("      • Review signal quality")
            print("      • Be more selective with entries")
            print("      • Consider smaller position sizes")
        else:
            trades_needed = max(1, int((self.target_sol - self.stats.current_pnl) / 0.3))
            print(f"\n   📊 On track - need ~{trades_needed} more winning trades")
            print("   📋 Keep following the system:")
            print("      • Stick to high-confidence setups")
            print("      • Use proper stop losses")
            print("      • Take profits at target")
        
        # Footer
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit | Updates every 10 seconds".center(80))
        print("=" * 80)
    
    def run_live(self, refresh_seconds: int = 10):
        """Run live updating dashboard."""
        try:
            while True:
                # Reload stats
                self.stats = self._load_today_stats()
                
                # Display
                self.display_dashboard()
                
                # Wait
                time.sleep(refresh_seconds)
                
        except KeyboardInterrupt:
            print("\n\n👋 Tracker stopped. See you in the trenches!")
    
    def print_quick_status(self):
        """Print a quick one-line status."""
        progress = self.stats.progress_pct
        emoji = "🟢" if self.stats.target_reached else "🟡"
        print(f"{emoji} Today: {self.stats.current_pnl:+.3f}/{self.target_sol} SOL "
              f"({progress:.0f}%) | Trades: {self.stats.trades_count} "
              f"| Wins: {self.stats.wins}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Profit Tracker")
    parser.add_argument("--target", "-t", type=float, default=1.0,
                       help="Daily target in SOL (default: 1)")
    parser.add_argument("--live", "-l", action="store_true",
                       help="Run live updating dashboard")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Show quick one-line status")
    
    args = parser.parse_args()
    
    tracker = ProfitTracker(target_sol=args.target)
    
    if args.quick:
        tracker.print_quick_status()
    elif args.live:
        tracker.run_live()
    else:
        tracker.display_dashboard()


if __name__ == "__main__":
    main()
