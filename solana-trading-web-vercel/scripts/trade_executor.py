#!/usr/bin/env python3
"""
🎯 Trade Execution Helper
Bridges signals from the 1 SOL/day system to the trading bot

Generates ready-to-use commands and tracks execution
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ExecutionPlan:
    """Complete execution plan for a trade."""
    token_symbol: str
    contract_address: str
    
    # Entry
    entry_price: float
    entry_command: str
    
    # Risk management
    stop_loss: float
    stop_command: str
    
    # Targets
    take_profit: float
    tp_command: str
    
    # Sizing
    position_sol: float
    
    # Metadata
    setup_type: str
    risk_score: int
    expected_profit: float


class TradeExecutor:
    """Helper for executing trades from signals."""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "profit_system"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Trading bot path
        self.bot_dir = Path(__file__).parent.parent.parent / "solana-trading-bot"
        
        # Load pending signals
        self.pending_signals = self._load_pending_signals()
        self.executed_trades = self._load_executed_trades()
    
    def _load_pending_signals(self) -> List[Dict]:
        """Load today's pending signals."""
        today = datetime.now().strftime('%Y-%m-%d')
        filename = self.data_dir / f"signals_{today}.json"
        
        if filename.exists():
            with open(filename) as f:
                return json.load(f)
        return []
    
    def _load_executed_trades(self) -> List[Dict]:
        """Load executed trades history."""
        filename = self.data_dir / "executed_trades.json"
        if filename.exists():
            with open(filename) as f:
                return json.load(f)
        return []
    
    def _save_executed_trades(self):
        """Save executed trades."""
        filename = self.data_dir / "executed_trades.json"
        with open(filename, 'w') as f:
            json.dump(self.executed_trades, f, indent=2)
    
    def generate_execution_plan(self, signal: Dict) -> ExecutionPlan:
        """Generate complete execution plan from signal."""
        symbol = signal.get("token_symbol", "UNKNOWN")
        address = signal.get("contract_address", "")
        
        # Use symbol for bot commands (if known), otherwise use contract
        token_ref = symbol if symbol != "UNKNOWN" else address[:8]
        
        entry = signal.get("entry_price", 0)
        stop = signal.get("stop_loss", 0)
        target = signal.get("take_profit", 0)
        size = signal.get("position_size_sol", 0.5)
        
        # Generate commands
        entry_cmd = f"/buy {token_ref} {size:.3f}"
        stop_cmd = f"/stoploss {token_ref} {stop:.8f} 100% 24"
        tp_cmd = f"/takeprofit {token_ref} {target:.8f} 100% 24"
        
        return ExecutionPlan(
            token_symbol=symbol,
            contract_address=address,
            entry_price=entry,
            entry_command=entry_cmd,
            stop_loss=stop,
            stop_command=stop_cmd,
            take_profit=target,
            tp_command=tp_cmd,
            position_sol=size,
            setup_type=signal.get("setup_type", "standard"),
            risk_score=signal.get("risk_score", 50),
            expected_profit=signal.get("potential_profit_sol", 0)
        )
    
    def print_execution_card(self, plan: ExecutionPlan, rank: int):
        """Print a formatted execution card."""
        tier = "💎" if plan.risk_score <= 25 else "🥇" if plan.risk_score <= 30 else "🥈"
        
        print(f"\n{'=' * 80}")
        print(f"🎯 EXECUTION PLAN #{rank}: {tier} {plan.token_symbol}")
        print(f"{'=' * 80}")
        print(f"   Contract: {plan.contract_address}")
        print(f"   Setup Type: {plan.setup_type.replace('_', ' ').title()}")
        print(f"   Risk Score: {plan.risk_score}/100")
        
        print(f"\n📊 Trade Parameters:")
        print(f"   Entry Price: ${plan.entry_price:.8f}")
        print(f"   Position Size: {plan.position_sol:.3f} SOL")
        print(f"   Expected Profit: +{plan.expected_profit:.3f} SOL")
        
        print(f"\n📝 Step-by-Step Execution:")
        print(f"\n   Step 1: ENTER POSITION")
        print(f"   ➜ {plan.entry_command}")
        
        print(f"\n   Step 2: SET STOP LOSS (Immediately after entry)")
        print(f"   ➜ {plan.stop_command}")
        
        print(f"\n   Step 3: SET TAKE PROFIT")
        print(f"   ➜ {plan.tp_command}")
        
        print(f"\n⚡ Quick Entry (copy-paste sequence):")
        print(f"   {plan.entry_command}")
        print(f"   {plan.stop_command}")
        print(f"   {plan.tp_command}")
        
        # Trading bot instructions
        print(f"\n🤖 Via Telegram Bot:")
        print(f"   1. Start bot: cd solana-trading-bot && python main.py")
        print(f"   2. Send commands above to your bot")
        print(f"   3. Confirm trades when prompted")
    
    def show_pending_trades(self):
        """Show all pending trade signals."""
        if not self.pending_signals:
            print("\n📭 No pending signals for today")
            print("   Run: python auto_scanner.py")
            return
        
        print("\n" + "=" * 80)
        print(f"📋 PENDING TRADES - {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 80)
        print(f"\nFound {len(self.pending_signals)} pending signals\n")
        
        # Generate execution plans for top 5
        for i, signal in enumerate(self.pending_signals[:5], 1):
            plan = self.generate_execution_plan(signal)
            self.print_execution_card(plan, i)
    
    def execute_trade(self, signal_index: int = 0):
        """Mark a trade as executed."""
        if not self.pending_signals or signal_index >= len(self.pending_signals):
            print("❌ Invalid signal index")
            return
        
        signal = self.pending_signals[signal_index]
        
        # Record execution
        execution = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal,
            "status": "open"
        }
        
        self.executed_trades.append(execution)
        self._save_executed_trades()
        
        print(f"\n✅ Trade recorded: {signal.get('token_symbol', 'UNKNOWN')}")
        print(f"   Status: OPEN")
        print(f"   Entry: ${signal.get('entry_price', 0):.8f}")
        print(f"   Stop: ${signal.get('stop_loss', 0):.8f}")
        print(f"   Target: ${signal.get('take_profit', 0):.8f}")
    
    def close_trade(self, index: int = -1, exit_price: float = 0, pnl_sol: float = 0):
        """Close an open trade."""
        if not self.executed_trades:
            print("❌ No open trades")
            return
        
        if index == -1:
            index = len(self.executed_trades) - 1
        
        if index < 0 or index >= len(self.executed_trades):
            print("❌ Invalid trade index")
            return
        
        trade = self.executed_trades[index]
        trade["status"] = "closed"
        trade["exit_price"] = exit_price
        trade["pnl_sol"] = pnl_sol
        trade["closed_at"] = datetime.now().isoformat()
        
        self._save_executed_trades()
        
        symbol = trade["signal"].get("token_symbol", "UNKNOWN")
        emoji = "🟢" if pnl_sol > 0 else "🔴"
        
        print(f"\n{emoji} Trade closed: {symbol}")
        print(f"   P&L: {pnl_sol:+.3f} SOL")
        
        # Update daily tracker
        self._update_daily_tracker(pnl_sol)
    
    def _update_daily_tracker(self, pnl_sol: float):
        """Update daily tracker with trade result."""
        history_file = self.data_dir / "trade_history.json"
        
        history = []
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)
        
        history.append({
            "timestamp": datetime.now().isoformat(),
            "pnl_sol": pnl_sol
        })
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def show_open_positions(self):
        """Show currently open positions."""
        open_trades = [t for t in self.executed_trades if t.get("status") == "open"]
        
        if not open_trades:
            print("\n📭 No open positions")
            return
        
        print("\n" + "=" * 80)
        print("📊 OPEN POSITIONS")
        print("=" * 80)
        
        for i, trade in enumerate(open_trades, 1):
            signal = trade["signal"]
            print(f"\n{i}. {signal.get('token_symbol', 'UNKNOWN')}")
            print(f"   Entry: ${signal.get('entry_price', 0):.8f}")
            print(f"   Stop: ${signal.get('stop_loss', 0):.8f}")
            print(f"   Target: ${signal.get('take_profit', 0):.8f}")
            print(f"   Opened: {trade.get('timestamp', '')[:16]}")
            print(f"   To close: python trade_executor.py --close {i} --pnl 0.5")
    
    def export_to_bot_format(self):
        """Export signals to a format ready for the trading bot."""
        if not self.pending_signals:
            print("❌ No signals to export")
            return
        
        export_data = []
        for signal in self.pending_signals[:10]:
            plan = self.generate_execution_plan(signal)
            export_data.append({
                "token": plan.token_symbol,
                "contract": plan.contract_address,
                "commands": {
                    "buy": plan.entry_command,
                    "stop": plan.stop_command,
                    "tp": plan.tp_command
                },
                "levels": {
                    "entry": plan.entry_price,
                    "stop": plan.stop_loss,
                    "target": plan.take_profit
                },
                "sizing": {
                    "position_sol": plan.position_sol,
                    "expected_profit": plan.expected_profit
                },
                "metadata": {
                    "risk_score": plan.risk_score,
                    "setup_type": plan.setup_type
                }
            })
        
        # Save export
        today = datetime.now().strftime('%Y%m%d')
        export_file = self.data_dir / f"bot_export_{today}.json"
        
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n✅ Exported {len(export_data)} signals to: {export_file}")
        print("\n📝 Quick reference (copy these):")
        print("-" * 80)
        
        for item in export_data[:5]:
            print(f"\n{item['token']}:")
            print(f"  Buy: {item['commands']['buy']}")
            print(f"  SL:  {item['commands']['stop']}")
            print(f"  TP:  {item['commands']['tp']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Trade Execution Helper")
    parser.add_argument("--show", "-s", action="store_true",
                       help="Show pending trade signals")
    parser.add_argument("--execute", "-e", type=int, metavar="INDEX",
                       help="Mark signal as executed (by index)")
    parser.add_argument("--positions", "-p", action="store_true",
                       help="Show open positions")
    parser.add_argument("--close", "-c", type=int, metavar="INDEX",
                       help="Close a position (by index)")
    parser.add_argument("--pnl", type=float, default=0.0,
                       help="P&L in SOL for closed trade")
    parser.add_argument("--export", action="store_true",
                       help="Export to bot format")
    
    args = parser.parse_args()
    
    executor = TradeExecutor()
    
    if args.show:
        executor.show_pending_trades()
    elif args.execute is not None:
        executor.execute_trade(args.execute)
    elif args.positions:
        executor.show_open_positions()
    elif args.close is not None:
        executor.close_trade(args.close, pnl_sol=args.pnl)
    elif args.export:
        executor.export_to_bot_format()
    else:
        # Default: show pending trades
        executor.show_pending_trades()
        
        print("\n" + "=" * 80)
        print("💡 Available Commands:")
        print("=" * 80)
        print("\n  Show pending trades:")
        print("    python trade_executor.py --show")
        print("\n  Record trade execution:")
        print("    python trade_executor.py --execute 0")
        print("\n  Show open positions:")
        print("    python trade_executor.py --positions")
        print("\n  Close a position:")
        print("    python trade_executor.py --close 0 --pnl 0.5")
        print("\n  Export to bot format:")
        print("    python trade_executor.py --export")


if __name__ == "__main__":
    main()
