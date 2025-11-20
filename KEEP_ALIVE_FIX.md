# Keep-Alive Fix for Koyeb Sleep Issue

## Problem
Koyeb puts the instance to sleep after 5 minutes of no HTTP traffic, even though:
- The bot's scheduled tasks run every 10 minutes
- The health check server is running
- The application is "healthy"

Koyeb's sleep detection is based on **incoming HTTP requests**, not just server availability.

## Solution
Added a `keep_alive_ping()` function that:
1. Pings the bot's own health endpoint every 4 minutes
2. Generates HTTP traffic to prevent Koyeb from detecting "no traffic"
3. Only runs in webhook mode (Koyeb deployment)
4. Starts 1 minute after bot initialization

## Implementation Details

### New Function: `keep_alive_ping()`
```python
async def keep_alive_ping(context) -> None:
    """
    Periodic task to ping the health endpoint and prevent Koyeb from sleeping.
    Runs every 4 minutes (before the 5-minute sleep timeout).
    """
```

### Scheduled in `post_init()`
```python
# Only in webhook mode (Koyeb)
if os.getenv('WEBHOOK_URL'):
    job_queue.run_repeating(
        keep_alive_ping,
        interval=240,  # 4 minutes
        first=60  # Start after 1 minute
    )
```

## Why This Works
- **4-minute interval**: Shorter than Koyeb's 5-minute timeout
- **Self-ping**: Creates HTTP traffic that Koyeb monitors
- **Webhook-only**: Doesn't interfere with local polling mode
- **Minimal overhead**: Simple GET request every 4 minutes

## Expected Behavior

### Before Fix
```
13:23:16 - Schedule update
No traffic for 5 minutes...
14:30:58 - Koyeb sends SIGTERM (sleep)
```

### After Fix
```
14:52:47 - Bot starts
14:53:47 - Keep-alive ping ✅
14:57:47 - Keep-alive ping ✅
15:01:47 - Keep-alive ping ✅
15:02:47 - Schedule update
15:05:47 - Keep-alive ping ✅
... (no sleep!)
```

## Deployment
Just push the changes to deploy:
```bash
git add bot.py KEEP_ALIVE_FIX.md
git commit -m "Add keep-alive pings to prevent Koyeb sleep"
git push
```

## Monitoring
Watch the logs for:
- `✅ Keep-alive ping successful` - every 4 minutes
- `✅ Scheduled keep-alive pings every 4 minutes` - on startup
- No more "No traffic detected" messages

## Alternative Approaches (Not Needed)
- ❌ External uptime monitoring (UptimeRobot) - adds external dependency
- ❌ Reduce schedule interval to < 5 minutes - too frequent API calls
- ❌ Keep-alive HTTP header - doesn't generate new requests
- ✅ **Self-ping** - Simple, reliable, no external dependencies
