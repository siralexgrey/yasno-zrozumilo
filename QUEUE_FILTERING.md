# 📋 Queue Filtering Feature Guide

The bot now supports filtering by queue groups so you can see only your specific outage schedule!

## Available Queues

The API provides schedules for 12 queue groups:
- **1.1, 1.2** - Queue group 1
- **2.1, 2.2** - Queue group 2
- **3.1, 3.2** - Queue group 3
- **4.1, 4.2** - Queue group 4
- **5.1, 5.2** - Queue group 5
- **6.1, 6.2** - Queue group 6

## How to Use

### Method 1: Save Your Queue (Recommended)

1. **Select your queue:**
   ```
   /queue
   ```
   The bot will show buttons with all available queues. Click your queue (e.g., "5.1")

2. **View your queue anytime:**
   ```
   /myqueue
   ```
   This will show only your saved queue

### Method 2: Filter by Command Argument

You can filter any queue on-the-fly without saving:
```
/schedule 5.1
```

### Method 3: View All Queues

To see all queues at once:
```
/schedule
```

## Commands Summary

| Command | Description |
|---------|-------------|
| `/queue` | Select your queue and save preference |
| `/myqueue` | Show schedule for your saved queue |
| `/schedule` | Show all queues |
| `/schedule 5.1` | Show specific queue (e.g., 5.1) |

## Example Usage

### Scenario 1: First Time User

```
You: /queue
Bot: [Shows buttons: 1.1, 1.2, 2.1, ... 6.2]
You: [Click "5.1"]
Bot: ✅ Черга 5.1 збережена!

You: /myqueue
Bot: ⚡️ Графік планових відключень
     🔸 Фільтр: Черга 5.1
     
     📅 Сьогодні (2025-11-18):
       🔴 01:00 - 04:30 (відключення)
       🔴 11:30 - 18:30 (відключення)
       ...
```

### Scenario 2: Check Different Queue Temporarily

```
You: /schedule 3.2
Bot: [Shows only queue 3.2]

You: /myqueue
Bot: [Shows your saved queue 5.1]
```

### Scenario 3: Reset to Show All

```
You: /queue
Bot: [Shows buttons]
You: [Click "📋 Показати всі черги"]
Bot: ✅ Налаштування скинуто!
```

## Benefits

✅ **Cleaner Output** - See only what matters to you
✅ **Quick Access** - Use `/myqueue` for instant results
✅ **Flexible** - Temporarily check other queues anytime
✅ **Persistent** - Your queue preference is saved per user

## Implementation Details

- User preferences are stored in memory (resets when bot restarts)
- Each user can have their own queue preference
- Works in both private chats and group chats
- Filtering happens server-side for better performance

## Testing Queue Filtering

Run the test script:
```bash
python test_queue_filter.py
```

This will show:
- All queues output
- Filtered output for queue 5.1
- Filtered output for queue 3.2
- Error handling for invalid queue
