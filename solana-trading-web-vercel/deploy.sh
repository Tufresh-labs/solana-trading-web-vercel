#!/bin/bash

# 1SOL Trader - Vercel Deploy Script
# Usage: ./deploy.sh

echo "🚀 1SOL Trader Vercel Deploy"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check API key is configured
if grep -q "cfb197fe-7adf-4a30-a2f0-9dfdbb5924dd" vercel.json; then
    echo -e "${GREEN}✓ Helius API key configured${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  API key not found in vercel.json${NC}"
    echo ""
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "⚠️  Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Check if logged in
echo "🔐 Checking Vercel login..."
vercel whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "Please login to Vercel:"
    vercel login
fi

# Confirm deployment
echo ""
echo -e "${BLUE}Ready to deploy 1SOL Trader with:${NC}"
echo "  • Real Smart Money Analysis"
echo "  • Helius API Integration"
echo "  • Serverless Functions"
echo "  • Phanes-inspired UI"
echo ""
read -p "Continue deployment? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Deploy
echo ""
echo "📦 Deploying to Vercel..."
vercel --prod

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "🎉 Your 1SOL Trader is now LIVE!"
    echo ""
    echo "Next steps:"
    echo "  1. Visit your deployed URL (shown above)"
    echo "  2. Test the API: /api/signals"
    echo "  3. Try searching a token address"
    echo "  4. Share it with your friends!"
    echo ""
    echo -e "${BLUE}Features enabled:${NC}"
    echo "  ✓ Real-time Smart Money analysis"
    echo "  ✓ Helius RPC integration"
    echo "  ✓ Holder tracking (whales, smart wallets)"
    echo "  ✓ Volume momentum detection"
    echo "  ✓ Combined scoring algorithm"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Deployment failed${NC}"
    echo "Check the error messages above."
    echo ""
    echo "Common fixes:"
    echo "  • Run 'vercel login' first"
    echo "  • Check your internet connection"
    echo "  • Ensure all files are committed"
    exit 1
fi
