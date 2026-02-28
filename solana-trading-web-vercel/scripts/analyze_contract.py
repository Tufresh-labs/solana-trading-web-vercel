#!/usr/bin/env python3
"""
Solana Contract Risk Analyzer
Analyzes SPL token contracts for risk factors and generates risk scores.
Integrates with DexScreener for real-time market data and volume analysis.
"""

import asyncio
import json
import sys
import os
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import aiohttp

# Configuration
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
DEXSCREENER_API = "https://api.dexscreener.com"

@dataclass
class TokenMetadata:
    name: str
    symbol: str
    mint_authority: Optional[str]
    freeze_authority: Optional[str]
    supply: int
    decimals: int
    is_initialized: bool

@dataclass
class VolumeAnalysis:
    timeframe: str
    total_volume: float
    avg_volume: float
    volume_spikes: int
    suspicious_volume_pattern: bool
    volume_trend: str  # increasing, decreasing, stable
    buy_sell_ratio: float  # >1 means more buys
    liquidity_depth: float
    price_volatility: float

@dataclass
class ChartMetrics:
    current_price: float
    price_change_24h: float
    market_cap: float
    liquidity_usd: float
    fdv: float
    pairs_count: int
    volume_24h: float
    top_pair_address: Optional[str]
    dex_platform: Optional[str]
    timeframes: Dict[str, VolumeAnalysis] = field(default_factory=dict)

@dataclass
class RiskFactors:
    mint_authority_risk: int
    freeze_authority_risk: int
    liquidity_risk: int
    holder_concentration_risk: int
    contract_age_risk: int
    verification_risk: int
    scam_pattern_risk: int
    volume_risk: int
    volatility_risk: int
    price_manipulation_risk: int

@dataclass
class AnalysisResult:
    contract_address: str
    timestamp: str
    token_metadata: TokenMetadata
    chart_metrics: ChartMetrics
    risk_factors: RiskFactors
    overall_risk_score: int
    risk_rating: str
    red_flags: List[str]
    green_flags: List[str]
    recommendation: str
    risk_reward_ratio: str
    volume_insights: List[str]

class SolanaContractAnalyzer:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.known_scam_patterns = self._load_scam_patterns()
        
    def _load_scam_patterns(self) -> Dict:
        """Load known scam patterns from reference file."""
        patterns_path = os.path.join(
            os.path.dirname(__file__), 
            "../references/scam_patterns.json"
        )
        try:
            with open(patterns_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"patterns": [], "blacklisted_addresses": []}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rpc_call(self, method: str, params: List) -> Dict:
        """Make a Solana RPC call."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        try:
            async with self.session.post(SOLANA_RPC_URL, json=payload, timeout=30) as resp:
                result = await resp.json()
                return result.get("result", {})
        except Exception as e:
            print(f"  ⚠️ RPC call failed: {e}")
            return {}
    
    async def _helius_call(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a Helius API call."""
        if not HELIUS_API_KEY:
            return {}
        url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": endpoint,
            "params": [params] if params else []
        }
        try:
            async with self.session.post(url, json=payload, timeout=30) as resp:
                result = await resp.json()
                return result.get("result", {})
        except Exception as e:
            print(f"  ⚠️ Helius call failed: {e}")
            return {}
    
    async def _dexscreener_call(self, endpoint: str) -> Dict:
        """Make a DexScreener API call."""
        url = f"{DEXSCREENER_API}{endpoint}"
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"  ⚠️ DexScreener call failed: {e}")
            return {}
    
    async def get_token_metadata(self, mint_address: str) -> TokenMetadata:
        """Fetch token metadata from on-chain data."""
        print("  📋 Fetching token metadata...")
        account_info = await self._rpc_call(
            "getAccountInfo", 
            [mint_address, {"encoding": "jsonParsed"}]
        )
        
        parsed = account_info.get("value", {}).get("data", {}).get("parsed", {})
        info = parsed.get("info", {})
        
        return TokenMetadata(
            name="Unknown",
            symbol="UNKNOWN",
            mint_authority=info.get("mintAuthority"),
            freeze_authority=info.get("freezeAuthority"),
            supply=int(info.get("supply", 0)),
            decimals=info.get("decimals", 0),
            is_initialized=info.get("isInitialized", False)
        )
    
    async def get_dexscreener_data(self, mint_address: str) -> ChartMetrics:
        """Fetch market data from DexScreener."""
        print("  📊 Fetching DexScreener market data...")
        
        # Get token pairs data
        data = await self._dexscreener_call(f"/token-pairs/v1/solana/{mint_address}")
        
        if not data or not isinstance(data, list) or len(data) == 0:
            print("  ⚠️ No DexScreener data available")
            return ChartMetrics(
                current_price=0,
                price_change_24h=0,
                market_cap=0,
                liquidity_usd=0,
                fdv=0,
                pairs_count=0,
                volume_24h=0,
                top_pair_address=None,
                dex_platform=None,
                timeframes={}
            )
        
        # Get best pair (highest liquidity)
        pairs = sorted(data, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
        top_pair = pairs[0] if pairs else {}
        
        liquidity_usd = float(top_pair.get("liquidity", {}).get("usd", 0) or 0)
        volume_24h = float(top_pair.get("volume", {}).get("h24", 0) or 0)
        price = float(top_pair.get("priceUsd", 0) or 0)
        price_change = float(top_pair.get("priceChange", {}).get("h24", 0) or 0)
        fdv = float(top_pair.get("fdv", 0) or 0)
        market_cap = fdv  # Approximation
        
        metrics = ChartMetrics(
            current_price=price,
            price_change_24h=price_change,
            market_cap=market_cap,
            liquidity_usd=liquidity_usd,
            fdv=fdv,
            pairs_count=len(pairs),
            volume_24h=volume_24h,
            top_pair_address=top_pair.get("pairAddress"),
            dex_platform=top_pair.get("dexId"),
            timeframes={}
        )
        
        # Get detailed pair data for volume analysis
        if top_pair.get("pairAddress"):
            await self._analyze_volume_patterns(top_pair.get("pairAddress"), metrics)
        
        return metrics
    
    async def _analyze_volume_patterns(self, pair_address: str, metrics: ChartMetrics):
        """Analyze volume patterns across different timeframes."""
        print("  📈 Analyzing volume patterns...")
        
        # Get pair history from DexScreener
        data = await self._dexscreener_call(f"/latest/dex/pairs/solana/{pair_address}")
        
        if not data or "pairs" not in data:
            return
        
        pair_data = data["pairs"][0] if data["pairs"] else {}
        
        # Extract volume data for different timeframes
        volume_data = pair_data.get("volume", {})
        price_data = pair_data.get("priceChange", {})
        
        # Create timeframe analyses
        timeframes = {
            "5m": VolumeAnalysis(
                timeframe="5m",
                total_volume=float(volume_data.get("m5", 0) or 0),
                avg_volume=0,  # Would need historical bars
                volume_spikes=0,
                suspicious_volume_pattern=False,
                volume_trend="unknown",
                buy_sell_ratio=1.0,
                liquidity_depth=metrics.liquidity_usd,
                price_volatility=abs(float(price_data.get("m5", 0) or 0))
            ),
            "15m": VolumeAnalysis(
                timeframe="15m",
                total_volume=float(volume_data.get("m15", 0) or 0),
                avg_volume=0,
                volume_spikes=0,
                suspicious_volume_pattern=False,
                volume_trend="unknown",
                buy_sell_ratio=1.0,
                liquidity_depth=metrics.liquidity_usd,
                price_volatility=abs(float(price_data.get("m15", 0) or 0))
            ),
            "30m": VolumeAnalysis(
                timeframe="30m",
                total_volume=float(volume_data.get("m30", 0) or 0),
                avg_volume=0,
                volume_spikes=0,
                suspicious_volume_pattern=False,
                volume_trend="unknown",
                buy_sell_ratio=1.0,
                liquidity_depth=metrics.liquidity_usd,
                price_volatility=abs(float(price_data.get("m30", 0) or 0))
            ),
            "1h": VolumeAnalysis(
                timeframe="1h",
                total_volume=float(volume_data.get("h1", 0) or 0),
                avg_volume=0,
                volume_spikes=0,
                suspicious_volume_pattern=False,
                volume_trend="unknown",
                buy_sell_ratio=1.0,
                liquidity_depth=metrics.liquidity_usd,
                price_volatility=abs(float(price_data.get("h1", 0) or 0))
            ),
            "24h": VolumeAnalysis(
                timeframe="24h",
                total_volume=float(volume_data.get("h24", 0) or 0),
                avg_volume=0,
                volume_spikes=0,
                suspicious_volume_pattern=False,
                volume_trend="unknown",
                buy_sell_ratio=1.0,
                liquidity_depth=metrics.liquidity_usd,
                price_volatility=abs(float(price_data.get("h24", 0) or 0))
            )
        }
        
        # Analyze patterns
        self._detect_volume_anomalies(timeframes)
        metrics.timeframes = timeframes
    
    def _detect_volume_anomalies(self, timeframes: Dict[str, VolumeAnalysis]):
        """Detect suspicious volume patterns."""
        tf_5m = timeframes.get("5m")
        tf_15m = timeframes.get("15m")
        tf_30m = timeframes.get("30m")
        tf_1h = timeframes.get("1h")
        tf_24h = timeframes.get("24h")
        
        # Check for volume spikes (5m volume is disproportionately high)
        if tf_5m and tf_1h and tf_1h.total_volume > 0:
            ratio_5m_to_1h = (tf_5m.total_volume * 12) / tf_1h.total_volume  # Annualized
            if ratio_5m_to_1h > 3:
                tf_5m.volume_spikes = 1
                tf_5m.suspicious_volume_pattern = True
        
        # Check for declining volume trend
        if tf_15m and tf_30m and tf_30m.total_volume > 0:
            if tf_15m.total_volume * 2 < tf_30m.total_volume * 0.5:
                tf_15m.volume_trend = "declining_sharply"
        
        # Check for wash trading indicators (volume but no price movement)
        for tf_name, tf in timeframes.items():
            if tf.total_volume > 10000 and tf.price_volatility < 0.5:
                tf.suspicious_volume_pattern = True
    
    async def get_holder_distribution(self, mint_address: str) -> Dict:
        """Get token holder distribution."""
        print("  👥 Analyzing holder distribution...")
        holders = await self._rpc_call(
            "getTokenLargestAccounts",
            [mint_address]
        )
        
        accounts = holders.get("value", [])
        total_supply = sum(int(a.get("amount", 0)) for a in accounts) if accounts else 0
        
        if not accounts or total_supply == 0:
            return {"top_10_concentration": 100, "holder_count": 0}
        
        top_10_amount = sum(int(a.get("amount", 0)) for a in accounts[:10])
        top_10_concentration = (top_10_amount / total_supply) * 100
        
        return {
            "top_10_concentration": top_10_concentration,
            "holder_count": len(accounts),
            "top_holders": accounts[:5]
        }
    
    async def get_contract_age(self, mint_address: str) -> Dict:
        """Get contract deployment information."""
        print("  📅 Checking contract age...")
        sigs = await self._rpc_call(
            "getSignaturesForAddress",
            [mint_address, {"limit": 1}]
        )
        
        if not sigs:
            return {"age_days": 0, "is_new": True}
        
        first_sig = sigs[0].get("signature")
        tx_info = await self._rpc_call(
            "getTransaction",
            [first_sig, {"encoding": "json"}]
        )
        
        block_time = tx_info.get("blockTime")
        if block_time:
            age_days = (datetime.now().timestamp() - block_time) / 86400
            return {
                "age_days": age_days,
                "is_new": age_days < 7,
                "first_tx": datetime.fromtimestamp(block_time).isoformat()
            }
        
        return {"age_days": 0, "is_new": True}
    
    def check_scam_patterns(self, metadata: TokenMetadata, 
                          holders: Dict, 
                          contract_address: str,
                          chart: ChartMetrics) -> List[str]:
        """Check for known scam patterns."""
        red_flags = []
        
        # Check blacklist
        if contract_address in self.known_scam_patterns.get("blacklisted_addresses", []):
            red_flags.append("CONTRACT_IN_BLACKLIST")
        
        # Check mint authority
        if metadata.mint_authority:
            red_flags.append("MINT_AUTHORITY_ACTIVE - Can inflate supply")
        
        # Check freeze authority
        if metadata.freeze_authority:
            red_flags.append("FREEZE_AUTHORITY_ACTIVE - Can freeze transfers")
        
        # Check holder concentration
        if holders.get("top_10_concentration", 0) > 80:
            red_flags.append("EXTREME_WHALE_CONCENTRATION - Top 10 holders >80%")
        elif holders.get("top_10_concentration", 0) > 50:
            red_flags.append("HIGH_WHALE_CONCENTRATION - Top 10 holders >50%")
        
        # Check liquidity
        if chart.liquidity_usd < 10000:
            red_flags.append("VERY_LOW_LIQUIDITY - < $10k, high slippage risk")
        elif chart.liquidity_usd < 50000:
            red_flags.append("LOW_LIQUIDITY - < $50k")
        
        # Check volume patterns
        for tf_name, tf in chart.timeframes.items():
            if tf.suspicious_volume_pattern and tf.volume_spikes > 0:
                red_flags.append(f"VOLUME_SPIKE_{tf_name} - Unusual volume activity")
        
        # Check for suspicious name
        if metadata.name.lower() in ["test", "fake", "scam"]:
            red_flags.append("SUSPICIOUS_TOKEN_NAME")
        
        return red_flags
    
    def calculate_risk_scores(self, metadata: TokenMetadata,
                            holders: Dict,
                            age: Dict,
                            red_flags: List[str],
                            chart: ChartMetrics) -> RiskFactors:
        """Calculate individual risk factor scores."""
        
        # Mint authority risk
        mint_risk = 100 if metadata.mint_authority else 0
        
        # Freeze authority risk
        freeze_risk = 80 if metadata.freeze_authority else 0
        
        # Liquidity risk based on actual USD liquidity
        liquidity_risk = 100
        if chart.liquidity_usd > 1000000:  # $1M+
            liquidity_risk = 10
        elif chart.liquidity_usd > 500000:  # $500k+
            liquidity_risk = 20
        elif chart.liquidity_usd > 100000:  # $100k+
            liquidity_risk = 40
        elif chart.liquidity_usd > 50000:   # $50k+
            liquidity_risk = 60
        elif chart.liquidity_usd > 10000:   # $10k+
            liquidity_risk = 80
        else:
            liquidity_risk = 100
        
        # Holder concentration risk
        concentration = holders.get("top_10_concentration", 0)
        if concentration > 90:
            holder_risk = 100
        elif concentration > 70:
            holder_risk = 80
        elif concentration > 50:
            holder_risk = 60
        elif concentration > 30:
            holder_risk = 40
        else:
            holder_risk = 20
        
        # Age risk
        age_days = age.get("age_days", 0)
        if age_days < 1:
            age_risk = 90
        elif age_days < 7:
            age_risk = 70
        elif age_days < 30:
            age_risk = 50
        elif age_days < 90:
            age_risk = 30
        else:
            age_risk = 10
        
        # Verification risk
        verification_risk = 50 if not metadata.is_initialized else 0
        
        # Scam pattern risk
        scam_risk = min(len(red_flags) * 10, 100)
        
        # Volume risk (based on 24h volume vs liquidity ratio)
        volume_risk = 50
        if chart.liquidity_usd > 0:
            vol_liq_ratio = chart.volume_24h / chart.liquidity_usd
            if vol_liq_ratio > 10:  # Very high turnover (possible wash trading)
                volume_risk = 80
            elif vol_liq_ratio > 5:
                volume_risk = 60
            elif vol_liq_ratio < 0.1:  # Very low volume
                volume_risk = 70
            else:
                volume_risk = 30
        
        # Volatility risk
        volatility_risk = 50
        if abs(chart.price_change_24h) > 100:  # >100% move
            volatility_risk = 90
        elif abs(chart.price_change_24h) > 50:
            volatility_risk = 70
        elif abs(chart.price_change_24h) > 20:
            volatility_risk = 50
        else:
            volatility_risk = 30
        
        # Price manipulation risk (based on volume patterns)
        manipulation_risk = 0
        for tf_name, tf in chart.timeframes.items():
            if tf.suspicious_volume_pattern:
                manipulation_risk += 15
        manipulation_risk = min(manipulation_risk, 100)
        
        return RiskFactors(
            mint_authority_risk=mint_risk,
            freeze_authority_risk=freeze_risk,
            liquidity_risk=liquidity_risk,
            holder_concentration_risk=holder_risk,
            contract_age_risk=age_risk,
            verification_risk=verification_risk,
            scam_pattern_risk=scam_risk,
            volume_risk=volume_risk,
            volatility_risk=volatility_risk,
            price_manipulation_risk=manipulation_risk
        )
    
    def calculate_overall_risk(self, factors: RiskFactors) -> tuple:
        """Calculate overall risk score and rating."""
        # Updated weights including new volume/volatility factors
        weights = {
            "mint_authority": 0.15,
            "freeze_authority": 0.08,
            "liquidity": 0.15,
            "holder_concentration": 0.12,
            "contract_age": 0.08,
            "verification": 0.07,
            "scam_pattern": 0.12,
            "volume": 0.10,
            "volatility": 0.08,
            "manipulation": 0.05
        }
        
        weighted_score = (
            factors.mint_authority_risk * weights["mint_authority"] +
            factors.freeze_authority_risk * weights["freeze_authority"] +
            factors.liquidity_risk * weights["liquidity"] +
            factors.holder_concentration_risk * weights["holder_concentration"] +
            factors.contract_age_risk * weights["contract_age"] +
            factors.verification_risk * weights["verification"] +
            factors.scam_pattern_risk * weights["scam_pattern"] +
            factors.volume_risk * weights["volume"] +
            factors.volatility_risk * weights["volatility"] +
            factors.price_manipulation_risk * weights["manipulation"]
        )
        
        score = int(weighted_score)
        
        if score <= 20:
            rating = "LOW"
        elif score <= 40:
            rating = "MEDIUM"
        elif score <= 60:
            rating = "HIGH"
        else:
            rating = "EXTREME"
        
        return score, rating
    
    def generate_volume_insights(self, chart: ChartMetrics) -> List[str]:
        """Generate insights based on volume analysis."""
        insights = []
        
        tf_24h = chart.timeframes.get("24h")
        tf_1h = chart.timeframes.get("1h")
        tf_5m = chart.timeframes.get("5m")
        
        if tf_24h and tf_24h.total_volume > 0:
            insights.append(f"24h Volume: ${tf_24h.total_volume:,.2f}")
            
            # Volume/Liquidity ratio
            if chart.liquidity_usd > 0:
                ratio = tf_24h.total_volume / chart.liquidity_usd
                insights.append(f"Volume/Liquidity Ratio: {ratio:.2f}x")
                
                if ratio > 5:
                    insights.append("⚠️ Very high volume relative to liquidity (possible wash trading)")
                elif ratio < 0.1:
                    insights.append("⚠️ Very low trading activity")
        
        if tf_1h and tf_1h.total_volume > 0:
            insights.append(f"1h Volume: ${tf_1h.total_volume:,.2f}")
        
        if tf_5m and tf_5m.suspicious_volume_pattern:
            insights.append("⚠️ Recent volume spike detected in 5m timeframe")
        
        # Price movement context
        if abs(chart.price_change_24h) > 50:
            insights.append(f"{'🚀' if chart.price_change_24h > 0 else '🔻'} Extreme 24h price movement: {chart.price_change_24h:+.2f}%")
        
        return insights
    
    def generate_recommendation(self, rating: str, red_flags: List[str], 
                               green_flags: List[str]) -> str:
        """Generate investment recommendation."""
        if rating == "EXTREME":
            return "AVOID - High probability of loss. Multiple critical risk factors detected."
        elif rating == "HIGH":
            return "CAUTION - Significant risks present. Only consider with thorough due diligence."
        elif rating == "MEDIUM":
            return "NEUTRAL - Moderate risks. Proceed with caution and position sizing."
        else:
            return "FAVORABLE - Lower risk profile. Still conduct due diligence before investing."
    
    def calculate_risk_reward(self, rating: str, factors: RiskFactors) -> str:
        """Estimate risk/reward ratio."""
        if rating == "EXTREME":
            return "Unfavorable (High Risk / Low Expected Return)"
        elif rating == "HIGH":
            return "Poor (Significant Risk / Uncertain Return)"
        elif rating == "MEDIUM":
            return "Moderate (Manageable Risk / Moderate Return Potential)"
        else:
            return "Favorable (Lower Risk / Better Risk-Adjusted Returns)"
    
    async def analyze(self, contract_address: str) -> AnalysisResult:
        """Perform full contract analysis."""
        print(f"\n🔍 Analyzing contract: {contract_address}")
        print("-" * 60)
        
        # Gather data concurrently
        metadata_task = self.get_token_metadata(contract_address)
        chart_task = self.get_dexscreener_data(contract_address)
        holders_task = self.get_holder_distribution(contract_address)
        age_task = self.get_contract_age(contract_address)
        
        metadata = await metadata_task
        chart = await chart_task
        holders = await holders_task
        age = await age_task
        
        # Check patterns
        red_flags = self.check_scam_patterns(metadata, holders, contract_address, chart)
        
        # Identify green flags
        green_flags = []
        if not metadata.mint_authority:
            green_flags.append("Mint authority revoked - Supply is fixed")
        if not metadata.freeze_authority:
            green_flags.append("Freeze authority revoked - Transfers cannot be frozen")
        if age.get("age_days", 0) > 90:
            green_flags.append("Contract is mature (>90 days old)")
        if holders.get("top_10_concentration", 100) < 30:
            green_flags.append("Good holder distribution")
        if chart.liquidity_usd > 100000:
            green_flags.append("Healthy liquidity (>$100k)")
        if chart.pairs_count > 2:
            green_flags.append("Listed on multiple DEXs")
        
        # Calculate risks
        risk_factors = self.calculate_risk_scores(
            metadata, holders, age, red_flags, chart
        )
        
        overall_score, rating = self.calculate_overall_risk(risk_factors)
        
        recommendation = self.generate_recommendation(rating, red_flags, green_flags)
        risk_reward = self.calculate_risk_reward(rating, risk_factors)
        volume_insights = self.generate_volume_insights(chart)
        
        result = AnalysisResult(
            contract_address=contract_address,
            timestamp=datetime.now().isoformat(),
            token_metadata=metadata,
            chart_metrics=chart,
            risk_factors=risk_factors,
            overall_risk_score=overall_score,
            risk_rating=rating,
            red_flags=red_flags,
            green_flags=green_flags,
            recommendation=recommendation,
            risk_reward_ratio=risk_reward,
            volume_insights=volume_insights
        )
        
        # Save to database
        await self._save_analysis(result)
        
        return result
    
    async def _save_analysis(self, result: AnalysisResult):
        """Save analysis to SQLite database for learning."""
        from database import ContractDatabase
        
        db = ContractDatabase()
        success = db.save_analysis(result)
        if success:
            print("  💾 Saved to database")
        else:
            print("  ⚠️ Failed to save to database")


def print_analysis(result: AnalysisResult):
    """Print formatted analysis results."""
    print("\n" + "=" * 70)
    print(f"🎯 RISK ANALYSIS REPORT")
    print("=" * 70)
    print(f"\nContract: {result.contract_address}")
    print(f"Analyzed: {result.timestamp}")
    
    print(f"\n📊 TOKEN METADATA")
    print(f"  Name: {result.token_metadata.name}")
    print(f"  Symbol: {result.token_metadata.symbol}")
    print(f"  Supply: {result.token_metadata.supply:,.0f}")
    print(f"  Decimals: {result.token_metadata.decimals}")
    
    cm = result.chart_metrics
    print(f"\n💰 MARKET DATA (DexScreener)")
    print(f"  Price: ${cm.current_price:.6f}" if cm.current_price > 0 else "  Price: N/A")
    print(f"  24h Change: {cm.price_change_24h:+.2f}%" if cm.price_change_24h != 0 else "  24h Change: N/A")
    print(f"  Market Cap: ${cm.market_cap:,.2f}" if cm.market_cap > 0 else "  Market Cap: N/A")
    print(f"  Liquidity: ${cm.liquidity_usd:,.2f}" if cm.liquidity_usd > 0 else "  Liquidity: N/A")
    print(f"  24h Volume: ${cm.volume_24h:,.2f}" if cm.volume_24h > 0 else "  24h Volume: N/A")
    print(f"  DEX Platform: {cm.dex_platform or 'N/A'}")
    print(f"  Trading Pairs: {cm.pairs_count}")
    
    if result.volume_insights:
        print(f"\n📈 VOLUME INSIGHTS")
        for insight in result.volume_insights:
            print(f"  {insight}")
    
    print(f"\n🚨 RISK SCORE: {result.overall_risk_score}/100 ({result.risk_rating})")
    print(f"📈 Risk/Reward: {result.risk_reward_ratio}")
    
    print(f"\n📋 RISK BREAKDOWN")
    rf = result.risk_factors
    print(f"  Mint Authority Risk:      {rf.mint_authority_risk}/100")
    print(f"  Freeze Authority Risk:    {rf.freeze_authority_risk}/100")
    print(f"  Liquidity Risk:           {rf.liquidity_risk}/100")
    print(f"  Holder Concentration:     {rf.holder_concentration_risk}/100")
    print(f"  Contract Age Risk:        {rf.contract_age_risk}/100")
    print(f"  Verification Risk:        {rf.verification_risk}/100")
    print(f"  Scam Pattern Risk:        {rf.scam_pattern_risk}/100")
    print(f"  Volume Risk:              {rf.volume_risk}/100")
    print(f"  Volatility Risk:          {rf.volatility_risk}/100")
    print(f"  Manipulation Risk:        {rf.price_manipulation_risk}/100")
    
    if result.red_flags:
        print(f"\n🔴 RED FLAGS ({len(result.red_flags)})")
        for flag in result.red_flags:
            print(f"  ⚠️  {flag}")
    
    if result.green_flags:
        print(f"\n🟢 GREEN FLAGS ({len(result.green_flags)})")
        for flag in result.green_flags:
            print(f"  ✅ {flag}")
    
    print(f"\n💡 RECOMMENDATION")
    print(f"  {result.recommendation}")
    print("=" * 70)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_contract.py <contract_address>")
        print("\nExample:")
        print("  python analyze_contract.py EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        sys.exit(1)
    
    contract_address = sys.argv[1]
    
    async with SolanaContractAnalyzer() as analyzer:
        result = await analyzer.analyze(contract_address)
        print_analysis(result)
        
        # Output JSON for programmatic use
        output_path = f"/tmp/analysis_{contract_address[:8]}.json"
        with open(output_path, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        print(f"\n💾 Full report saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
