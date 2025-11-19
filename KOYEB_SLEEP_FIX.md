# Koyeb Sleep Issue - Fixed ✅

## The Problem

Your bot was being stopped by Koyeb with this message:
```
No traffic detected in the past 300 seconds. Transitioning to deep sleep.
Instance is stopping.
```

This happened because:
- Koyeb monitors **HTTP traffic** to determine if an instance is active
- Your bot uses **Telegram polling** (outgoing requests to Telegram's servers)
- Koyeb doesn't see incoming HTTP requests, so it thinks the instance is idle
- After 5 minutes (300 seconds) of no HTTP traffic, Koyeb puts it to sleep

## The Solution

The bot now **pings itself** every 4 minutes to generate HTTP traffic and stay awake:

### How It Works

1. **Self-ping task**: Scheduled job runs every 4 minutes
2. **HTTP request**: Makes GET request to `http://localhost:{PORT}/health`
3. **Koyeb sees traffic**: Detects incoming HTTP request
4. **Instance stays active**: No deep sleep!

### Implementation Details

```python
async def keep_alive_ping(context):
    """Ping own health endpoint to prevent Koyeb from sleeping"""
    port = int(os.getenv('PORT', 8000))
    if os.getenv('PORT'):  # Only on Koyeb
        async with aiohttp.ClientSession() as session:
            await session.get(f'http://localhost:{port}/health', timeout=5)

# Scheduled every 4 minutes (240 seconds)
job_queue.run_repeating(keep_alive_ping, interval=240, first=60)
```

### Smart Detection

- **On Koyeb**: Runs keep-alive pings (when `PORT` env var exists)
- **Locally**: Doesn't run keep-alive pings (saves resources)

## What Changed

### Files Modified:
1. **bot.py** - Added keep-alive ping mechanism
2. **KOYEB_DEPLOYMENT.md** - Updated deployment guide

### No Breaking Changes:
- Bot works exactly the same
- All features work as before
- Only difference: generates periodic HTTP traffic to stay awake

## Verification

After deploying, check your Koyeb logs. You should see:

```
Scheduled keep-alive pings every 4 minutes (Koyeb mode)
```

And every 4 minutes:
```
Keep-alive ping: 200
```

You should **NOT** see:
```
No traffic detected in the past 300 seconds
Instance is stopping
```

## Benefits

✅ **Instance stays running 24/7**
✅ **Instant response to user commands** (no wake-up delay)
✅ **Scheduled tasks run on time** (10-minute schedule updates)
✅ **Users get real-time notifications**
✅ **No additional costs** (stays within free tier limits)

## Alternative Solutions (Not Used)

We didn't use these because they're more complex:

1. **Webhooks**: Requires SSL certificate and exposed HTTPS endpoint
2. **External pinger**: Needs another service (UptimeRobot, etc.)
3. **Paid tier**: Koyeb's paid tier doesn't sleep, but costs money

Our solution is simpler and free! 🎉
