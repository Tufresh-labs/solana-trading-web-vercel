#!/usr/bin/env python3
"""
🔍 Code Verification Agent
Validates code quality, integration correctness, and system health.

Responsibilities:
- Check code syntax and imports
- Verify integration points between components
- Validate configuration requirements
- Test agent functionality
- Generate verification reports
"""

import ast
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a verification check."""
    check_name: str
    status: str  # passed, failed, warning
    message: str
    details: List[str] = field(default_factory=list)
    severity: str = "info"  # info, warning, error, critical


@dataclass
class VerificationReport:
    """Complete verification report."""
    timestamp: str
    total_checks: int
    passed: int
    failed: int
    warnings: int
    results: List[VerificationResult]
    summary: str


class CodeVerificationAgent:
    """
    Automated code verification for the 1SOL trading system.
    
    Verifies:
    1. Syntax correctness
    2. Import resolution
    3. Integration points
    4. Configuration completeness
    5. Agent functionality
    """
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.results: List[VerificationResult] = []
        self.errors: List[str] = []
        
    def verify_all(self) -> VerificationReport:
        """Run all verification checks."""
        logger.info("🔍 Starting code verification...")
        
        # Check 1: Smart Money Agent
        self._verify_smart_money_agent()
        
        # Check 2: Telegram Bot Integration
        self._verify_telegram_integration()
        
        # Check 3: Profit System Integration
        self._verify_profit_system_integration()
        
        # Check 4: File Structure
        self._verify_file_structure()
        
        # Check 5: Dependencies
        self._verify_dependencies()
        
        # Check 6: Configuration
        self._verify_configuration()
        
        # Generate report
        return self._generate_report()
    
    def _verify_smart_money_agent(self):
        """Verify the Smart Money Momentum Agent."""
        logger.info("Checking Smart Money Agent...")
        
        agent_path = self.project_root / "solana-contract-analyzer" / "scripts" / "smart_money_momentum_agent.py"
        
        if not agent_path.exists():
            self.results.append(VerificationResult(
                check_name="Smart Money Agent File",
                status="failed",
                message="smart_money_momentum_agent.py not found",
                severity="critical"
            ))
            return
        
        # Check syntax
        try:
            with open(agent_path) as f:
                code = f.read()
                ast.parse(code)
            
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Syntax",
                status="passed",
                message="Python syntax is valid"
            ))
        except SyntaxError as e:
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Syntax",
                status="failed",
                message=f"Syntax error: {e}",
                severity="critical"
            ))
            return
        
        # Check for required classes
        required_classes = [
            "SmartMoneyMomentumAgent",
            "SmartMoneySignal",
            "HolderMetrics",
            "VolumeMomentum",
            "AgentConfig"
        ]
        
        missing_classes = []
        for cls in required_classes:
            if cls not in code:
                missing_classes.append(cls)
        
        if missing_classes:
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Classes",
                status="failed",
                message=f"Missing classes: {', '.join(missing_classes)}",
                severity="error"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Classes",
                status="passed",
                message=f"All {len(required_classes)} required classes present"
            ))
        
        # Check for required methods
        required_methods = [
            "analyze_token",
            "analyze_holders",
            "analyze_volume_momentum",
            "detect_chart_patterns",
            "find_opportunities"
        ]
        
        missing_methods = []
        for method in required_methods:
            if f"async def {method}" not in code and f"def {method}" not in code:
                missing_methods.append(method)
        
        if missing_methods:
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Methods",
                status="warning",
                message=f"Missing methods: {', '.join(missing_methods)}"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Smart Money Agent Methods",
                status="passed",
                message=f"All {len(required_methods)} key methods present"
            ))
    
    def _verify_telegram_integration(self):
        """Verify Telegram bot integration."""
        logger.info("Checking Telegram Bot Integration...")
        
        bot_path = self.project_root / "solana-trading-bot" / "src" / "enhanced_bot.py"
        integration_path = self.project_root / "solana-trading-bot" / "src" / "smart_money_integration.py"
        
        # Check integration file exists
        if not integration_path.exists():
            self.results.append(VerificationResult(
                check_name="Smart Money Integration File",
                status="failed",
                message="smart_money_integration.py not found",
                severity="critical"
            ))
            return
        
        # Check enhanced_bot.py imports
        if not bot_path.exists():
            self.results.append(VerificationResult(
                check_name="Enhanced Bot File",
                status="failed",
                message="enhanced_bot.py not found",
                severity="critical"
            ))
            return
        
        with open(bot_path) as f:
            bot_code = f.read()
        
        # Check for Smart Money imports
        if "SmartMoneyIntegration" in bot_code:
            self.results.append(VerificationResult(
                check_name="Bot Import Integration",
                status="passed",
                message="SmartMoneyIntegration imported in enhanced_bot.py"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Bot Import Integration",
                status="failed",
                message="SmartMoneyIntegration not imported in enhanced_bot.py",
                severity="error"
            ))
        
        # Check for smartmoney command
        if "smartmoney_command" in bot_code:
            self.results.append(VerificationResult(
                check_name="Bot Command Handler",
                status="passed",
                message="smartmoney_command handler found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Bot Command Handler",
                status="failed",
                message="smartmoney_command handler not found",
                severity="error"
            ))
        
        # Check for /sm shortcut
        if "sm_command" in bot_code:
            self.results.append(VerificationResult(
                check_name="Bot Shortcut Command",
                status="passed",
                message="/sm shortcut command found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Bot Shortcut Command",
                status="warning",
                message="/sm shortcut command not found"
            ))
        
        # Check for callback handlers
        if "sm_buy_" in bot_code:
            self.results.append(VerificationResult(
                check_name="Bot Callback Handlers",
                status="passed",
                message="Smart Money callback handlers found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Bot Callback Handlers",
                status="warning",
                message="Smart Money callback handlers may be missing"
            ))
    
    def _verify_profit_system_integration(self):
        """Verify Profit System integration."""
        logger.info("Checking Profit System Integration...")
        
        profit_path = self.project_root / "solana-contract-analyzer" / "scripts" / "profit_system.py"
        
        if not profit_path.exists():
            self.results.append(VerificationResult(
                check_name="Profit System File",
                status="failed",
                message="profit_system.py not found",
                severity="critical"
            ))
            return
        
        with open(profit_path) as f:
            code = f.read()
        
        # Check for Smart Money import
        if "smart_money_momentum_agent" in code:
            self.results.append(VerificationResult(
                check_name="Profit System Import",
                status="passed",
                message="Smart Money agent imported in profit_system.py"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Profit System Import",
                status="failed",
                message="Smart Money agent not imported",
                severity="error"
            ))
        
        # Check for enhancement method
        if "enhance_signal_with_smart_money" in code:
            self.results.append(VerificationResult(
                check_name="Signal Enhancement Method",
                status="passed",
                message="enhance_signal_with_smart_money method found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Signal Enhancement Method",
                status="failed",
                message="enhance_signal_with_smart_money method not found",
                severity="error"
            ))
        
        # Check for async opportunities method
        if "find_opportunities_async" in code:
            self.results.append(VerificationResult(
                check_name="Async Opportunities Method",
                status="passed",
                message="find_opportunities_async method found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="Async Opportunities Method",
                status="warning",
                message="find_opportunities_async method not found"
            ))
        
        # Check for Smart Money exclusive opportunities
        if "find_smart_money_opportunities" in code:
            self.results.append(VerificationResult(
                check_name="SM Exclusive Opportunities",
                status="passed",
                message="find_smart_money_opportunities method found"
            ))
        else:
            self.results.append(VerificationResult(
                check_name="SM Exclusive Opportunities",
                status="warning",
                message="find_smart_money_opportunities method not found"
            ))
    
    def _verify_file_structure(self):
        """Verify project file structure."""
        logger.info("Checking File Structure...")
        
        required_files = {
            "Smart Money Agent": "solana-contract-analyzer/scripts/smart_money_momentum_agent.py",
            "Telegram Integration": "solana-trading-bot/src/smart_money_integration.py",
            "Enhanced Bot": "solana-trading-bot/src/enhanced_bot.py",
            "Profit System": "solana-contract-analyzer/scripts/profit_system.py",
            "Scaling Docs": "SCALING_RECOMMENDATIONS.md",
        }
        
        for name, path in required_files.items():
            full_path = self.project_root / path
            if full_path.exists():
                size = full_path.stat().st_size
                self.results.append(VerificationResult(
                    check_name=f"File: {name}",
                    status="passed",
                    message=f"File exists ({size:,} bytes)"
                ))
            else:
                self.results.append(VerificationResult(
                    check_name=f"File: {name}",
                    status="failed",
                    message="File not found",
                    severity="error"
                ))
        
        # Check data directories
        data_dirs = [
            "solana-contract-analyzer/data/profit_system",
            "solana-contract-analyzer/data/smart_money",
            "solana-trading-bot/data"
        ]
        
        for dir_path in data_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                self.results.append(VerificationResult(
                    check_name=f"Directory: {dir_path}",
                    status="passed",
                    message="Directory exists"
                ))
            else:
                self.results.append(VerificationResult(
                    check_name=f"Directory: {dir_path}",
                    status="warning",
                    message="Directory will be created at runtime"
                ))
    
    def _verify_dependencies(self):
        """Verify required dependencies."""
        logger.info("Checking Dependencies...")
        
        required_packages = [
            "aiohttp",
            "telegram",
        ]
        
        for package in required_packages:
            try:
                if package == "telegram":
                    # Special case for python-telegram-bot
                    spec = importlib.util.find_spec("telegram")
                else:
                    spec = importlib.util.find_spec(package)
                
                if spec is not None:
                    self.results.append(VerificationResult(
                        check_name=f"Package: {package}",
                        status="passed",
                        message=f"Package is installed"
                    ))
                else:
                    self.results.append(VerificationResult(
                        check_name=f"Package: {package}",
                        status="warning",
                        message=f"Package may not be installed"
                    ))
            except Exception as e:
                self.results.append(VerificationResult(
                    check_name=f"Package: {package}",
                    status="warning",
                    message=f"Could not verify: {e}"
                ))
    
    def _verify_configuration(self):
        """Verify configuration requirements."""
        logger.info("Checking Configuration...")
        
        # Check for required environment variables
        required_env = [
            "HELIUS_API_KEY",
        ]
        
        optional_env = [
            "TELEGRAM_BOT_TOKEN",
            "SOLANA_RPC_URL",
        ]
        
        for env_var in required_env:
            if os.getenv(env_var):
                self.results.append(VerificationResult(
                    check_name=f"Env: {env_var}",
                    status="passed",
                    message="Environment variable is set"
                ))
            else:
                self.results.append(VerificationResult(
                    check_name=f"Env: {env_var}",
                    status="failed",
                    message="Required environment variable not set",
                    severity="warning"  # Not critical for verification
                ))
        
        for env_var in optional_env:
            if os.getenv(env_var):
                self.results.append(VerificationResult(
                    check_name=f"Env: {env_var}",
                    status="passed",
                    message="Environment variable is set"
                ))
            else:
                self.results.append(VerificationResult(
                    check_name=f"Env: {env_var}",
                    status="warning",
                    message="Optional environment variable not set"
                ))
    
    def _generate_report(self) -> VerificationReport:
        """Generate final verification report."""
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        warnings = sum(1 for r in self.results if r.status == "warning")
        
        # Generate summary
        if failed == 0:
            summary = "✅ All critical checks passed! System is ready for deployment."
        elif failed <= 2:
            summary = f"⚠️ {failed} issues found. System may work with limitations."
        else:
            summary = f"❌ {failed} critical issues found. Please fix before deployment."
        
        return VerificationReport(
            timestamp=datetime.now().isoformat(),
            total_checks=len(self.results),
            passed=passed,
            failed=failed,
            warnings=warnings,
            results=self.results,
            summary=summary
        )
    
    def print_report(self, report: VerificationReport):
        """Pretty print the verification report."""
        print("\n" + "="*70)
        print("🔍 CODE VERIFICATION REPORT")
        print("="*70)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Checks: {report.total_checks}")
        print(f"✅ Passed: {report.passed}")
        print(f"❌ Failed: {report.failed}")
        print(f"⚠️  Warnings: {report.warnings}")
        print("\n" + "-"*70)
        print("DETAILED RESULTS:")
        print("-"*70)
        
        for result in report.results:
            icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⚠️"
            print(f"\n{icon} {result.check_name}")
            print(f"   Status: {result.status.upper()}")
            print(f"   Message: {result.message}")
            if result.details:
                for detail in result.details:
                    print(f"   - {detail}")
        
        print("\n" + "="*70)
        print("SUMMARY:")
        print("="*70)
        print(report.summary)
        print("="*70)
    
    def save_report(self, report: VerificationReport, filename: Optional[str] = None):
        """Save report to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"verification_report_{timestamp}.json"
        
        filepath = self.project_root / "solana-contract-analyzer" / "data" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": report.timestamp,
            "summary": {
                "total_checks": report.total_checks,
                "passed": report.passed,
                "failed": report.failed,
                "warnings": report.warnings,
                "summary_text": report.summary
            },
            "results": [
                {
                    "check_name": r.check_name,
                    "status": r.status,
                    "message": r.message,
                    "severity": r.severity,
                    "details": r.details
                }
                for r in report.results
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Report saved to: {filepath}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Verification Agent")
    parser.add_argument("--save", "-s", action="store_true", help="Save report to file")
    parser.add_argument("--project-root", "-p", help="Project root directory")
    
    args = parser.parse_args()
    
    agent = CodeVerificationAgent(args.project_root)
    report = agent.verify_all()
    agent.print_report(report)
    
    if args.save:
        agent.save_report(report)
    
    # Exit with error code if critical failures
    critical_failures = sum(
        1 for r in report.results 
        if r.status == "failed" and r.severity == "critical"
    )
    
    if critical_failures > 0:
        print(f"\n❌ {critical_failures} critical failures found!")
        sys.exit(1)
    else:
        print("\n✅ Verification complete!")
        sys.exit(0)


if __name__ == "__main__":
    main()
