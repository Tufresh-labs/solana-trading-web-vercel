#!/usr/bin/env python3
"""
🎯 1 SOL/DAY PROFIT SYSTEM
Master orchestrator for consistent daily Solana trading profits

This system integrates:
- Token discovery and scanning
- Risk analysis and scoring
- Trade signal generation
- Position sizing and risk management
- Daily profit tracking

Target: 1 SOL profit per day (~$150-250 depending on SOL price)
"""

import json
import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import ContractDatabase
from scripts.analyze_contract import ContractAnalyzer
from scripts.mass_scanner import MassScanner
from scripts.scalp_strategy import ScalpStrategyGenerator, ScalpSetup
from scripts.smart_money_momentum_agent import (
    SmartMoneyMomentumAgent, 
    SmartMoneySignal,
    AgentConfig as SMAgentConfig
)


@dataclass
class DailyTarget:
    """Daily profit target configuration."""
    sol_target: float = 1.0  # Target SOL profit per day
    max_trades_per_day: int = 5
    min_risk_reward: float = 1.5
    max_risk_score: int = 35
    min_liquidity: float = 150000  # $150K
    position_size_pct: float = 3.0  # 3% per trade
    daily_loss_limit: float = 0.5  # Stop after 0.5 SOL loss


@dataclass
class TradeSignal:
    """Generated trade signal with full execution plan."""
    # Token info
    contract_address: str
    token_symbol: str
    
    # Risk metrics
    risk_score: int
    risk_rating: str
    confidence: str
    
    # Market data
    current_price: float
    price_change_24h: float
    liquidity_usd: float
    volume_24h: float
    
    # Entry/Exit plan
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_sol: float
    
    # Expected outcomes
    potential_profit_sol: float
    potential_loss_sol: float
    risk_reward_ratio: float
    expected_win_rate: float
    
    # Execution metadata
    setup_type: str
    max_hold_time: str
    reasoning: List[str]
    warnings: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Status
    status: str = "pending"  # pending, executed, closed
    actual_profit_sol: Optional[float] = None


@dataclass
class DailySession:
    """Track a single trading session."""
    date: str
    target_sol: float
    
    # Tracking
    signals_generated: List[TradeSignal] = field(default_factory=list)
    trades_taken: List[TradeSignal] = field(default_factory=list)
    total_profit_sol: float = 0.0
    total_loss_sol: float = 0.0
    net_pnl_sol: float = 0.0
    
    # Status
    target_reached: bool = False
    daily_limit_hit: bool = False
    session_closed: bool = False
    
    def add_trade(self, signal: TradeSignal, actual_pnl: float):
        """Record a completed trade."""
        self.trades_taken.append(signal)
        if actual_pnl > 0:
            self.total_profit_sol += actual_pnl
        else:
            self.total_loss_sol += abs(actual_pnl)
        self.net_pnl_sol = self.total_profit_sol - self.total_loss_sol
        
        # Check targets
        if self.net_pnl_sol >= self.target_sol:
            self.target_reached = True
        if self.total_loss_sol >= 0.5:  # Daily loss limit
            self.daily_limit_hit = True


class ProfitSystem:
    """
    Main 1 SOL/day profit system.
    
    Orchestrates token discovery, analysis, signal generation,
    and profit tracking to achieve consistent daily profits.
    """
    
    def __init__(self, config: Optional[DailyTarget] = None, use_smart_money: bool = True):
        self.config = config or DailyTarget()
        self.db = ContractDatabase()
        self.analyzer = ContractAnalyzer()
        self.scalp_generator = ScalpStrategyGenerator()
        
        # Smart Money Agent
        self.use_smart_money = use_smart_money
        self.smart_money_agent: Optional[SmartMoneyMomentumAgent] = None
        if use_smart_money:
            self.smart_money_agent = SmartMoneyMomentumAgent(SMAgentConfig())
        
        # Tracking
        self.session: Optional[DailySession] = None
        self.signals: List[TradeSignal] = []
        
        # Data directory
        self.data_dir = Path(__file__).parent.parent / "data" / "profit_system"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load history
        self.history = self._load_history()
        
    def _load_history(self) -> List[Dict]:
        """Load trading history."""
        history_file = self.data_dir / "trade_history.json"
        if history_file.exists():
            with open(history_file) as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """Save trading history."""
        history_file = self.data_dir / "trade_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)
    
    def calculate_position_size(self, portfolio_sol: float, risk_score: int) -> float:
        """Calculate position size in SOL based on risk."""
        base_size = portfolio_sol * (self.config.position_size_pct / 100)
        
        # Adjust for risk
        if risk_score <= 25:
            multiplier = 1.0
        elif risk_score <= 30:
            multiplier = 0.9
        elif risk_score <= 35:
            multiplier = 0.75
        else:
            multiplier = 0.5
        
        return base_size * multiplier
    
    def generate_signal(self, contract_address: str, portfolio_sol: float = 50.0) -> Optional[TradeSignal]:
        """Generate a complete trade signal for a token."""
        # Get scalp setup
        setup = self.scalp_generator.generate_setup(contract_address)
        if not setup:
            return None
        
        # Filter by criteria
        if setup.risk_score > self.config.max_risk_score:
            return None
        if setup.liquidity_usd < self.config.min_liquidity:
            return None
        
        # Calculate position size in SOL
        position_sol = self.calculate_position_size(portfolio_sol, setup.risk_score)
        
        # Calculate potential profit/loss in SOL
        # Estimate SOL value of position
        sol_price = 180  # Approximate SOL price in USD
        position_usd = position_sol * sol_price
        
        # Calculate entry value in tokens
        token_amount = position_usd / setup.entry_price
        
        # Calculate profit/loss scenarios
        value_at_tp = token_amount * setup.take_profit_2  # Use TP2 for estimate
        value_at_sl = token_amount * setup.stop_loss
        
        potential_profit_usd = value_at_tp - position_usd
        potential_loss_usd = position_usd - value_at_sl
        
        potential_profit_sol = potential_profit_usd / sol_price
        potential_loss_sol = potential_loss_usd / sol_price
        
        # Calculate R:R
        rr = potential_profit_sol / potential_loss_sol if potential_loss_sol > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        # Estimate win rate based on setup quality
        if setup.risk_score <= 25 and setup.confidence == "HIGH":
            win_rate = 0.70
        elif setup.risk_score <= 30 and setup.confidence in ["HIGH", "MEDIUM"]:
            win_rate = 0.65
        elif setup.risk_score <= 35:
            win_rate = 0.60
        else:
            win_rate = 0.55
        
        return TradeSignal(
            contract_address=contract_address,
            token_symbol=setup.token_symbol,
            risk_score=setup.risk_score,
            risk_rating=setup.risk_rating,
            confidence=setup.confidence,
            current_price=setup.current_price,
            price_change_24h=setup.price_change_24h,
            liquidity_usd=setup.liquidity_usd,
            volume_24h=setup.volume_24h,
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit_2,  # Use TP2 as main target
            position_size_sol=position_sol,
            potential_profit_sol=potential_profit_sol,
            potential_loss_sol=potential_loss_sol,
            risk_reward_ratio=rr,
            expected_win_rate=win_rate,
            setup_type=setup.setup_type,
            max_hold_time=setup.max_hold_time,
            reasoning=setup.reasoning,
            warnings=setup.warnings
        )
    
    async def enhance_signal_with_smart_money(
        self, 
        signal: TradeSignal
    ) -> Optional[TradeSignal]:
        """
        Enhance a base signal with Smart Money Momentum analysis.
        Adjusts win rate and confidence based on Smart Money metrics.
        """
        if not self.smart_money_agent:
            return signal
        
        try:
            sm_signal = await self.smart_money_agent.analyze_token(signal.contract_address)
            if not sm_signal:
                return signal
            
            # Adjust confidence based on Smart Money score
            original_win_rate = signal.expected_win_rate
            sm_adjustment = 0
            
            # Smart money presence increases win rate
            if sm_signal.holder_metrics.smart_money_count >= 5:
                sm_adjustment += 0.10
            elif sm_signal.holder_metrics.smart_money_count >= 3:
                sm_adjustment += 0.05
            
            # Smart money buying increases win rate
            if sm_signal.holder_metrics.smart_money_buying:
                sm_adjustment += 0.08
            
            # High momentum score increases win rate
            if sm_signal.momentum_score >= 75:
                sm_adjustment += 0.05
            
            # Conflicting signals reduce win rate
            if sm_signal.signal_type in ["sell", "strong_sell"]:
                sm_adjustment -= 0.15
            elif sm_signal.signal_type == "hold":
                sm_adjustment -= 0.05
            
            # Calculate new win rate (cap at 80%)
            new_win_rate = min(0.80, original_win_rate + sm_adjustment)
            
            # Update reasoning with Smart Money insights
            enhanced_reasoning = signal.reasoning.copy()
            enhanced_warnings = signal.warnings.copy()
            
            # Add Smart Money insights
            if sm_signal.holder_metrics.smart_money_count > 0:
                enhanced_reasoning.append(
                    f"🧠 {sm_signal.holder_metrics.smart_money_count} smart money wallets detected"
                )
            
            if sm_signal.holder_metrics.smart_money_buying:
                enhanced_reasoning.append(
                    f"🟢 Smart money accumulating ({sm_signal.holder_metrics.smart_money_holdings_percent:.1f}% held)"
                )
            
            if sm_signal.volume_momentum.volume_trend == "spiking":
                enhanced_reasoning.append(
                    f"🔥 Volume spike: {sm_signal.volume_momentum.volume_ratio:.1f}x average"
                )
            
            # Add warnings if red flags
            if sm_signal.red_flags:
                for flag in sm_signal.red_flags[:2]:
                    if flag not in enhanced_warnings:
                        enhanced_warnings.append(f"⚠️ {flag}")
            
            # Create enhanced signal
            enhanced_signal = TradeSignal(
                contract_address=signal.contract_address,
                token_symbol=signal.token_symbol,
                risk_score=signal.risk_score,
                risk_rating=signal.risk_rating,
                confidence=signal.confidence,
                current_price=signal.current_price,
                price_change_24h=signal.price_change_24h,
                liquidity_usd=signal.liquidity_usd,
                volume_24h=signal.volume_24h,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                position_size_sol=signal.position_size_sol,
                potential_profit_sol=signal.potential_profit_sol,
                potential_loss_sol=signal.potential_loss_sol,
                risk_reward_ratio=signal.risk_reward_ratio,
                expected_win_rate=new_win_rate,
                setup_type=f"{signal.setup_type}_SM",
                max_hold_time=signal.max_hold_time,
                reasoning=enhanced_reasoning,
                warnings=enhanced_warnings
            )
            
            return enhanced_signal
            
        except Exception as e:
            print(f"  ⚠️ Smart Money enhancement failed: {e}")
            return signal
    
    def find_opportunities(self, portfolio_sol: float = 50.0) -> List[TradeSignal]:
        """Find all current trading opportunities (sync version)."""
        import asyncio
        return asyncio.run(self.find_opportunities_async(portfolio_sol))
    
    async def find_opportunities_async(self, portfolio_sol: float = 50.0) -> List[TradeSignal]:
        """Find all current trading opportunities with Smart Money enhancement."""
        print("\n🔍 Scanning for 1 SOL/day opportunities...")
        if self.use_smart_money:
            print("  🧠 Smart Money Agent enabled")
        print("=" * 80)
        
        # Initialize Smart Money agent if needed
        if self.smart_money_agent and not self.smart_money_agent.session:
            await self.smart_money_agent.__aenter__()
        
        # Get all analyzed contracts
        contracts = self.db.get_all_contracts(limit=200)
        print(f"  Analyzing {len(contracts)} contracts...")
        
        signals = []
        enhanced_count = 0
        
        for contract in contracts:
            signal = self.generate_signal(contract["contract_address"], portfolio_sol)
            if signal:
                # Enhance with Smart Money if enabled
                if self.use_smart_money and self.smart_money_agent:
                    enhanced = await self.enhance_signal_with_smart_money(signal)
                    if enhanced and enhanced.expected_win_rate > signal.expected_win_rate:
                        enhanced_count += 1
                        signal = enhanced
                signals.append(signal)
        
        # Sort by quality (risk score, then confidence)
        def sort_key(s):
            conf_score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s.confidence, 0)
            return (s.risk_score, -conf_score, -s.risk_reward_ratio)
        
        signals.sort(key=sort_key)
        
        print(f"  ✓ Found {len(signals)} qualified signals")
        if self.use_smart_money:
            print(f"  🧠 {enhanced_count} signals enhanced with Smart Money analysis")
        
        # Cleanup Smart Money agent
        if self.smart_money_agent:
            await self.smart_money_agent.__aexit__(None, None, None)
        
        return signals
    
    def print_signal_card(self, signal: TradeSignal, rank: int):
        """Print a formatted signal card."""
        print(f"\n{'=' * 80}")
        
        # Tier badge
        if signal.risk_score <= 25:
            tier = "💎 S-TIER"
        elif signal.risk_score <= 30:
            tier = "🥇 A-TIER"
        else:
            tier = "🥈 B-TIER"
        
        print(f"🎯 SIGNAL #{rank}: {tier} | {signal.token_symbol}")
        print(f"   {signal.contract_address}")
        print(f"{'=' * 80}")
        
        # Risk section
        risk_emoji = "🟢" if signal.risk_score <= 25 else "🟡" if signal.risk_score <= 30 else "🟠"
        print(f"\n{risk_emoji} Risk Profile:")
        print(f"   Score: {signal.risk_score}/100 ({signal.risk_rating})")
        print(f"   Confidence: {signal.confidence}")
        print(f"   Est. Win Rate: {signal.expected_win_rate*100:.0f}%")
        
        # Market data
        change_emoji = "🟢" if signal.price_change_24h > 0 else "🔴"
        print(f"\n📊 Market Data:")
        print(f"   Price: ${signal.current_price:.6f} ({change_emoji} {signal.price_change_24h:+.1f}%)")
        print(f"   Liquidity: ${signal.liquidity_usd:,.0f}")
        print(f"   24h Volume: ${signal.volume_24h:,.0f}")
        
        # Trade plan
        print(f"\n💰 Trade Plan ({signal.setup_type.replace('_', ' ').title()}):")
        print(f"   🚪 Entry: ${signal.entry_price:.6f}")
        print(f"   🛑 Stop:  ${signal.stop_loss:.6f}")
        print(f"   ✅ Target: ${signal.take_profit:.6f}")
        print(f"   ⏱️  Max Hold: {signal.max_hold_time}")
        
        # Position sizing
        print(f"\n💼 Position Sizing:")
        print(f"   Size: {signal.position_size_sol:.3f} SOL")
        print(f"   Potential Profit: +{signal.potential_profit_sol:.3f} SOL")
        print(f"   Max Loss: -{signal.potential_loss_sol:.3f} SOL")
        print(f"   Risk/Reward: 1:{signal.risk_reward_ratio:.1f}")
        
        # Payout toward daily target
        progress = (signal.potential_profit_sol / self.config.sol_target) * 100
        print(f"\n🎯 Contribution to Daily Target:")
        print(f"   This trade could contribute {progress:.1f}% of 1 SOL target")
        trades_needed = self.config.sol_target / signal.potential_profit_sol
        print(f"   ~{trades_needed:.1f} similar wins = 1 SOL profit")
        
        # Reasoning
        print(f"\n✅ Why This Setup:")
        for reason in signal.reasoning[:4]:
            print(f"   {reason}")
        
        # Warnings
        if signal.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in signal.warnings[:3]:
                print(f"   {warning}")
        
        # Execution commands
        print(f"\n📝 Execution Commands:")
        print(f"   # Via Trading Bot:")
        print(f"   /buy {signal.token_symbol} {signal.position_size_sol:.2f}")
        print(f"   /stoploss {signal.token_symbol} {signal.stop_loss:.6f} 100%")
        print(f"   /takeprofit {signal.token_symbol} {signal.take_profit:.6f} 100%")
    
    def print_daily_battle_plan(self, signals: List[TradeSignal]):
        """Print the daily trading battle plan."""
        print("\n" + "=" * 80)
        print("📋 DAILY BATTLE PLAN - 1 SOL TARGET")
        print("=" * 80)
        
        if not signals:
            print("\n❌ No qualified signals today")
            print("   Run scanner to find new tokens")
            return
        
        # Show top signals
        top_signals = signals[:self.config.max_trades_per_day]
        
        print(f"\n🎯 Top {len(top_signals)} Opportunities:")
        print(f"{'Rank':<6}{'Token':<12}{'Risk':<8}{'R:R':<8}{'Profit':<12}{'Target %':<12}{'Confidence':<12}")
        print("-" * 80)
        
        total_potential = 0
        for i, sig in enumerate(top_signals, 1):
            total_potential += sig.potential_profit_sol
            target_pct = (sig.potential_profit_sol / self.config.sol_target) * 100
            print(f"{i:<6}{sig.token_symbol:<12}{sig.risk_score:<8}"
                  f"1:{sig.risk_reward_ratio:<5.1f}{sig.potential_profit_sol:<10.3f}SOL"
                  f"{target_pct:<10.1f}%{sig.confidence:<12}")
        
        print("-" * 80)
        print(f"{'TOTAL POTENTIAL:':<30}{total_potential:.3f} SOL ({(total_potential/self.config.sol_target)*100:.0f}% of target)")
        
        # Strategy recommendations
        print("\n📊 Strategy Recommendations:")
        
        if total_potential >= self.config.sol_target:
            print("   ✅ Sufficient opportunities to hit target today")
        else:
            print(f"   ⚠️  May need {(self.config.sol_target/total_potential):.1f}x winning trades to hit target")
        
        # Best approach
        if len(top_signals) >= 3:
            print("   📈 Recommended: Take first 3 signals for diversification")
        elif len(top_signals) >= 1:
            print("   📈 Recommended: Take all available signals")
        
        # Risk management
        print("\n🛡️  Risk Management:")
        total_risk = sum(s.potential_loss_sol for s in top_signals[:3])
        print(f"   Total risk if all 3 hit stop: {total_risk:.3f} SOL")
        print(f"   Daily loss limit: {self.config.daily_loss_limit} SOL")
        print(f"   Stop trading if losses reach: {self.config.daily_loss_limit} SOL")
    
    async def find_smart_money_opportunities(
        self, 
        min_score: float = 70,
        portfolio_sol: float = 50.0
    ) -> List[TradeSignal]:
        """
        Find opportunities based purely on Smart Money signals.
        These may not pass traditional filters but have strong holder/momentum patterns.
        """
        if not self.smart_money_agent:
            print("⚠️ Smart Money Agent not available")
            return []
        
        print("\n🧠 Finding Smart Money exclusive opportunities...")
        print("=" * 80)
        
        await self.smart_money_agent.__aenter__()
        
        # Get Smart Money signals
        sm_signals = await self.smart_money_agent.find_opportunities(min_score=min_score)
        
        # Convert to TradeSignals
        trade_signals = []
        for sm_signal in sm_signals:
            # Skip if we already have this token from regular scan
            if any(s.contract_address == sm_signal.token_address for s in self.signals):
                continue
            
            # Calculate basic position sizing
            position_sol = self.calculate_position_size(portfolio_sol, 30)  # Assume medium risk
            
            # Use suggested values from Smart Money analysis
            entry = sm_signal.suggested_entry or 0
            stop = sm_signal.suggested_stop or entry * 0.9
            target = sm_signal.suggested_target or entry * 1.2
            
            # Calculate R:R
            risk = abs(entry - stop) if entry > 0 else 0.01
            reward = abs(target - entry) if entry > 0 else 0.01
            rr = reward / risk if risk > 0 else 1.0
            
            # Win rate based on Smart Money score
            base_win_rate = 0.60
            if sm_signal.combined_score >= 80:
                base_win_rate = 0.70
            elif sm_signal.combined_score >= 70:
                base_win_rate = 0.65
            
            trade_signal = TradeSignal(
                contract_address=sm_signal.token_address,
                token_symbol=sm_signal.symbol,
                risk_score=30,  # Medium risk for Smart Money signals
                risk_rating="MODERATE",
                confidence="HIGH" if sm_signal.combined_score >= 75 else "MEDIUM",
                current_price=entry,
                price_change_24h=sm_signal.momentum_indicators.price_momentum_24h,
                liquidity_usd=50000,  # Assume minimum
                volume_24h=sm_signal.volume_momentum.current_volume_24h,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target,
                position_size_sol=position_sol,
                potential_profit_sol=position_sol * 0.15,  # Estimate 15%
                potential_loss_sol=position_sol * 0.05,    # Estimate 5%
                risk_reward_ratio=rr,
                expected_win_rate=base_win_rate,
                setup_type="SMART_MOMENTUM",
                max_hold_time="24h",
                reasoning=[
                    f"🧠 Smart Money Score: {sm_signal.smart_money_score:.0f}",
                    f"📈 Momentum Score: {sm_signal.momentum_score:.0f}",
                    f"🔍 Pattern Score: {sm_signal.pattern_score:.0f}",
                    f"🎯 Combined: {sm_signal.combined_score:.0f}",
                ] + sm_signal.key_insights[:2],
                warnings=sm_signal.red_flags[:3]
            )
            
            trade_signals.append(trade_signal)
        
        await self.smart_money_agent.__aexit__(None, None, None)
        
        print(f"  ✓ Found {len(trade_signals)} Smart Money exclusive opportunities")
        return trade_signals
    
    def run_daily_scan(self, portfolio_sol: float = 50.0, include_smart_money_exclusive: bool = True):
        """Run a complete daily scan and generate battle plan."""
        import asyncio
        
        print("\n" + "=" * 80)
        print("🚀 1 SOL/DAY PROFIT SYSTEM - DAILY SCAN")
        print("=" * 80)
        print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target: {self.config.sol_target} SOL profit")
        print(f"💼 Portfolio: {portfolio_sol} SOL")
        print(f"📊 Max Risk Score: {self.config.max_risk_score}")
        print(f"💧 Min Liquidity: ${self.config.min_liquidity:,.0f}")
        if self.use_smart_money:
            print(f"🧠 Smart Money Enhancement: ENABLED")
        
        # Find opportunities (async)
        signals = asyncio.run(self.find_opportunities_async(portfolio_sol))
        
        # Find Smart Money exclusive opportunities
        if include_smart_money_exclusive and self.use_smart_money:
            sm_signals = asyncio.run(self.find_smart_money_opportunities(
                min_score=70, 
                portfolio_sol=portfolio_sol
            ))
            # Add to main list, marking as Smart Money exclusive
            signals.extend(sm_signals)
            # Re-sort
            def sort_key(s):
                conf_score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s.confidence, 0)
                return (s.risk_score, -conf_score, -s.risk_reward_ratio)
            signals.sort(key=sort_key)
        
        # Print detailed cards for top 5
        print("\n" + "=" * 80)
        print("📋 DETAILED SIGNALS")
        print("=" * 80)
        
        for i, signal in enumerate(signals[:5], 1):
            self.print_signal_card(signal, i)
        
        # Print battle plan
        self.print_daily_battle_plan(signals)
        
        # Save signals
        self.signals = signals
        self._save_daily_signals(signals)
        
        return signals
    
    def _save_daily_signals(self, signals: List[TradeSignal]):
        """Save today's signals to file."""
        today = datetime.now().strftime('%Y-%m-%d')
        filename = self.data_dir / f"signals_{today}.json"
        
        data = [asdict(s) for s in signals]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n💾 Saved {len(signals)} signals to {filename}")
    
    def track_trade(self, contract_address: str, entry_price: float, 
                   exit_price: float, position_sol: float, side: str = "long"):
        """Track a completed trade."""
        # Calculate P&L
        pnl_pct = (exit_price - entry_price) / entry_price
        if side == "short":
            pnl_pct = -pnl_pct
        
        pnl_sol = position_sol * pnl_pct
        
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "contract": contract_address,
            "entry": entry_price,
            "exit": exit_price,
            "position_sol": position_sol,
            "pnl_pct": pnl_pct * 100,
            "pnl_sol": pnl_sol,
            "side": side
        }
        
        self.history.append(trade_record)
        self._save_history()
        
        # Print result
        emoji = "🟢" if pnl_sol > 0 else "🔴"
        print(f"\n{emoji} Trade Recorded:")
        print(f"   P&L: {pnl_sol:+.3f} SOL ({pnl_pct*100:+.2f}%)")
        print(f"   Progress toward 1 SOL target: {abs(pnl_sol)/self.config.sol_target*100:.1f}%")
        
        return pnl_sol
    
    def show_stats(self):
        """Show system performance statistics."""
        print("\n" + "=" * 80)
        print("📊 1 SOL/DAY SYSTEM STATISTICS")
        print("=" * 80)
        
        if not self.history:
            print("\n📭 No trades recorded yet")
            return
        
        total_trades = len(self.history)
        wins = sum(1 for t in self.history if t["pnl_sol"] > 0)
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t["pnl_sol"] for t in self.history)
        avg_win = sum(t["pnl_sol"] for t in self.history if t["pnl_sol"] > 0) / wins if wins > 0 else 0
        avg_loss = sum(t["pnl_sol"] for t in self.history if t["pnl_sol"] < 0) / losses if losses > 0 else 0
        
        print(f"\n📈 Overall Performance:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_pnl:+.3f} SOL")
        print(f"   Avg Win: +{avg_win:.3f} SOL")
        print(f"   Avg Loss: {avg_loss:.3f} SOL")
        
        # Daily breakdown
        from collections import defaultdict
        daily_pnl = defaultdict(float)
        for trade in self.history:
            date = trade["timestamp"][:10]
            daily_pnl[date] += trade["pnl_sol"]
        
        print(f"\n📅 Daily Results:")
        days_hit_target = sum(1 for pnl in daily_pnl.values() if pnl >= self.config.sol_target)
        print(f"   Days traded: {len(daily_pnl)}")
        print(f"   Days hit 1 SOL target: {days_hit_target} ({days_hit_target/len(daily_pnl)*100:.0f}%)")
        print(f"   Best day: {max(daily_pnl.values()):+.3f} SOL")
        print(f"   Worst day: {min(daily_pnl.values()):+.3f} SOL")
        
        # Recent trades
        print(f"\n📝 Last 5 Trades:")
        for trade in self.history[-5:]:
            emoji = "🟢" if trade["pnl_sol"] > 0 else "🔴"
            print(f"   {emoji} {trade['timestamp'][:10]}: {trade['pnl_sol']:+.3f} SOL")


def main():
    parser = argparse.ArgumentParser(description="1 SOL/Day Profit System")
    parser.add_argument("--portfolio", "-p", type=float, default=50.0,
                       help="Portfolio size in SOL (default: 50)")
    parser.add_argument("--target", "-t", type=float, default=1.0,
                       help="Daily profit target in SOL (default: 1)")
    parser.add_argument("--scan", "-s", action="store_true",
                       help="Run daily scan for opportunities")
    parser.add_argument("--stats", action="store_true",
                       help="Show performance statistics")
    
    args = parser.parse_args()
    
    # Create system
    config = DailyTarget(sol_target=args.target)
    system = ProfitSystem(config)
    
    if args.stats:
        system.show_stats()
    elif args.scan or True:  # Default to scan
        system.run_daily_scan(args.portfolio)
        print("\n" + "=" * 80)
        print("✅ Daily scan complete!")
        print("=" * 80)
        print("\n💡 Next Steps:")
        print("   1. Review the top signals above")
        print("   2. Use the trading bot to execute:")
        print("      cd solana-trading-bot && python main.py")
        print("   3. After trading, track results with:")
        print("      python profit_system.py --stats")


if __name__ == "__main__":
    main()
