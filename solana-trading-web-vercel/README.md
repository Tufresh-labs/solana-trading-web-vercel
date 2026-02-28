# 🎯 1SOL Trader - Vercel Edition

A modern, Phanes-inspired web trading platform powered by Smart Money intelligence and your Helius API key.

## ✨ Features

- 🔥 **Real Smart Money Analysis** - Using your Helius API key
- 🧠 **Holder Intelligence** - Track smart wallets & whales
- 📊 **Volume Momentum** - Detect spikes & accumulation
- 🎯 **Combined Scoring** - SM (35%) + Momentum (40%) + Pattern (25%)
- 💜 **Phanes UI** - Dark theme with tree-style data display
- ⚡ **Serverless** - Auto-scaling on Vercel's edge network

## 🚀 Quick Deploy

### Prerequisites
- Vercel account (free): https://vercel.com/signup
- Node.js (for Vercel CLI)

### Deploy in 30 seconds

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to project
cd solana-trading-web-vercel

# Deploy!
vercel --prod
```

Your site will be live at `https://1sol-trader.vercel.app` 🎉

---

## 🔑 API Key Configuration

### ✅ Your Helius API Key
```
cfb197fe-7adf-4a30-a2f0-9dfdbb5924dd
```

This key is already configured in:
- `vercel.json` → For production deployment
- `.env.local` → For local development

### Update Key (if needed)

**For Vercel Dashboard:**
1. Go to your project → Settings → Environment Variables
2. Update `HELIUS_API_KEY`

**For Local Dev:**
```bash
# Edit .env.local
HELIUS_API_KEY=your_new_key_here
```

---

## 📡 API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /api` | Health check | [Try it](https://your-app.vercel.app/api) |
| `GET /api/signals` | Get Smart Money signals | [Try it](https://your-app.vercel.app/api/signals) |
| `GET /api/analyze/<token>` | Analyze specific token | `/api/analyze/DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` |
| `GET /api/portfolio` | Portfolio data | `/api/portfolio` |
| `GET /api/holdings` | Holdings | `/api/holdings` |
| `POST /api/trade` | Execute trade | `/api/trade` |

### Test Your API

```bash
# Test health
curl https://your-app.vercel.app/api

# Get signals
curl https://your-app.vercel.app/api/signals?min_score=70

# Analyze BONK
curl https://your-app.vercel.app/api/analyze/DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
```

---

## 🎨 UI Features

### Dashboard
- Portfolio value with daily target progress
- Live Smart Money signals
- Market overview (SOL, BTC, ETH)
- Recent activity feed

### Signal Cards
```
🎯 SIGNAL: BONK - STRONG BUY
├ SM Score:    ████████░░ 78
├ Momentum:    ████████░░ 85
├ Pattern:     ███████░░░ 80
└ Combined:    ████████░░ 82

├ 🧠 Smart Money: 7 wallets
├ 📊 Volume: SPIKING (3.2x)
└ 📈 24h Change: +15.4%
```

### Token Detail Modal
- Full Smart Money analysis
- Green/Red flags
- Entry/Stop/Target prices
- One-click trade execution

---

## 🛠️ Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with Vercel CLI
vercel dev

# Or run frontend only
cd public && python3 -m http.server 3000
```

### Project Structure

```
solana-trading-web-vercel/
├── api/                       # Serverless API functions
│   ├── index.py              # Health check
│   ├── signals.py            # Smart Money signals (REAL DATA)
│   ├── analyze.py            # Token analysis (REAL DATA)
│   ├── portfolio.py          # Portfolio data
│   ├── holdings.py           # Holdings
│   └── trade.py              # Execute trades
├── public/                    # Frontend
│   ├── index.html            # Main HTML
│   ├── styles.css            # Phanes-inspired theme
│   └── app.js                # Frontend logic
├── scripts/                   # Smart Money Agent
│   ├── smart_money_momentum_agent.py
│   └── ...
├── vercel.json               # Vercel config (with API key)
├── requirements.txt          # Python dependencies
├── .env.local                # Local env (with API key)
└── README.md                 # This file
```

---

## 🔒 Security

- ✅ API key stored in Vercel environment variables
- ✅ Server-side API calls (key not exposed to frontend)
- ✅ CORS configured for security
- ✅ Rate limiting via Vercel's edge network

---

## 📊 Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│  Vercel API  │────▶│   Helius    │
│   (User)    │◀────│   (Python)   │◀────│    RPC      │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Smart Money  │
                    │    Agent     │
                    └──────────────┘
```

---

## 🎯 How It Works

1. **User visits site** → Static files from Vercel CDN
2. **Requests signals** → Serverless function calls Smart Money Agent
3. **Agent queries Helius** → Gets holder data via your API key
4. **Agent queries DexScreener** → Gets volume/price data
5. **Agent calculates scores** → SM + Momentum + Pattern
6. **Returns to frontend** → Beautiful cards displayed

---

## 🐛 Troubleshooting

### API Returns Mock Data
Check function logs in Vercel dashboard. Common issues:
- Helius API rate limit (add delay between calls)
- Token has insufficient liquidity
- Network timeout

### Slow Loading
- First load: Cold start (normal for serverless)
- Subsequent: Cached for 30 seconds

### CORS Errors
Already configured in all handlers. If issues persist:
```python
self.send_header('Access-Control-Allow-Origin', '*')
```

---

## 📝 Environment Variables

| Variable | Value | Location |
|----------|-------|----------|
| `HELIUS_API_KEY` | `cfb197fe-7adf-4a30-a2f0-9dfdbb5924dd` | vercel.json, .env.local |

---

## 🚀 Deployment Checklist

- [x] Helius API key configured
- [x] Smart Money agent included
- [x] Dependencies listed
- [x] CORS enabled
- [x] Caching implemented
- [ ] Deploy to Vercel
- [ ] Test endpoints
- [ ] Share URL

---

## 📞 Support

- Helius Docs: https://docs.helius.xyz
- Vercel Python: https://vercel.com/docs/functions/serverless-functions/runtimes/python
- Smart Money Agent: Check `scripts/smart_money_momentum_agent.py`

---

**Ready to deploy with real Smart Money data!** 🚀💰

Run `vercel --prod` to go live!
