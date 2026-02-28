"""
1SOL Trader API - Execute Trade
Vercel Serverless Function
"""

from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import time

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            token_address = data.get('token_address')
            amount = data.get('amount', 0.5)
            side = data.get('side', 'buy')
            
            if not token_address:
                raise ValueError("Token address required")
            
            # Mock trade execution
            trade = {
                "tx_id": f"tx_{int(time.time())}_{hash(token_address) % 10000}",
                "token": token_address,
                "amount": amount,
                "side": side,
                "timestamp": datetime.now().isoformat(),
                "status": "confirmed",
                "solscan_url": f"https://solscan.io/tx/mock_tx_{int(time.time())}"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "success": True,
                "trade": trade,
                "message": f"{side.upper()} order executed successfully"
            }
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "success": False,
                "error": str(e)
            }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
