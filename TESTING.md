# 🧪 Testing Guide for Yasno Zrozumilo Bot

## Prerequisites

✅ **Dependencies installed** (already done)
✅ **API is working** (verified)

## Step 1: Get Your Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name for your bot (e.g., "Yasno Zrozumilo")
   - Choose a username (must end in 'bot', e.g., "yasno_zrozumilo_bot")
4. Copy the token that BotFather gives you (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Configure the Bot

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add your token:
```
TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_TOKEN_HERE
```

## Step 3: Run the Bot

```bash
python bot.py
```

You should see:
```
INFO - Starting bot...
INFO - Updating schedule...
INFO - Successfully fetched schedule from API
INFO - Schedule updated at 2025-11-18 12:34:56
INFO - Scheduled periodic updates every 30 minutes
```

## Step 4: Test Commands in Telegram

### In Private Chat:

1. **Find your bot**: Search for your bot's username in Telegram
2. **Start the bot**: Send `/start`
3. **Test commands**:
   - `/schedule` - Should show the power outage schedule
   - `/status` - Should show when data was last updated
   - `/help` - Should show help information

### In Group Chat:

1. **Add bot to group**: 
   - Create a test group or use existing one
   - Add your bot as a member
2. **Test commands** (same as private chat)

## Step 5: Verify Automatic Updates

The bot fetches data every 30 minutes. To test:

1. Send `/status` - note the "Last update" time
2. Wait 30+ minutes (or adjust `UPDATE_INTERVAL` in bot.py for faster testing)
3. Send `/status` again - should show updated time

## Quick Test Mode (Optional)

To test updates faster, temporarily change the interval:

Edit `bot.py`, line 28:
```python
UPDATE_INTERVAL = 60  # 1 minute instead of 1800 (30 minutes)
```

Then restart the bot.

## Testing Checklist

- [ ] Bot starts without errors
- [ ] Initial data fetch succeeds
- [ ] `/start` command works
- [ ] `/schedule` displays formatted schedule
- [ ] `/status` shows last update time
- [ ] `/help` shows help text
- [ ] Bot works in private chat
- [ ] Bot works in group chat
- [ ] Automatic updates happen every 30 minutes
- [ ] Data formatting is readable

## Troubleshooting

### Bot doesn't start
- Check that TELEGRAM_BOT_TOKEN is set correctly in `.env`
- Verify the token with @BotFather

### "Connection error"
- Check your internet connection
- Try running `python test_api.py` to verify API access

### Bot doesn't respond
- Make sure the bot is running (terminal shows no errors)
- Check if you're sending commands to the correct bot

### Schedule not showing
- Wait a few seconds after starting the bot for initial data fetch
- Check terminal logs for API errors

## Expected Output Example

When you send `/schedule`, you should see something like:

```
⚡️ Графік планових відключень

🔸 Черга 1.1
📅 Сьогодні (2025-11-18):
  🔴 04:30 - 11:30 (відключення)
  🔴 15:00 - 21:00 (відключення)
📅 Завтра (2025-11-19):
  ⏳ Очікується графік

🔸 Черга 1.2
...
```

## Advanced Testing

### Test API directly:
```bash
python test_api.py
```

### Monitor logs:
Watch the terminal output while the bot runs to see:
- When updates happen
- Any errors or warnings
- User commands received

### Test error handling:
1. Disconnect from internet
2. Send `/schedule`
3. Should still show cached data (if available)

## Stop the Bot

Press `Ctrl+C` in the terminal where the bot is running.
