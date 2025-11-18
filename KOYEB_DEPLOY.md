# 🚀 Koyeb Deployment Guide

## ✅ Prerequisites
- GitHub account
- Telegram Bot Token from @BotFather
- This repository pushed to GitHub

---

## 📦 Deployment Steps

### 1. **Create Koyeb Account**
1. Go to https://app.koyeb.com
2. Sign up with GitHub (no credit card required!)
3. Verify your email

### 2. **Deploy Your Bot**
1. Click **"Create Service"**
2. Select **"GitHub"**
3. Connect your GitHub account
4. Select repository: `yasno-zrozumilo`
5. Configure:
   - **Builder**: Dockerfile
   - **Dockerfile path**: `Dockerfile` (default)
   - **Port**: Leave empty (not a web service)
   
### 3. **Add Environment Variables**
Click **"Environment variables"** and add:
```
TELEGRAM_BOT_TOKEN=your_actual_token_here
```

### 4. **Configure Service**
- **Service name**: `yasno-bot` (or your choice)
- **Region**: Choose closest to Ukraine (Frankfurt recommended)
- **Instance type**: **Nano** (Free tier - 512MB RAM)

### 5. **Deploy!**
Click **"Deploy"** button

---

## 📊 Monitoring Your Bot

### In Koyeb Dashboard:
- ✅ **Logs**: Click on your service → "Logs" tab
- ✅ **Status**: Green = Running
- ✅ **Restarts**: Auto-restarts on crash
- ✅ **Metrics**: CPU/Memory usage

### Expected Log Output:
```
INFO - Starting bot...
INFO - Loaded preferences for X users with queues
INFO - Using cached schedule data
INFO - Schedule updated at 2025-11-18 06:09:05+02:00
INFO - Scheduled periodic updates every 30 minutes
INFO - Application started
```

---

## 🔧 Troubleshooting

### Bot not responding?
1. Check logs in Koyeb dashboard
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Restart service

### Service keeps restarting?
1. Check error logs
2. Verify Dockerfile builds correctly locally:
   ```bash
   docker build -t yasno-bot .
   docker run -e TELEGRAM_BOT_TOKEN=your_token yasno-bot
   ```

### Need to update bot?
1. Push changes to GitHub
2. Koyeb auto-deploys (or click "Redeploy")

---

## 💾 Data Persistence

Your bot saves:
- `user_preferences.json` - User settings
- `schedule_cache.json` - Cached schedule data

**Note**: Koyeb free tier has **ephemeral storage** - data resets on redeploy.
To persist data, upgrade to paid plan with persistent volumes.

---

## 🎯 Post-Deployment Checklist

- [ ] Bot responds to `/start` command
- [ ] Can select queue with `/queue`
- [ ] Notifications working (test in 30 min)
- [ ] Check logs for any errors
- [ ] Set up UptimeRobot monitoring (optional)

---

## 📈 Optional: UptimeRobot Monitoring

1. Go to https://uptimerobot.com
2. Add monitor:
   - **Type**: Keyword Monitor
   - **URL**: Your Koyeb service URL/health endpoint
   - Or use Telegram bot status check
3. Get alerts if bot goes down

---

## 🔄 Updating Your Bot

```bash
# Make changes locally
git add .
git commit -m "Update bot"
git push origin main

# Koyeb auto-deploys in ~2 minutes
```

---

## 💰 Cost

**Koyeb Free Tier:**
- ✅ 100% FREE
- ✅ No credit card
- ✅ 1 service always running
- ✅ 512MB RAM
- ✅ Enough for this bot!

---

## 🆘 Need Help?

- Koyeb Docs: https://www.koyeb.com/docs
- Koyeb Discord: https://discord.gg/koyeb
- Check Koyeb status: https://status.koyeb.com

---

## 🎉 You're Done!

Your bot is now:
- ✅ Running 24/7
- ✅ Auto-restarting on crashes
- ✅ Auto-deploying on GitHub pushes
- ✅ 100% FREE!

Test it: Open Telegram → Search for your bot → Send `/start`
