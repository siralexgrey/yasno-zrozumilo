# 🚀 Deploy to Replit (Free Forever)

## Step 1: Prepare GitHub Repository

First, push your code to GitHub:

```bash
cd /Users/andrii.tymchenko/Development/Telegram-bots/yasno-zrozumilo
git init
git add .
git commit -m "Yasno bot - ready for Replit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/yasno-zrozumilo.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 2: Create Replit Project

1. Go to https://replit.com
2. Sign up or login with GitHub
3. Click **"Create"** (top left)
4. Select **"Import from GitHub"**
5. Paste your repo URL:
   ```
   https://github.com/YOUR_USERNAME/yasno-zrozumilo
   ```
6. Click **"Import"**
7. Wait for Replit to clone and set up

## Step 3: Add Environment Variables

1. In Replit editor, look for **"Secrets"** icon (lock icon) on left sidebar
2. Click **"Add Secret"**
3. Key: `TELEGRAM_BOT_TOKEN`
4. Value: Paste your bot token from @BotFather
5. Click **"Add Secret"**

## Step 4: Install Dependencies

1. Click **"Shell"** tab at bottom
2. Run:
   ```bash
   pip install -r requirements.txt
   ```
3. Wait for installation to complete

## Step 5: Run Bot

1. Click **"Run"** button (top center)
2. Or in Shell tab:
   ```bash
   python bot.py
   ```
3. You should see:
   ```
   Starting bot...
   Successfully fetched schedule from API
   Scheduled periodic updates every 30 minutes
   Application started
   ```

## Step 6: Keep Running 24/7

Replit has two ways to keep your bot running:

### Option A: Replit Always On (Paid, but cheap ~$7/month)
- Better for production
- Guaranteed 24/7 uptime

### Option B: Free (Requires Activity)
- Replit keeps your bot running while you have the tab open
- Or use UptimeRobot to keep it alive

## UptimeRobot Method (Free & Easy)

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Click **"Add New Monitor"**
4. Type: **"HTTP(s)"**
5. URL: Get from Replit:
   - In Replit, click **"Share"** (top right)
   - Copy **"Published URL"** (looks like: `https://yasno-bot.replit.dev`)
6. Interval: 5 minutes
7. Click **"Create Monitor"**

UptimeRobot will ping your bot every 5 minutes, keeping it alive!

## Test Your Bot

In Telegram:
1. Find your bot by username
2. Send `/start`
3. Send `/queue` to select your queue
4. Send `/myqueue` to see schedule
5. Send `/notifications` to enable alerts

## Monitor Bot

In Replit:
- **Output** tab - See what bot is doing
- **Secrets** - Manage bot token
- **Version Control** - Git history

## Update Code

When you want to update:

```bash
git add .
git commit -m "Update features"
git push
```

Then in Replit:
1. Click **"Version Control"** (left sidebar)
2. Click **"Pull"** to get latest code
3. Click **"Run"** again

Or just edit directly in Replit editor and click **"Run"**.

## Troubleshooting

**Bot not starting?**
- Check Secrets - is `TELEGRAM_BOT_TOKEN` set?
- Check output for error messages
- Token valid? Test with @BotFather

**Bot stops after a while?**
- Use UptimeRobot to keep it alive
- Or upgrade to Replit Always On

**Need more details?**
- Replit has built-in tutorials
- Check `.replit` file for configuration

## Summary

✅ Free forever on Replit
✅ No credit card needed
✅ Easy one-click deploy
✅ Use UptimeRobot to keep alive 24/7
✅ Update code anytime by pushing to GitHub

Enjoy your bot! 🎉
