"""
1SOL Trader API - Holdings
Vercel Serverless Function
"""

from http.server import BaseHTTPRequestHandler
import json
import random

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Mock holdings with slight price variations
        base_holdings = [
            {
                "symbol": "BONK",
                "name": "Bonk",
                "amount": 1250000,
                "entry_price": 0.00001050,
                "current_price": 0.00001234 * (1 + (random.random() - 0.5) * 0.05),
                "pnl_pct": 17.5,
                "pnl_sol": 0.23
            },
            {
                "symbol": "PEPE",
                "name": "Pepe",
                "amount": 850000,
                "entry_price": 0.00000920,
                "current_price": 0.00000890 * (1 + (random.random() - 0.5) * 0.03),
                "pnl_pct": -3.3,
                "pnl_sol": -0.05
            },
            {
                "symbol": "JUP",
                "name": "Jupiter",
                "amount": 500,
                "entry_price": 0.75,
                "current_price": 0.85 * (1 + (random.random() - 0.5) * 0.04),
                "pnl_pct": 13.3,
                "pnl_sol": 0.08
            }
        ]
        
        # Recalculate P&L based on current prices
        for holding in base_holdings:
            pnl_pct = ((holding['current_price'] - holding['entry_price']) / holding['entry_price']) * 100
            holding['pnl_pct'] = round(pnl_pct, 2)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "holdings": base_holdings,
            "total_value_sol": sum(h['amount'] * h['current_price'] / 150 for h in base_holdings)  # Rough SOL conversion
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
