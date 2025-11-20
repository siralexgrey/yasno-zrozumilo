# Event Loop Shutdown Fix

## Problem

The bot was experiencing a `RuntimeError: Event loop is closed` error when shutting down on Koyeb:

```
2025-11-19 23:29:28,516 - concurrent.futures - ERROR - exception calling callback for <Future at 0x7f263252bb20 state=finished returned list>
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/concurrent/futures/_base.py", line 330, in _invoke_callbacks
    callback(self)
  File "/usr/local/lib/python3.9/asyncio/futures.py", line 398, in _call_set_state
    dest_loop.call_soon_threadsafe(_set_state, destination, source)
  File "/usr/local/lib/python3.9/asyncio/base_events.py", line 796, in call_soon_threadsafe
    self._check_closed()
  File "/usr/local/lib/python3.9/asyncio/base_events.py", line 515, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
```

## Root Cause

This error occurred due to a race condition during shutdown:

1. **ThreadPoolExecutor callbacks**: The `requests` library (used in `fetch_schedule()`) runs synchronous HTTP calls in a ThreadPoolExecutor
2. **Event loop closure**: When Koyeb sends SIGTERM to stop the container, the event loop was being closed immediately
3. **Callback execution**: ThreadPoolExecutor callbacks tried to call `loop.call_soon_threadsafe()` on the closed loop, causing the error

## Solution

### 1. Replaced Blocking HTTP with Async

Changed from synchronous `requests` to async `aiohttp`:

```python
# Before (blocking)
async def fetch_schedule():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data

# After (async)
async def fetch_schedule():
    timeout = ClientTimeout(total=10)
    async with ClientSession(timeout=timeout) as session:
        async with session.get(API_URL) as response:
            response.raise_for_status()
            data = await response.json()
            return data
```

**Why this helps**: 
- No ThreadPoolExecutor is used
- All operations are native async/await
- No callbacks trying to access the event loop from other threads

### 2. Implemented Graceful Shutdown

Added proper shutdown sequence for webhook mode:

```python
async def run_webhook():
    try:
        # Start health server
        runner = await start_health_server()
        
        # Initialize and start application
        await application.initialize()
        await application.start()
        
        # Run forever
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Received shutdown signal")
    finally:
        # Proper cleanup order
        await application.stop()
        await runner.cleanup()
        await application.shutdown()
```

### 3. Added Signal Handlers

Proper handling of SIGTERM and SIGINT:

```python
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    # Cancel all tasks gracefully
    for task in asyncio.all_tasks(loop):
        task.cancel()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

### 4. Proper Task Cancellation

Before closing the event loop, cancel all pending tasks:

```python
finally:
    # Cancel all remaining tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    
    # Wait for cancellation to complete
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    # Now safe to close
    loop.close()
```

## Benefits

1. **No more event loop errors**: All async operations complete before loop closure
2. **Cleaner shutdown**: Resources are properly released in the correct order
3. **Better performance**: Native async HTTP calls instead of thread pool
4. **More reliable**: No race conditions between threads and event loop
5. **Koyeb compatible**: Properly handles container stop signals

## Testing

### Local Testing
```bash
# Start the bot
python bot.py

# Test graceful shutdown
pkill -SIGTERM -f "python bot.py"
```

You should see clean shutdown logs without errors.

### Koyeb Deployment

After pushing to GitHub, Koyeb will automatically redeploy. The bot will now:
- Handle health checks properly
- Process webhook requests
- Shut down gracefully when the container is stopped
- No more "Event loop is closed" errors in logs

## Technical Details

### Why ThreadPoolExecutor Was Problematic

When using `requests.get()` in an async function:
1. Python runs it in a ThreadPoolExecutor (via `loop.run_in_executor`)
2. The thread completes the HTTP request
3. It tries to notify the event loop via a callback
4. If the loop is closed, the callback fails with `RuntimeError`

### Why aiohttp Solves It

`aiohttp` is fully async:
1. Uses non-blocking sockets
2. All I/O happens on the event loop
3. No thread pool needed
4. No cross-thread callbacks
5. Everything cancels cleanly with the event loop

## Related Files

- `bot.py`: Main bot file with fixes
- `requirements.txt`: Already includes `aiohttp==3.9.1`
- `Dockerfile`: No changes needed
