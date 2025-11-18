# ⚡ Replit Quick Start (5 Minutes)

## Prerequisites
- GitHub account (free)
- Telegram bot token from @BotFather
- Replit account (free, sign up with GitHub)

## Step 1: Push Code to GitHub

```bash
cd /Users/andrii.tymchenko/Development/Telegram-bots/yasno-zrozumilo
git init
git add .
git commit -m "Yasno bot for Replit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/yasno-zrozumilo.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 2: Create Replit Project (30 seconds)

1. Visit https://replit.com
2. Click **Create**
3. Click **Import from GitHub**
4. Paste: `https://github.com/YOUR_USERNAME/yasno-zrozumilo`
5. Click **Import**

Done! Replit clones and sets up your project.

## Step 3: Add Bot Token (1 minute)

1. In Replit, find the lock icon (Secrets) on left
2. Click **Add Secret**
3. Key: `TELEGRAM_BOT_TOKEN`
4. Value: Paste your token from @BotFather
5. Click **Add Secret**

## Step 4: Install & Run (1 minute)

1. Click **Run** (top button)
2. Replit auto-installs `requirements.txt`
3. Bot starts running!

You should see in output:
```
Starting bot...
Successfully fetched schedule from API
Scheduled periodic updates every 30 minutes
Application started
```

## Step 5: Keep Running 24/7 (2 minutes)

Option A: **UptimeRobot (Free)**
1. Go to https://uptimerobot.com
2. Sign up (free)
3. Click **Add New Monitor**
4. Get your Replit URL:
   - In Replit, click **Share** (top right)
   - Copy the URL (looks like `https://yasno-bot.replit.dev`)
5. Paste URL in UptimeRobot
6. Set interval to 5 minutes
7. Create monitor

Done! Your bot stays alive 24/7!

## Test It!

In Telegram:
- Search for your bot by username
- Send `/start`
- Send `/queue` → select your queue
- Send `/myqueue` → see your schedule
- Send `/notifications` → enable alerts

## Update Code

Push changes to GitHub:
```bash
git add .
git commit -m "Update features"
git push
```

Then in Replit:
1. Click **Version Control** (left sidebar)
2. Click **Pull**
3. Click **Run**

## Free Forever?

✅ Replit: Free
✅ UptimeRobot: Free
✅ GitHub: Free
✅ Telegram Bot: Free

**Total Cost: $0/month** 🎉

## Need Help?

- See `REPLIT_DEPLOY.md` for detailed guide
- Replit has built-in tutorials
- Check bot output for errors

Enjoy your 24/7 bot! 🚀
