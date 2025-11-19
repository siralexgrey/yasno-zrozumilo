# Koyeb Deployment Guide

## Problem: Instance Goes to Sleep

Koyeb puts instances into "deep sleep" after 5 minutes of no HTTP traffic. Since this bot uses Telegram's long-polling (not webhooks), Koyeb doesn't detect activity and stops the instance.

## Solution Implemented

The bot now automatically pings its own health endpoint every 4 minutes to keep the instance awake. This works by:

1. **Self-ping mechanism**: Bot sends HTTP request to itself (`/health`)
2. **Frequency**: Every 4 minutes (safely under the 5-minute timeout)
3. **Smart detection**: Only activates when `PORT` env var exists (Koyeb deployment)
4. **No local impact**: Doesn't run when testing locally

## Koyeb Configuration

### 1. Build Settings
- **Build command**: (leave empty or use default)
- **Run command**: `.venv/bin/python bot.py` or `python bot.py`

### 2. Environment Variables
Make sure these are set in Koyeb:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `GITHUB_TOKEN` - (Optional) For persistent storage via Gist
- `GIST_ID` - (Optional) Your GitHub Gist ID
- `PORT` - **This is automatically set by Koyeb** (no need to add manually)

### 3. Health Check
- **Path**: `/health` or `/`
- **Port**: Use the port exposed by the service (Koyeb handles this automatically)
- **Protocol**: HTTP

### 4. Instance Settings
- **Type**: Web service
- **Scaling**: Single instance (or auto-scale as needed)
- **Region**: Choose closest to your users

## Deployment Strategy

Koyeb uses **rolling deployment** by default:
1. New instance starts on a different port
2. Health check ensures new instance is ready
3. Traffic switches to new instance
4. Old instance is terminated

## Troubleshooting

### Port Conflict Errors
If you still see port conflicts:
1. Check that you're not hardcoding port 8000 anywhere
2. Ensure the `PORT` environment variable is being used
3. Verify health check endpoint is working: `/health`

### Instance Not Starting
1. Check logs in Koyeb dashboard
2. Verify all environment variables are set
3. Ensure `requirements.txt` is up to date
4. Check that the health check endpoint responds with 200 OK

### Old Instance Won't Stop
This is now handled automatically by:
- Using Koyeb's assigned PORT (different for each instance)
- Health check validation before traffic switch
- Automatic termination of old instance after new one is healthy

## Local Testing

When running locally, the bot will use port 8000 by default:
```bash
python bot.py
```

To test with a different port:
```bash
PORT=3000 python bot.py
```

## Monitoring

Check your deployment status:
1. Koyeb Dashboard → Your Service → Deployments
2. View logs for any errors
3. Test health endpoint: `https://your-app.koyeb.app/health`
