# 🚀 Deploy 1SOL Trader to Vercel

Follow these steps to deploy your Smart Money trading platform to Vercel in minutes!

## 📋 Prerequisites

- [Vercel account](https://vercel.com/signup) (free)
- [GitHub account](https://github.com/signup) (optional, for auto-deploy)
- Git installed locally

## ⚡ Quick Deploy (2 minutes)

### Option 1: Vercel CLI (Recommended)

```bash
# Install Vercel CLI if not already installed
npm i -g vercel

# Navigate to the project
cd solana-trading-web-vercel

# Deploy!
vercel --prod
```

Follow the prompts:
- Login/signup to Vercel
- Link to existing project? **N**
- Project name: `1sol-trader` (or your choice)
- Directory: `./` (current)

Your site will be live at `https://1sol-trader.vercel.app` 🎉

---

### Option 2: Git Integration (Auto-deploy)

```bash
# Initialize git repo
cd solana-trading-web-vercel
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - 1SOL Trader"

# Create GitHub repo (manual or via gh CLI)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/1sol-trader.git
git push -u origin main

# Connect to Vercel:
# 1. Go to https://vercel.com/new
# 2. Import your GitHub repo
# 3. Deploy!
```

---

## 🔧 Configuration

### Environment Variables (Optional)

For production with real data, add these in Vercel dashboard:

1. Go to your project on Vercel
2. Click **Settings** → **Environment Variables**
3. Add:

| Name | Value | Environment |
|------|-------|-------------|
| `HELIUS_API_KEY` | your_key_here | Production |
| `HELIUS_API_KEY` | your_key_here | Preview |

### Custom Domain

1. Go to **Settings** → **Domains**
2. Add your domain
3. Follow DNS configuration

---

## 📁 Project Structure

```
solana-trading-web-vercel/
├── api/                    # Serverless API functions
│   ├── index.py           # Health check (/api)
│   ├── signals.py         # Get signals (/api/signals)
│   ├── analyze.py         # Analyze token (/api/analyze/<token>)
│   ├── portfolio.py       # Portfolio data (/api/portfolio)
│   ├── holdings.py        # Holdings (/api/holdings)
│   └── trade.py           # Execute trade (/api/trade)
├── public/                # Static frontend files
│   ├── index.html        # Main HTML
│   ├── styles.css        # Phanes-inspired theme
│   └── app.js            # Frontend logic
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python deps (empty for now)
└── VERCEL_DEPLOY.md     # This file
```

---

## 🌐 API Endpoints

Once deployed, your API is available at:

```
https://your-project.vercel.app/api/health        → Health check
https://your-project.vercel.app/api/signals       → Get signals
https://your-project.vercel.app/api/analyze/<token> → Analyze token
https://your-project.vercel.app/api/portfolio     → Portfolio data
https://your-project.vercel.app/api/holdings      → Holdings
https://your-project.vercel.app/api/trade         → Execute trade (POST)
```

Test it:
```bash
curl https://your-project.vercel.app/api/health
```

---

## 🎨 Customization

### Change Colors

Edit `public/styles.css`:
```css
:root {
    --accent-primary: #8b5cf6;  /* Change this */
    --success: #10b981;          /* And this */
}
```

### Add Real Data

To connect to your Smart Money Agent:

1. Update `api/signals.py` to import and call your agent
2. Add `solana-contract-analyzer` to the project
3. Update `requirements.txt` with dependencies

Example:
```python
# api/signals.py
import sys
sys.path.append('../solana-contract-analyzer/scripts')
from smart_money_momentum_agent import SmartMoneyMomentumAgent

# Use agent to get real signals
```

---

## 🔒 Security Notes

### Current Setup (Demo Mode)
- ✅ Uses mock data (safe to deploy)
- ✅ No API keys exposed
- ✅ Read-only operations

### Production Setup
When adding real API keys:
- Store keys in Vercel Environment Variables
- Never commit keys to git
- Add rate limiting
- Consider authentication

---

## 🐛 Troubleshooting

### Build Failed
```bash
# Check vercel.json syntax
cat vercel.json | python -m json.tool

# Ensure file structure is correct
ls -la api/
ls -la public/
```

### API Not Working
```bash
# Test locally
vercel dev

# Check function logs in Vercel dashboard
```

### CORS Errors
Already configured in each API handler:
```python
self.send_header('Access-Control-Allow-Origin', '*')
```

---

## 📊 Monitoring

### Vercel Analytics
1. Go to your project dashboard
2. Click **Analytics**
3. View: Visitors, Performance, Core Web Vitals

### Function Logs
1. Go to **Deployments**
2. Click on a deployment
3. View **Function Logs**

---

## 🔄 Updates

### Automatic (Git)
Push to GitHub → Auto-deploys to Vercel

### Manual
```bash
vercel --prod
```

---

## 🎯 What's Included

✅ **Dark Theme UI** - Phanes-inspired design  
✅ **Smart Money Signals** - Visual score breakdown  
✅ **Real-time Updates** - Auto-refresh every 30s  
✅ **Responsive Design** - Works on mobile/desktop  
✅ **API Backend** - Serverless functions  
✅ **Toast Notifications** - User feedback  
✅ **Token Analysis** - Search any token  

---

## 🚀 Next Steps

1. **Deploy it!** Run `vercel --prod`
2. **Share it!** Post your URL
3. **Customize it!** Change colors, add features
4. **Connect Real Data!** Link to your Smart Money Agent

---

## 📞 Support

- Vercel Docs: https://vercel.com/docs
- Python Serverless: https://vercel.com/docs/functions/serverless-functions/runtimes/python
- Issues? Check function logs in Vercel dashboard

---

**Happy Trading! 🎯💰**
