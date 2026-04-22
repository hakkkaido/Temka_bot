#!/bin/bash
# 🚀 Быстрый старт Gemini Bot

set -e

echo "════════════════════════════════════════════════════════"
echo "  🤖 GEMINI BOT - Quick Start"
echo "════════════════════════════════════════════════════════"
echo ""

# Check Python
echo "1️⃣  Checking Python version..."
python3 --version
echo ""

# Install dependencies
echo "2️⃣  Installing dependencies..."
pip install -q -U google-genai aiogram python-dotenv httpx
echo "   ✅ Dependencies installed"
echo ""

# Create workspace directory
echo "3️⃣  Creating workspace..."
mkdir -p workspace data
echo "   ✅ Workspace created"
echo ""

# Run tests
echo "4️⃣  Running configuration tests..."
python3 test_setup.py
echo ""

# Ready!
echo "════════════════════════════════════════════════════════"
echo "  ✅ ALL DONE! Bot is ready to launch"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📌 Next step: Start the bot"
echo "   Command: python3 main.py"
echo ""
echo "📱 Send messages to Telegram chat: $(grep TELEGRAM_CHAT_ID .env | cut -d'=' -f2)"
echo ""
echo "📖 Documentation: https://github.com/hakkkaido/Temka_bot"
echo "════════════════════════════════════════════════════════"
