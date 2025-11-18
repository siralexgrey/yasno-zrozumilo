#!/bin/bash

# Quick Setup Script for Yasno Zrozumilo Bot

echo "🤖 Yasno Zrozumilo Bot - Quick Setup"
echo "===================================="
echo ""

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ .env file already exists"
else
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your TELEGRAM_BOT_TOKEN"
    echo ""
    echo "To get a token:"
    echo "  1. Open Telegram and search for @BotFather"
    echo "  2. Send /newbot and follow the prompts"
    echo "  3. Copy the token and paste it in .env"
    echo ""
    read -p "Press Enter to open .env in nano (or Ctrl+C to exit)..."
    nano .env
fi

echo ""
echo "🧪 Running tests..."
python test_bot.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the bot, run:"
echo "  python bot.py"
echo ""
echo "Or use this command to run in background:"
echo "  nohup python bot.py > bot.log 2>&1 &"
