#!/usr/bin/env python3
"""
Database module for Solana Contract Risk Analyzer
Uses SQLite for storing contract analyses and risk data
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict

DATABASE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../data/contract_analysis.db"
)

class ContractDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self._ensure_directory()
        self.init_database()
    
    def _ensure_directory(self):
        """Ensure the data directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize the database with tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Main contract analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contract_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    token_name TEXT,
                    token_symbol TEXT,
                    supply INTEGER,
                    decimals INTEGER,
                    mint_authority TEXT,
                    freeze_authority TEXT,
                    is_initialized BOOLEAN,
                    
                    -- Market data
                    current_price REAL,
                    price_change_24h REAL,
                    market_cap REAL,
                    liquidity_usd REAL,
                    fdv REAL,
                    pairs_count INTEGER,
                    volume_24h REAL,
                    dex_platform TEXT,
                    
                    -- Risk scores
                    overall_risk_score INTEGER,
                    risk_rating TEXT,
                    mint_authority_risk INTEGER,
                    freeze_authority_risk INTEGER,
                    liquidity_risk INTEGER,
                    holder_concentration_risk INTEGER,
                    contract_age_risk INTEGER,
                    verification_risk INTEGER,
                    scam_pattern_risk INTEGER,
                    volume_risk INTEGER,
                    volatility_risk INTEGER,
                    price_manipulation_risk INTEGER,
                    
                    -- Analysis data
                    top_10_concentration REAL,
                    holder_count INTEGER,
                    contract_age_days REAL,
                    first_tx TEXT,
                    
                    -- Flags
                    red_flags TEXT,  -- JSON array
                    green_flags TEXT,  -- JSON array
                    volume_insights TEXT,  -- JSON array
                    
                    -- Recommendations
                    recommendation TEXT,
                    risk_reward_ratio TEXT,
                    
                    -- Raw data
                    raw_analysis TEXT,  -- Full JSON
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Volume data table (time series)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS volume_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    total_volume REAL,
                    avg_volume REAL,
                    volume_spikes INTEGER,
                    suspicious_pattern BOOLEAN,
                    volume_trend TEXT,
                    buy_sell_ratio REAL,
                    liquidity_depth REAL,
                    price_volatility REAL,
                    timestamp TEXT,
                    FOREIGN KEY (contract_address) REFERENCES contract_analysis(contract_address),
                    UNIQUE(contract_address, timeframe)
                )
            ''')
            
            # Historical risk scores (for tracking changes over time)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    risk_score INTEGER,
                    risk_rating TEXT,
                    price REAL,
                    liquidity REAL,
                    volume_24h REAL,
                    FOREIGN KEY (contract_address) REFERENCES contract_analysis(contract_address)
                )
            ''')
            
            # Known scam patterns / blacklist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT UNIQUE NOT NULL,
                    reason TEXT,
                    source TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_address ON contract_analysis(contract_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_score ON contract_analysis(overall_risk_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON contract_analysis(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rating ON contract_analysis(risk_rating)')
            
            conn.commit()
    
    def save_analysis(self, result) -> bool:
        """Save a contract analysis to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Extract data from result
                data = {
                    'contract_address': result.contract_address,
                    'timestamp': result.timestamp,
                    'token_name': result.token_metadata.name,
                    'token_symbol': result.token_metadata.symbol,
                    'supply': result.token_metadata.supply,
                    'decimals': result.token_metadata.decimals,
                    'mint_authority': result.token_metadata.mint_authority,
                    'freeze_authority': result.token_metadata.freeze_authority,
                    'is_initialized': result.token_metadata.is_initialized,
                    
                    'current_price': result.chart_metrics.current_price,
                    'price_change_24h': result.chart_metrics.price_change_24h,
                    'market_cap': result.chart_metrics.market_cap,
                    'liquidity_usd': result.chart_metrics.liquidity_usd,
                    'fdv': result.chart_metrics.fdv,
                    'pairs_count': result.chart_metrics.pairs_count,
                    'volume_24h': result.chart_metrics.volume_24h,
                    'dex_platform': result.chart_metrics.dex_platform,
                    
                    'overall_risk_score': result.overall_risk_score,
                    'risk_rating': result.risk_rating,
                    'mint_authority_risk': result.risk_factors.mint_authority_risk,
                    'freeze_authority_risk': result.risk_factors.freeze_authority_risk,
                    'liquidity_risk': result.risk_factors.liquidity_risk,
                    'holder_concentration_risk': result.risk_factors.holder_concentration_risk,
                    'contract_age_risk': result.risk_factors.contract_age_risk,
                    'verification_risk': result.risk_factors.verification_risk,
                    'scam_pattern_risk': result.risk_factors.scam_pattern_risk,
                    'volume_risk': result.risk_factors.volume_risk,
                    'volatility_risk': result.risk_factors.volatility_risk,
                    'price_manipulation_risk': result.risk_factors.price_manipulation_risk,
                    
                    'red_flags': json.dumps(result.red_flags),
                    'green_flags': json.dumps(result.green_flags),
                    'volume_insights': json.dumps(result.volume_insights),
                    'recommendation': result.recommendation,
                    'risk_reward_ratio': result.risk_reward_ratio,
                    'raw_analysis': json.dumps(asdict(result), default=str)
                }
                
                # Insert or replace
                cursor.execute('''
                    INSERT OR REPLACE INTO contract_analysis (
                        contract_address, timestamp, token_name, token_symbol, supply,
                        decimals, mint_authority, freeze_authority, is_initialized,
                        current_price, price_change_24h, market_cap, liquidity_usd, fdv,
                        pairs_count, volume_24h, dex_platform, overall_risk_score,
                        risk_rating, mint_authority_risk, freeze_authority_risk,
                        liquidity_risk, holder_concentration_risk, contract_age_risk,
                        verification_risk, scam_pattern_risk, volume_risk, volatility_risk,
                        price_manipulation_risk, red_flags, green_flags, volume_insights,
                        recommendation, risk_reward_ratio, raw_analysis
                    ) VALUES (
                        :contract_address, :timestamp, :token_name, :token_symbol, :supply,
                        :decimals, :mint_authority, :freeze_authority, :is_initialized,
                        :current_price, :price_change_24h, :market_cap, :liquidity_usd, :fdv,
                        :pairs_count, :volume_24h, :dex_platform, :overall_risk_score,
                        :risk_rating, :mint_authority_risk, :freeze_authority_risk,
                        :liquidity_risk, :holder_concentration_risk, :contract_age_risk,
                        :verification_risk, :scam_pattern_risk, :volume_risk, :volatility_risk,
                        :price_manipulation_risk, :red_flags, :green_flags, :volume_insights,
                        :recommendation, :risk_reward_ratio, :raw_analysis
                    )
                ''', data)
                
                # Save volume data for each timeframe
                for tf_name, tf_data in result.chart_metrics.timeframes.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO volume_data (
                            contract_address, timeframe, total_volume, avg_volume,
                            volume_spikes, suspicious_pattern, volume_trend, buy_sell_ratio,
                            liquidity_depth, price_volatility, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.contract_address,
                        tf_name,
                        tf_data.total_volume,
                        tf_data.avg_volume,
                        tf_data.volume_spikes,
                        tf_data.suspicious_volume_pattern,
                        tf_data.volume_trend,
                        tf_data.buy_sell_ratio,
                        tf_data.liquidity_depth,
                        tf_data.price_volatility,
                        result.timestamp
                    ))
                
                # Save to risk history
                cursor.execute('''
                    INSERT INTO risk_history (
                        contract_address, timestamp, risk_score, risk_rating,
                        price, liquidity, volume_24h
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.contract_address,
                    result.timestamp,
                    result.overall_risk_score,
                    result.risk_rating,
                    result.chart_metrics.current_price,
                    result.chart_metrics.liquidity_usd,
                    result.chart_metrics.volume_24h
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    
    def get_analysis(self, contract_address: str) -> Optional[Dict]:
        """Get analysis for a specific contract."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM contract_analysis WHERE contract_address = ?
            ''', (contract_address,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_volume_data(self, contract_address: str) -> List[Dict]:
        """Get volume data for a specific contract."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM volume_data 
                WHERE contract_address = ?
                ORDER BY timeframe
            ''', (contract_address,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_risk_history(self, contract_address: str) -> List[Dict]:
        """Get risk score history for a contract."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM risk_history 
                WHERE contract_address = ?
                ORDER BY timestamp DESC
            ''', (contract_address,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_contracts(self, limit: int = 100, order_by: str = "timestamp") -> List[Dict]:
        """Get all analyzed contracts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            valid_columns = ['timestamp', 'overall_risk_score', 'liquidity_usd', 'volume_24h']
            if order_by not in valid_columns:
                order_by = 'timestamp'
            
            cursor.execute(f'''
                SELECT 
                    contract_address,
                    token_name,
                    token_symbol,
                    timestamp,
                    overall_risk_score,
                    risk_rating,
                    current_price,
                    liquidity_usd,
                    volume_24h,
                    price_change_24h
                FROM contract_analysis
                ORDER BY {order_by} DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_by_risk_rating(self, rating: str) -> List[Dict]:
        """Get contracts by risk rating (LOW, MEDIUM, HIGH, EXTREME)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM contract_analysis 
                WHERE risk_rating = ?
                ORDER BY overall_risk_score ASC
            ''', (rating,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_lowest_risk(self, min_liquidity: float = 10000, limit: int = 10) -> List[Dict]:
        """Get lowest risk contracts with minimum liquidity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM contract_analysis 
                WHERE liquidity_usd >= ? AND overall_risk_score <= 40
                ORDER BY overall_risk_score ASC, liquidity_usd DESC
                LIMIT ?
            ''', (min_liquidity, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_to_blacklist(self, contract_address: str, reason: str, source: str = "manual"):
        """Add a contract to the blacklist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO blacklist (contract_address, reason, source)
                VALUES (?, ?, ?)
            ''', (contract_address, reason, source))
            conn.commit()
    
    def is_blacklisted(self, contract_address: str) -> bool:
        """Check if a contract is blacklisted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM blacklist WHERE contract_address = ?',
                (contract_address,)
            )
            return cursor.fetchone() is not None
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total contracts
            cursor.execute('SELECT COUNT(*) FROM contract_analysis')
            stats['total_contracts'] = cursor.fetchone()[0]
            
            # By risk rating
            cursor.execute('''
                SELECT risk_rating, COUNT(*) 
                FROM contract_analysis 
                GROUP BY risk_rating
            ''')
            stats['by_rating'] = dict(cursor.fetchall())
            
            # Average risk score
            cursor.execute('SELECT AVG(overall_risk_score) FROM contract_analysis')
            stats['avg_risk_score'] = cursor.fetchone()[0] or 0
            
            # Blacklist count
            cursor.execute('SELECT COUNT(*) FROM blacklist')
            stats['blacklisted_count'] = cursor.fetchone()[0]
            
            return stats
    
    def export_to_json(self, filepath: str):
        """Export all data to JSON."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM contract_analysis')
            analyses = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM volume_data')
            volumes = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM risk_history')
            history = [dict(row) for row in cursor.fetchall()]
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'analyses': analyses,
                'volume_data': volumes,
                'risk_history': history
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

def main():
    """CLI for database operations."""
    import sys
    
    db = ContractDatabase()
    
    if len(sys.argv) < 2:
        print("Database Operations:")
        print("  python database.py stats           - Show statistics")
        print("  python database.py list            - List all contracts")
        print("  python database.py low-risk        - Show lowest risk contracts")
        print("  python database.py get <address>   - Get specific contract")
        print("  python database.py export <file>   - Export to JSON")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        stats = db.get_statistics()
        print("\n📊 Database Statistics")
        print("=" * 40)
        print(f"Total Contracts: {stats['total_contracts']}")
        print(f"Blacklisted: {stats['blacklisted_count']}")
        print(f"Average Risk Score: {stats['avg_risk_score']:.1f}/100")
        print("\nBy Risk Rating:")
        for rating, count in stats['by_rating'].items():
            print(f"  {rating}: {count}")
    
    elif cmd == "list":
        contracts = db.get_all_contracts(limit=20)
        print("\n📋 Recent Analyses")
        print("=" * 100)
        print(f"{'Contract':<44}{'Symbol':<10}{'Risk':<8}{'Rating':<10}{'Liquidity':<15}{'Volume 24h':<15}")
        print("-" * 100)
        for c in contracts:
            short_addr = f"{c['contract_address'][:40]}..."
            print(f"{short_addr:<44}{c['token_symbol']:<10}{c['overall_risk_score']:<8}{c['risk_rating']:<10}${c['liquidity_usd']:>12,.0f}${c['volume_24h']:>12,.0f}")
    
    elif cmd == "low-risk":
        contracts = db.get_lowest_risk(min_liquidity=5000, limit=10)
        print("\n🟢 Lowest Risk Contracts")
        print("=" * 100)
        print(f"{'Contract':<44}{'Symbol':<10}{'Risk':<8}{'Liquidity':<15}{'Price':<12}")
        print("-" * 100)
        for c in contracts:
            short_addr = f"{c['contract_address'][:40]}..."
            print(f"{short_addr:<44}{c['token_symbol']:<10}{c['overall_risk_score']:<8}${c['liquidity_usd']:>12,.0f}${c['current_price']:>10.6f}")
    
    elif cmd == "get" and len(sys.argv) > 2:
        addr = sys.argv[2]
        analysis = db.get_analysis(addr)
        if analysis:
            print(f"\n📄 Contract: {addr}")
            print("=" * 60)
            print(f"Name: {analysis['token_name']} ({analysis['token_symbol']})")
            print(f"Risk Score: {analysis['overall_risk_score']}/100 ({analysis['risk_rating']})")
            print(f"Price: ${analysis['current_price']:.6f}")
            print(f"Liquidity: ${analysis['liquidity_usd']:,.2f}")
            print(f"Recommendation: {analysis['recommendation']}")
            print(f"\nRed Flags: {json.loads(analysis['red_flags'])}")
            print(f"Green Flags: {json.loads(analysis['green_flags'])}")
        else:
            print(f"Contract {addr} not found in database")
    
    elif cmd == "export" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        db.export_to_json(filepath)
        print(f"✅ Exported database to {filepath}")
    
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()
