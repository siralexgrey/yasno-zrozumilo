#!/usr/bin/env python3
"""
Yasno Zrozumilo Telegram Bot
Fetches planned power outage schedules from Yasno API and displays them to users.
"""

import os
import logging
import asyncio
import json
import signal
import sys
import atexit
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession, ClientTimeout
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Configuration - Multiple cities support
CITIES = {
    'dnipro': {
        'name': 'Дніпро',
        'api_url': 'https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages'
    },
    'kyiv': {
        'name': 'Київ',
        'api_url': 'https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/25/dsos/902/planned-outages'
    }
}

UPDATE_INTERVAL = 600  # 10 minutes in seconds

# Persistent storage file paths
PREFERENCES_FILE = "user_preferences.json"
SCHEDULE_CACHE_FILE = "schedule_cache.json"

# GitHub Gist configuration for persistent storage
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GIST_ID = os.getenv('GIST_ID')

# Global storage for schedule data (per city)
schedule_data: Dict[str, Optional[Dict[str, Any]]] = {'dnipro': None, 'kyiv': None}
last_update: Dict[str, Optional[datetime]] = {'dnipro': None, 'kyiv': None}  # When data was updated in Yasno API (from updatedOn)
last_fetch: Dict[str, Optional[datetime]] = {'dnipro': None, 'kyiv': None}  # When we last fetched data from API

# User preferences for queue filtering (user_id -> queue_name)
user_queue_preferences: Dict[int, Optional[str]] = {}

# User city selection (user_id -> city_code)
user_city_preferences: Dict[int, str] = {}

# User notification preferences (user_id -> chat_id)
# Stores chat IDs of users who want automatic notifications
user_notifications: Dict[int, int] = {}


def get_main_keyboard(has_city: bool = True) -> ReplyKeyboardMarkup:
    """Get the main reply keyboard for the bot."""
    if has_city:
        keyboard = [
            ["📋 Графік", "🔸 Моя черга"],
            ["🏙️ Місто", "⚙️ Вибрати чергу"],
            ["🔔 Сповіщення", "📊 Статус"],
            ["ℹ️ Довідка"]
        ]
    else:
        # Minimal keyboard when city is not selected
        keyboard = [
            ["🏙️ Вибрати місто"],
            ["ℹ️ Довідка"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


async def load_preferences() -> None:
    """Load user preferences from JSON file or GitHub Gist."""
    global user_queue_preferences, user_notifications, user_city_preferences, last_update
    
    # Try to load from GitHub Gist first (persistent storage)
    if GITHUB_TOKEN and GIST_ID:
        try:
            logger.info(f"Loading preferences from GitHub Gist (ID: {GIST_ID[:8]}...)...")
            headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(f'https://api.github.com/gists/{GIST_ID}', headers=headers) as response:
                    if response.status == 200:
                        gist_data = await response.json()
                        if 'user_preferences.json' in gist_data['files']:
                            content = gist_data['files']['user_preferences.json']['content']
                            data = json.loads(content)
                            
                            # Convert string keys back to integers
                            user_queue_preferences = {int(k): v for k, v in data.get('queues', {}).items()}
                            user_notifications = {int(k): v for k, v in data.get('notifications', {}).items()}
                            user_city_preferences = {int(k): v for k, v in data.get('cities', {}).items()}
                            
                            # Restore last update time with proper timezone - for backward compatibility
                            if 'last_update' in data and data['last_update']:
                                try:
                                    from datetime import timezone, timedelta as td
                                    schedule_tz = timezone(td(hours=2))
                                    last_update_dt = datetime.fromisoformat(data['last_update'])
                                    # Ensure timezone is set to +02:00
                                    if last_update_dt.tzinfo is None:
                                        last_update_dt = last_update_dt.replace(tzinfo=schedule_tz)
                                    else:
                                        last_update_dt = last_update_dt.astimezone(schedule_tz)
                                    # Set for dnipro (legacy)
                                    last_update['dnipro'] = last_update_dt
                                    logger.info(f"Restored last update time from Gist: {last_update_dt}")
                                except Exception as e:
                                    logger.warning(f"Could not restore last update time: {e}")
                            
                            # Restore per-city last update times
                            if 'last_update_cities' in data:
                                for city, update_time_str in data['last_update_cities'].items():
                                    if update_time_str:
                                        try:
                                            from datetime import timezone, timedelta as td
                                            schedule_tz = timezone(td(hours=2))
                                            update_dt = datetime.fromisoformat(update_time_str)
                                            if update_dt.tzinfo is None:
                                                update_dt = update_dt.replace(tzinfo=schedule_tz)
                                            else:
                                                update_dt = update_dt.astimezone(schedule_tz)
                                            last_update[city] = update_dt
                                        except Exception as e:
                                            logger.warning(f"Could not restore {city} update time: {e}")
                            
                            logger.info(f"✅ Successfully loaded from Gist: {len(user_queue_preferences)} users with queues, {len(user_notifications)} with notifications, {len(user_city_preferences)} with cities")
                            logger.info(f"Loaded queues: {user_queue_preferences}")
                            logger.info(f"Loaded notifications: {user_notifications}")
                            logger.info(f"Loaded cities: {user_city_preferences}")
                            
                            # Also save to local file as backup
                            save_preferences_local()
                            return
        except Exception as e:
            logger.warning(f"Failed to load from GitHub Gist: {e}. Falling back to local file.")
    else:
        logger.info(f"GitHub Gist not configured (Token: {'set' if GITHUB_TOKEN else 'missing'}, Gist ID: {'set' if GIST_ID else 'missing'})")
    
    # Fallback to local file
    if not os.path.exists(PREFERENCES_FILE):
        logger.info("No preferences file found, starting with empty preferences")
        return
    
    try:
        with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert string keys back to integers (JSON keys are always strings)
        user_queue_preferences = {int(k): v for k, v in data.get('queues', {}).items()}
        user_notifications = {int(k): v for k, v in data.get('notifications', {}).items()}
        user_city_preferences = {int(k): v for k, v in data.get('cities', {}).items()}
        
        # Restore last update time with proper timezone - for backward compatibility
        if 'last_update' in data and data['last_update']:
            try:
                from datetime import timezone, timedelta as td
                schedule_tz = timezone(td(hours=2))
                last_update_dt = datetime.fromisoformat(data['last_update'])
                # Ensure timezone is set to +02:00
                if last_update_dt.tzinfo is None:
                    last_update_dt = last_update_dt.replace(tzinfo=schedule_tz)
                else:
                    last_update_dt = last_update_dt.astimezone(schedule_tz)
                # Set for dnipro (legacy)
                last_update['dnipro'] = last_update_dt
                logger.info(f"Restored last update time: {last_update_dt}")
            except Exception as e:
                logger.warning(f"Could not restore last update time: {e}")
        
        # Restore per-city last update times
        if 'last_update_cities' in data:
            for city, update_time_str in data['last_update_cities'].items():
                if update_time_str:
                    try:
                        from datetime import timezone, timedelta as td
                        schedule_tz = timezone(td(hours=2))
                        update_dt = datetime.fromisoformat(update_time_str)
                        if update_dt.tzinfo is None:
                            update_dt = update_dt.replace(tzinfo=schedule_tz)
                        else:
                            update_dt = update_dt.astimezone(schedule_tz)
                        last_update[city] = update_dt
                    except Exception as e:
                        logger.warning(f"Could not restore {city} update time: {e}")
        
        logger.info(f"Loaded preferences for {len(user_queue_preferences)} users with queues")
        logger.info(f"Loaded notification settings for {len(user_notifications)} users")
        logger.info(f"Loaded city preferences for {len(user_city_preferences)} users")
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")


async def save_preferences() -> None:
    """Save user preferences to JSON file and GitHub Gist."""
    logger.info(f"💾 Saving preferences: {len(user_queue_preferences)} queues, {len(user_notifications)} notifications, {len(user_city_preferences)} cities")
    logger.info(f"Queues being saved: {user_queue_preferences}")
    logger.info(f"Notifications being saved: {user_notifications}")
    logger.info(f"Cities being saved: {user_city_preferences}")
    
    # Save to local file first
    save_preferences_local()
    
    # Also save to GitHub Gist for persistence across redeploys
    if GITHUB_TOKEN and GIST_ID:
        try:
            data = {
                'queues': user_queue_preferences,
                'notifications': user_notifications,
                'cities': user_city_preferences,
                'last_update': last_update['dnipro'].isoformat() if last_update.get('dnipro') else None,  # Legacy
                'last_update_cities': {
                    city: dt.isoformat() if dt else None
                    for city, dt in last_update.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            payload = {
                'files': {
                    'user_preferences.json': {
                        'content': json.dumps(data, indent=2, ensure_ascii=False)
                    }
                }
            }
            
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                async with session.patch(
                    f'https://api.github.com/gists/{GIST_ID}',
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info("User preferences saved to GitHub Gist")
                    else:
                        logger.warning(f"Failed to save to Gist: {response.status}")
        except Exception as e:
            logger.warning(f"Failed to save to GitHub Gist: {e}")


def save_preferences_local() -> None:
    """Save user preferences to local JSON file."""
    try:
        data = {
            'queues': user_queue_preferences,
            'notifications': user_notifications,
            'cities': user_city_preferences,
            'last_update': last_update['dnipro'].isoformat() if last_update.get('dnipro') else None,  # Legacy
            'last_update_cities': {
                city: dt.isoformat() if dt else None
                for city, dt in last_update.items()
            },
            'last_saved': datetime.now().isoformat()
        }
        
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("User preferences saved locally")
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")


def save_schedule_cache(data: Dict[str, Any]) -> None:
    """Save schedule data with updatedOn timestamps to cache file."""
    try:
        cache_data = {
            'schedule': data,
            'cached_at': datetime.now().isoformat()
        }
        
        with open(SCHEDULE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.debug("Schedule cache saved")
    except Exception as e:
        logger.error(f"Failed to save schedule cache: {e}")


def load_schedule_cache() -> Optional[Dict[str, Any]]:
    """Load cached schedule data with updatedOn timestamps."""
    global schedule_data, last_update
    
    if not os.path.exists(SCHEDULE_CACHE_FILE):
        logger.info("No schedule cache found")
        return None
    
    try:
        with open(SCHEDULE_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        schedule = cache_data.get('schedule')
        cached_at = cache_data.get('cached_at')
        
        if schedule:
            logger.info(f"Loaded cached schedule from {cached_at}")
            return schedule
        
        return None
    except Exception as e:
        logger.error(f"Failed to load schedule cache: {e}")
        return None


async def fetch_schedule(city: str = 'dnipro') -> Optional[Dict[str, Any]]:
    """
    Fetch the power outage schedule from Yasno API using aiohttp.
    
    Args:
        city: City code ('dnipro' or 'kyiv')
    
    Returns:
        Dictionary with schedule data or None if request fails
    """
    if city not in CITIES:
        logger.error(f"Invalid city code: {city}")
        return None
    
    api_url = CITIES[city]['api_url']
    
    try:
        logger.info(f"Fetching schedule from API for {CITIES[city]['name']}: {api_url}")
        timeout = ClientTimeout(total=10)
        async with ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as response:
                logger.info(f"API response status: {response.status}")
                response.raise_for_status()
                data = await response.json()
                logger.info(f"Successfully fetched schedule from API - {len(data)} queues for {CITIES[city]['name']}")
                save_schedule_cache(data)  # Save to cache with updatedOn timestamps
                return data
    except Exception as e:
        logger.error(f"Error fetching schedule for {city}: {e}", exc_info=True)
        return None


def has_schedule_changed(old_data: Dict[str, Any], new_data: Dict[str, Any], queue_name: str) -> tuple[bool, list[str]]:
    """
    Check if schedule changed for a specific queue.
    Excludes natural date rollovers (when tomorrow becomes today).
    
    Returns:
        Tuple of (changed: bool, changes: list of change descriptions)
    """
    changes = []
    
    if not old_data or not new_data:
        return False, []
    
    old_queue = old_data.get(queue_name, {})
    new_queue = new_data.get(queue_name, {})
    
    if not old_queue or not new_queue:
        return False, []
    
    # First check: if entire queue objects are identical, no change
    if old_queue == new_queue:
        logger.debug(f"Queue {queue_name}: objects are identical, no change")
        return False, []
    
    logger.debug(f"Queue {queue_name}: objects differ, analyzing changes...")
    
    # Get slot data
    old_today_slots = old_queue.get('today', {}).get('slots', [])
    new_today_slots = new_queue.get('today', {}).get('slots', [])
    old_tomorrow_slots = old_queue.get('tomorrow', {}).get('slots', [])
    new_tomorrow_slots = new_queue.get('tomorrow', {}).get('slots', [])
    
    # Check for natural date rollover: old tomorrow becomes new today
    # This happens at midnight and should NOT trigger a notification
    is_date_rollover = (
        old_tomorrow_slots and 
        new_today_slots and 
        old_tomorrow_slots == new_today_slots and
        old_today_slots != new_today_slots  # Today actually changed
    )
    
    if is_date_rollover:
        # This is just a natural date change, not a schedule update
        return False, []
    
    # Check if updatedOn changed
    old_updated = old_queue.get('updatedOn', '')
    new_updated = new_queue.get('updatedOn', '')
    
    if old_updated != new_updated:
        # Format the date nicely: "2025-11-20T15:09:44+02:00" -> "20.11.2025 15:09"
        try:
            from datetime import timezone, timedelta as td
            schedule_tz = timezone(td(hours=2))
            updated_dt = datetime.fromisoformat(new_updated)
            # Convert to +02:00 timezone if needed
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=schedule_tz)
            else:
                updated_dt = updated_dt.astimezone(schedule_tz)
            formatted_date = updated_dt.strftime('%d.%m.%Y %H:%M')
            changes.append(f"Графік оновлено: {formatted_date}")
        except Exception:
            # Fallback to truncated string if parsing fails
            changes.append(f"Графік оновлено: {new_updated[:16]}")
    
    # Check for emergency status changes
    old_today = old_queue.get('today', {})
    new_today = new_queue.get('today', {})
    old_today_status = old_today.get('status', '')
    new_today_status = new_today.get('status', '')
    
    if new_today_status == 'EmergencyShutdowns' and old_today_status != 'EmergencyShutdowns':
        changes.append("🚨 АВАРІЙНЕ ВІДКЛЮЧЕННЯ сьогодні!")
    elif old_today_status == 'EmergencyShutdowns' and new_today_status != 'EmergencyShutdowns':
        changes.append("✅ Аварійне відключення скасовано")
    
    # Check if tomorrow's schedule appeared
    old_tomorrow = old_queue.get('tomorrow', {})
    new_tomorrow = new_queue.get('tomorrow', {})
    
    old_status = old_tomorrow.get('status', '')
    new_status = new_tomorrow.get('status', '')
    
    # Check for emergency status on tomorrow
    if new_status == 'EmergencyShutdowns' and old_status != 'EmergencyShutdowns':
        changes.append("🚨 АВАРІЙНЕ ВІДКЛЮЧЕННЯ завтра!")
    elif old_status == 'EmergencyShutdowns' and new_status != 'EmergencyShutdowns':
        changes.append("✅ Аварійне відключення на завтра скасовано")
    
    # If tomorrow's schedule changed from WaitingForSchedule to having slots
    if old_status == 'WaitingForSchedule' and new_status != 'WaitingForSchedule':
        if 'slots' in new_tomorrow and new_status != 'EmergencyShutdowns':
            changes.append("З'явився графік на завтра!")
    
    # Check if today's slots changed (excluding date rollovers already handled above)
    if old_today_slots != new_today_slots:
        changes.append("Змінився графік на сьогодні")
    
    return len(changes) > 0, changes


async def notify_users_of_changes_for_city(application: Application, old_data: Dict[str, Any], new_data: Dict[str, Any], city_code: str) -> None:
    """
    Notify users about schedule changes for their selected queues in a specific city.
    """
    if not user_notifications:
        return
    
    for user_id, chat_id in user_notifications.items():
        # Check if user has this city selected
        user_city = user_city_preferences.get(user_id)
        if user_city != city_code:
            continue
        
        # Get user's preferred queue
        queue_name = user_queue_preferences.get(user_id)
        
        if not queue_name:
            continue
        
        # Check if schedule changed for this queue
        changed, changes = has_schedule_changed(old_data, new_data, queue_name)
        
        if changed:
            logger.info(f"📢 Queue {queue_name} changed for user {user_id}: {changes}")
            try:
                # Format the notification message
                city_name = CITIES[city_code]['name']
                message = f"🔔 *Оновлення для {city_name}, черга {queue_name}*\n\n"
                message += "\n".join(f"• {change}" for change in changes)
                message += "\n\n"
                
                # Add updated schedule
                formatted_schedule = format_schedule(new_data, queue_name, city_name)
                message += formatted_schedule
                
                # Send notification
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Sent notification to user {user_id} for {city_name}, queue {queue_name}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")


async def notify_users_of_changes(application: Application, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> None:
    """
    Notify users about schedule changes for their selected queues.
    LEGACY function - kept for backward compatibility.
    """
    if not user_notifications:
        return
    
    for user_id, chat_id in user_notifications.items():
        # Get user's preferred queue
        queue_name = user_queue_preferences.get(user_id)
        
        if not queue_name:
            continue
        
        # Check if schedule changed for this queue
        changed, changes = has_schedule_changed(old_data, new_data, queue_name)
        
        if changed:
            try:
                # Format the notification message
                message = f"🔔 *Оновлення для черги {queue_name}*\n\n"
                message += "\n".join(f"• {change}" for change in changes)
                message += "\n\n"
                
                # Add updated schedule
                formatted_schedule = format_schedule(new_data, queue_name)
                message += formatted_schedule
                
                # Send notification
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Sent notification to user {user_id} for queue {queue_name}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")


async def update_schedule(context) -> None:
    """
    Background task to update the schedule every 10 minutes for all cities.
    Also sends notifications to users if their queue schedule changed.
    """
    global schedule_data, last_update, last_fetch
    
    logger.info("Updating schedule for all cities...")
    
    # Get the application object (context can be Application or CallbackContext)
    application = context if isinstance(context, Application) else context.application
    
    from datetime import timezone, timedelta as td
    schedule_tz = timezone(td(hours=2))
    
    # Update schedule for each city
    for city_code in CITIES.keys():
        logger.info(f"Fetching schedule for {CITIES[city_code]['name']}...")
        data = await fetch_schedule(city_code)
        
        if data:
            # Record when we fetched the data
            last_fetch[city_code] = datetime.now(schedule_tz)
            
            # Check for changes and notify users
            if schedule_data[city_code] is not None:
                # Check if entire schedule changed
                if schedule_data[city_code] != data:
                    logger.info(f"🔔 Schedule changed for {CITIES[city_code]['name']}, checking user queues...")
                    # Only notify users who have this city selected
                    await notify_users_of_changes_for_city(application, schedule_data[city_code], data, city_code)
                else:
                    logger.info(f"✅ No schedule changes for {CITIES[city_code]['name']}")
            
            # Update schedule data (old becomes previous, new becomes current)
            schedule_data[city_code] = data
            
            # Extract the most recent updatedOn timestamp from all queues
            updated_timestamps = []
            for queue_name, queue_data in data.items():
                if isinstance(queue_data, dict) and 'updatedOn' in queue_data:
                    try:
                        updated_timestamps.append(datetime.fromisoformat(queue_data['updatedOn']))
                    except Exception as e:
                        logger.warning(f"Could not parse updatedOn for queue {queue_name} in {city_code}: {e}")
            
            # Set last_update to the most recent updatedOn timestamp
            if updated_timestamps:
                last_update_utc = max(updated_timestamps)
                # Convert from UTC (+00:00) to schedule timezone (+02:00)
                last_update[city_code] = last_update_utc.astimezone(schedule_tz)
                logger.info(f"Schedule for {CITIES[city_code]['name']} updated at {last_update[city_code]} (from API updatedOn)")
                logger.info(f"Data fetched at {last_fetch[city_code]}")
            else:
                last_update[city_code] = datetime.now(schedule_tz)
                logger.warning(f"No updatedOn timestamps found for {city_code}, using current time")
        else:
            logger.warning(f"Failed to update schedule for {city_code}")
    
    logger.info("Schedule update complete for all cities")
    # Don't save preferences here - only save when user preferences actually change


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def format_date_eastern(date_str: str) -> str:
    """Convert date from YYYY-MM-DD to DD.MM.YYYY format"""
    try:
        if date_str and len(date_str) >= 10:
            # Extract YYYY-MM-DD from the string
            date_part = date_str[:10]
            parts = date_part.split('-')
            if len(parts) == 3:
                return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return date_str[:10]
    except Exception:
        return date_str[:10] if date_str else ""


def format_schedule(data: Dict[str, Any], queue_filter: Optional[str] = None, city_name: Optional[str] = None) -> str:
    """
    Format the schedule data into a readable message.
    
    Args:
        data: Schedule data from API
        queue_filter: Optional queue name to filter (e.g., "1.1")
        city_name: Optional city name to display in the header
        
    Returns:
        Formatted string for display
    """
    if not data:
        return "📋 Немає доступних даних про графік відключень"
    
    message = "⚡️ *Графік планових відключень*\n"
    
    # Add city name if provided
    if city_name:
        message += f"🏙️ Місто: {city_name}\n"
    
    message += "\n"
    
    # Filter by queue if specified
    if queue_filter:
        if queue_filter not in data:
            return f"❌ Черга {queue_filter} не знайдена.\n\nДоступні черги: {', '.join(sorted(data.keys()))}"
        queue_names = [queue_filter]
        message += f"🔸 Фільтр: Черга {queue_filter}\n\n"
    else:
        queue_names = sorted(data.keys())
    
    # Process each queue group
    for queue_name in queue_names:
        queue_data = data[queue_name]
        
        if not isinstance(queue_data, dict):
            continue
            
        message += f"🔸 *Черга {queue_name}*\n"
        
        # Today's schedule
        if 'today' in queue_data:
            today = queue_data['today']
            today_date = format_date_eastern(today.get('date', ''))
            today_status = today.get('status', '')
            
            message += f"📅 Сьогодні ({today_date}):\n"
            
            # Calculate total outage minutes and power hours
            total_outage_minutes = 0
            
            # Check for emergency status
            if today_status == 'EmergencyShutdowns':
                message += "  🚨 *АВАРІЙНЕ ВІДКЛЮЧЕННЯ!*\n"
                # For emergency status, show slots if available
                if 'slots' in today:
                    for slot in today['slots']:
                        if slot.get('type') == 'Definite':
                            start_time = minutes_to_time(slot['start'])
                            end_time = minutes_to_time(slot['end'])
                            message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                            total_outage_minutes += slot['end'] - slot['start']
            else:
                # Normal status - show slots or "no outages"
                if 'slots' in today:
                    has_outages = False
                    for slot in today['slots']:
                        if slot.get('type') == 'Definite':
                            has_outages = True
                            start_time = minutes_to_time(slot['start'])
                            end_time = minutes_to_time(slot['end'])
                            message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                            total_outage_minutes += slot['end'] - slot['start']
                    
                    if not has_outages:
                        message += "  ✅ Відключень немає\n"
            
            # Calculate and display power availability hours (only if there are outages)
            if total_outage_minutes > 0:
                total_minutes_in_day = 24 * 60
                power_minutes = total_minutes_in_day - total_outage_minutes
                power_hours = power_minutes / 60
                message += f"  ⚡️ Електрика: {power_hours:.1f} год\n"
        
        # Tomorrow's schedule
        if 'tomorrow' in queue_data:
            tomorrow = queue_data['tomorrow']
            tomorrow_date = format_date_eastern(tomorrow.get('date', ''))
            message += f"📅 Завтра ({tomorrow_date}):\n"
            
            # Calculate total outage minutes and power hours
            total_outage_minutes = 0
            
            status = tomorrow.get('status', '')
            if status == 'WaitingForSchedule':
                message += "  ⏳ Очікується графік\n"
            elif status == 'EmergencyShutdowns':
                message += "  🚨 *АВАРІЙНЕ ВІДКЛЮЧЕННЯ!*\n"
                if 'slots' in tomorrow:
                    for slot in tomorrow['slots']:
                        if slot.get('type') == 'Definite':
                            start_time = minutes_to_time(slot['start'])
                            end_time = minutes_to_time(slot['end'])
                            message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                            total_outage_minutes += slot['end'] - slot['start']
            elif 'slots' in tomorrow:
                has_outages = False
                for slot in tomorrow['slots']:
                    if slot.get('type') == 'Definite':
                        has_outages = True
                        start_time = minutes_to_time(slot['start'])
                        end_time = minutes_to_time(slot['end'])
                        message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                        total_outage_minutes += slot['end'] - slot['start']
                
                if not has_outages:
                    message += "  ✅ Відключень немає\n"
            
            # Calculate and display power availability hours (only if there are outages and not waiting for schedule)
            if status != 'WaitingForSchedule' and total_outage_minutes > 0:
                total_minutes_in_day = 24 * 60
                power_minutes = total_minutes_in_day - total_outage_minutes
                power_hours = power_minutes / 60
                message += f"  ⚡️ Електрика: {power_hours:.1f} год\n"
        
        message += "\n"
    
    return message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    """
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    if not user_city:
        # User hasn't selected a city yet - prompt them to select
        welcome_message = (
            "👋 Вітаю! Я бот Yasno Zrozumilo.\n\n"
            "Я надаю інформацію про планові відключення електроенергії.\n\n"
            "🏙️ *Спочатку оберіть ваше місто:*"
        )
        
        # Create inline keyboard with city options
        keyboard = [
            [InlineKeyboardButton("🏙️ Дніпро", callback_data="city_dnipro")],
            [InlineKeyboardButton("🏙️ Київ", callback_data="city_kyiv")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # User has already selected a city
        city_name = CITIES[user_city]['name']
        welcome_message = (
            f"👋 Вітаю! Я бот Yasno Zrozumilo.\n\n"
            f"🏙️ Ваше місто: *{city_name}*\n\n"
            "Я надаю інформацію про планові відключення електроенергії.\n\n"
            "🔔 *Як використовувати сповіщення:*\n"
            "1. Натисніть кнопку щоб вибрати чергу\n"
            "2. Натисніть кнопку щоб включити сповіщення\n"
            "3. Ви будете отримувати оновлення кожні 10 хвилин!\n\n"
            "Ви можете змінити місто командою /city"
        )
        
        await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard(has_city=True), parse_mode='Markdown')


async def city_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /city command - show city selection keyboard.
    """
    user_id = update.effective_user.id
    current_city = user_city_preferences.get(user_id)
    
    # Create inline keyboard with city options
    keyboard = [
        [InlineKeyboardButton("🏙️ Дніпро", callback_data="city_dnipro")],
        [InlineKeyboardButton("🏙️ Київ", callback_data="city_kyiv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🏙️ *Виберіть ваше місто:*\n\n"
    if current_city:
        message += f"Поточне місто: *{CITIES[current_city]['name']}*\n\n"
    message += "Виберіть місто зі списку нижче."
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    """
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    help_message = (
        "ℹ️ *Допомога*\n\n"
        "*Команди:*\n"
        "/start - Початок роботи з ботом\n"
        "/city - Вибрати місто\n"
        "/schedule - Отримати актуальний графік відключень\n"
        "/queue - Вибрати свою чергу\n"
        "/myqueue - Показати графік вашої черги\n"
        "/notifications - Керувати сповіщеннями\n"
        "/status - Перевірити статус оновлення даних\n"
        "/help - Показати цю довідку\n\n"
        "*Сповіщення:*\n"
        "Коли ви вибрали місто, чергу та включили сповіщення, ви будете отримувати:\n"
        "• Оновлення коли змінюється графік вашої черги\n"
        "• Сповіщення коли з'являється графік на завтра\n"
        "Перевірка відбувається кожні 10 хвилин.\n\n"
        "*Про бота:*\n"
        "Бот автоматично оновлює дані кожні 10 хвилин.\n"
        "Можна використовувати в груповому чаті.\n"
        "Підтримуються міста: Дніпро, Київ."
    )
    await update.message.reply_text(help_message, reply_markup=get_main_keyboard(has_city=bool(user_city)), parse_mode='Markdown')


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /schedule command - display the current schedule.
    Can accept queue as argument: /schedule 5.1
    """
    global schedule_data, last_update
    
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    if not user_city:
        await update.message.reply_text(
            "❌ Спочатку виберіть місто командою /city",
            reply_markup=get_main_keyboard(has_city=False)
        )
        return
    
    city_data = schedule_data.get(user_city)
    
    if city_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд.",
            reply_markup=get_main_keyboard(has_city=True)
        )
        return
    
    # Check if queue number provided as argument
    queue_filter = None
    if context.args and len(context.args) > 0:
        queue_filter = context.args[0]
    
    city_name = CITIES[user_city]['name']
    formatted_schedule = format_schedule(city_data, queue_filter, city_name)
    
    city_last_update = last_update.get(user_city)
    if city_last_update:
        time_info = f"\n\n🕐 Оновлено: {city_last_update.strftime('%d.%m.%Y %H:%M')}"
        formatted_schedule += time_info
    
    await update.message.reply_text(formatted_schedule, reply_markup=get_main_keyboard(has_city=True), parse_mode='Markdown')


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /queue command - show queue selection keyboard.
    """
    global schedule_data
    
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    if not user_city:
        await update.message.reply_text(
            "❌ Спочатку виберіть місто командою /city",
            reply_markup=get_main_keyboard(has_city=False)
        )
        return
    
    city_data = schedule_data.get(user_city)
    
    if city_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд.",
            reply_markup=get_main_keyboard(has_city=True)
        )
        return
    
    # Create inline keyboard with all available queues
    keyboard = []
    queue_names = sorted(city_data.keys())
    
    # Create rows with 3 buttons each
    row = []
    for queue_name in queue_names:
        row.append(InlineKeyboardButton(queue_name, callback_data=f"queue_{queue_name}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    # Add remaining buttons
    if row:
        keyboard.append(row)
    
    # Add "Show All" button
    keyboard.append([InlineKeyboardButton("📋 Показати всі черги", callback_data="queue_all")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_queue = user_queue_preferences.get(user_id)
    city_name = CITIES[user_city]['name']
    
    # Get the appropriate outages link for the city
    outages_links = {
        'dnipro': 'https://static.yasno.ua/dnipro/outages',
        'kyiv': 'https://static.yasno.ua/kyiv/outages'
    }
    outages_link = outages_links.get(user_city, 'https://yasno.ua')
    
    message = f"🏙️ Місто: *{city_name}*\n\n"
    message += "🔸 *Виберіть свою чергу відключень:*\n\n"
    if current_queue:
        message += f"Поточна черга: *{current_queue}*\n\n"
    message += f"❓ Не знаєте свою чергу? Перевірте тут:\n{outages_link}\n\n"
    message += "Після вибору команда /myqueue буде показувати тільки вашу чергу."
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def myqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /myqueue command - show schedule for user's selected queue.
    """
    global schedule_data, last_update
    
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    if not user_city:
        await update.message.reply_text(
            "❌ Спочатку виберіть місто командою /city",
            reply_markup=get_main_keyboard(has_city=False)
        )
        return
    
    queue_filter = user_queue_preferences.get(user_id)
    
    if not queue_filter:
        await update.message.reply_text(
            "❌ Ви ще не вибрали чергу.\n\n"
            "Використовуйте /queue щоб вибрати свою чергу.",
            reply_markup=get_main_keyboard(has_city=True)
        )
        return
    
    city_data = schedule_data.get(user_city)
    
    if city_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд.",
            reply_markup=get_main_keyboard(has_city=True)
        )
        return
    
    city_name = CITIES[user_city]['name']
    formatted_schedule = format_schedule(city_data, queue_filter, city_name)
    
    city_last_update = last_update.get(user_city)
    if city_last_update:
        time_info = f"\n\n🕐 Оновлено: {city_last_update.strftime('%d.%m.%Y %H:%M')}"
        formatted_schedule += time_info
    
    await update.message.reply_text(formatted_schedule, reply_markup=get_main_keyboard(has_city=True), parse_mode='Markdown')


async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from city selection buttons.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data.startswith("city_"):
        # Set user city preference
        city_code = callback_data.replace("city_", "")
        
        if city_code in CITIES:
            user_city_preferences[user_id] = city_code
            await save_preferences()
            
            city_name = CITIES[city_code]['name']
            
            await query.edit_message_text(
                f"✅ Місто *{city_name}* збережено!\n\n"
                f"Тепер ви можете вибрати чергу командою /queue\n\n"
                "Ви можете змінити місто в будь-який час командою /city",
                parse_mode='Markdown'
            )
            
            # Send the main keyboard
            await query.message.reply_text(
                "Виберіть дію з меню нижче:",
                reply_markup=get_main_keyboard(has_city=True)
            )


async def queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from queue selection buttons.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    callback_data = query.data
    
    if callback_data == "queue_all":
        # Clear user preference
        user_queue_preferences[user_id] = None
        await save_preferences()
        await query.edit_message_text(
            "✅ Налаштування скинуто!\n\n"
            "Тепер /myqueue буде показувати всі черги.\n"
            "Використовуйте /schedule для перегляду графіка."
        )
    elif callback_data.startswith("queue_"):
        # Set user preference
        queue_name = callback_data.replace("queue_", "")
        user_queue_preferences[user_id] = queue_name
        
        # Enable notifications for this user
        chat_id = update.effective_chat.id
        user_notifications[user_id] = chat_id
        await save_preferences()
        
        city_name = CITIES[user_city]['name'] if user_city else "вашого міста"
        
        await query.edit_message_text(
            f"✅ Черга *{queue_name}* збережена!\n\n"
            f"🏙️ Місто: {city_name}\n"
            f"Тепер команда /myqueue буде показувати тільки чергу {queue_name}.\n"
            f"🔔 Ви будете отримувати оновлення для цієї черги кожні 10 хвилин.\n\n"
            "Використовуйте:\n"
            f"• /myqueue - ваша черга ({queue_name})\n"
            "• /schedule - всі черги\n"
            f"• /schedule {queue_name} - конкретна черга\n"
            "• /notifications - керувати сповіщеннями\n"
            "• /city - змінити місто",
            parse_mode='Markdown'
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /status command - show update status.
    """
    global schedule_data, last_fetch
    
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    if not user_city:
        await update.message.reply_text(
            "❌ Спочатку виберіть місто командою /city",
            reply_markup=get_main_keyboard(has_city=False)
        )
        return
    
    city_last_fetch = last_fetch.get(user_city)
    city_data = schedule_data.get(user_city)
    city_name = CITIES[user_city]['name']
    
    if city_last_fetch is None:
        status_message = f"⏳ Дані для {city_name} ще не завантажені"
    else:
        # Make last_fetch timezone-aware if it's not already
        if city_last_fetch.tzinfo is None:
            from datetime import timezone
            last_fetch_aware = city_last_fetch.replace(tzinfo=timezone.utc)
        else:
            last_fetch_aware = city_last_fetch
        
        # Calculate next update time
        next_update = last_fetch_aware + timedelta(seconds=UPDATE_INTERVAL)
        
        # Format times
        last_fetch_str = last_fetch_aware.strftime('%d.%m.%Y %H:%M')
        next_update_str = next_update.strftime('%d.%m.%Y %H:%M')
        
        status_message = (
            f"✅ *Статус системи*\n\n"
            f"🏙️ Місто: {city_name}\n"
            f"Останнє оновлення: {last_fetch_str}\n"
            f"Наступне оновлення: {next_update_str}\n"
            f"Дані: {'✅ Доступні' if city_data else '❌ Недоступні'}"
        )
    
    await update.message.reply_text(status_message, reply_markup=get_main_keyboard(has_city=True), parse_mode='Markdown')


async def command_buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle command button callbacks from /start menu.
    """
    query = update.callback_query
    callback_data = query.data
    
    await query.answer()
    
    # Route to appropriate command handler
    if callback_data == "cmd_schedule":
        await schedule_callback(update, context)
    elif callback_data == "cmd_myqueue":
        await myqueue_callback(update, context)
    elif callback_data == "cmd_queue":
        await queue_callback_button(update, context)
    elif callback_data == "cmd_notifications":
        await notifications_callback_button(update, context)
    elif callback_data == "cmd_status":
        await status_callback(update, context)
    elif callback_data == "cmd_help":
        await help_callback(update, context)


async def schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle schedule button from command buttons."""
    query = update.callback_query
    message = format_schedule(schedule_data, None)
    await query.edit_message_text(message)


async def myqueue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle my queue button from command buttons."""
    query = update.callback_query
    user_id = update.effective_user.id
    queue_name = user_queue_preferences.get(user_id)
    
    if queue_name:
        message = format_schedule(schedule_data, queue_name)
    else:
        message = "❌ Ви ще не вибрали чергу\n\nВиберіть чергу з /queue"
    
    await query.edit_message_text(message)


async def queue_callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle queue selection button from command buttons."""
    query = update.callback_query
    
    keyboard = [[InlineKeyboardButton(f"{i}", callback_data=f"queue_{i}") for i in [f"{k}.{j}" for k in range(1, 7) for j in [1, 2]]]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🔸 *Вибір черги*\n\nВиберіть вашу чергу (1.1 - 6.2):"
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def notifications_callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle notifications button from command buttons."""
    query = update.callback_query
    user_id = update.effective_user.id
    queue_name = user_queue_preferences.get(user_id)
    is_enabled = user_id in user_notifications
    
    keyboard = []
    
    if is_enabled:
        keyboard.append([InlineKeyboardButton("🔔 Вимкнути сповіщення", callback_data="notif_off")])
        status = f"✅ Сповіщення включені для черги *{queue_name}*"
    else:
        keyboard.append([InlineKeyboardButton("🔔 Включити сповіщення", callback_data="notif_on")])
        if queue_name:
            status = f"❌ Сповіщення вимкнені для черги *{queue_name}*"
        else:
            status = "❌ Сповіщення вимкнені\n\nВиберіть чергу з /queue щоб включити сповіщення"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "🔔 *Керування сповіщеннями*\n\n"
        f"{status}\n\n"
        "Ви будете отримувати повідомлення коли:\n"
        "• Графік для вашої черги оновлюється\n"
        "• З'являється графік на завтра\n\n"
        "Оновлення перевіряються кожні 10 хвилин."
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status button from command buttons."""
    query = update.callback_query
    
    message = (
        "📊 *Статус бота*\n\n"
        f"⏰ Останнє оновлення: {last_update}\n"
        f"📡 Статус: ✅ Активний\n"
        f"🔄 Оновлення: Кожні 10 хвилин\n"
        f"📚 Кількість черг: 12 (1.1 - 6.2)"
    )
    await query.edit_message_text(message, parse_mode='Markdown')


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button from command buttons."""
    query = update.callback_query
    
    help_message = (
        "ℹ️ *Довідка*\n\n"
        "*Команди:*\n"
        "/start - Головне меню\n"
        "/schedule - Подивитися повний графік\n"
        "/queue - Вибрати чергу\n"
        "/myqueue - Ваша черга\n"
        "/notifications - Управління сповіщеннями\n"
        "/status - Статус бота\n"
        "/help - Ця довідка\n\n"
        "*Про бота:*\n"
        "🤖 Yasno Bot - бот для перегляду графіків перерв\n"
        "📡 Графік оновлюється автоматично кожні 10 хвилин\n"
        "🔔 Ви можете отримувати сповіщення про зміни графіка"
    )
    await query.edit_message_text(help_message, parse_mode='Markdown')


async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /notifications command - manage notification settings.
    """
    user_id = update.effective_user.id
    queue_name = user_queue_preferences.get(user_id)
    is_enabled = user_id in user_notifications
    
    keyboard = []
    
    if is_enabled:
        keyboard.append([InlineKeyboardButton("🔔 Вимкнути сповіщення", callback_data="notif_off")])
        status = f"✅ Сповіщення включені для черги *{queue_name}*"
    else:
        keyboard.append([InlineKeyboardButton("🔔 Включити сповіщення", callback_data="notif_on")])
        if queue_name:
            status = f"❌ Сповіщення вимкнені для черги *{queue_name}*"
        else:
            status = "❌ Сповіщення вимкнені\n\nВиберіть чергу з /queue щоб включити сповіщення"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "🔔 *Керування сповіщеннями*\n\n"
        f"{status}\n\n"
        "Ви будете отримувати повідомлення коли:\n"
        "• Графік для вашої черги оновлюється\n"
        "• З'являється графік на завтра\n\n"
        "Оновлення перевіряються кожні 10 хвилин."
    )
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle notification toggle callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "notif_on":
        queue_name = user_queue_preferences.get(user_id)
        if not queue_name:
            await query.edit_message_text(
                "❌ Спочатку виберіть чергу з /queue"
            )
            return
        
        chat_id = update.effective_chat.id
        user_notifications[user_id] = chat_id
        await save_preferences()
        
        await query.edit_message_text(
            f"✅ Сповіщення включені для черги *{queue_name}*\n\n"
            "Ви будете отримувати оновлення кожні 10 хвилин.",
            parse_mode='Markdown'
        )
        logger.info(f"Notifications enabled for user {user_id}, queue {queue_name}")
        
    elif callback_data == "notif_off":
        if user_id in user_notifications:
            queue_name = user_queue_preferences.get(user_id, "невідома")
            del user_notifications[user_id]
            await save_preferences()
            
            await query.edit_message_text(
                f"❌ Сповіщення вимкнені для черги *{queue_name}*\n\n"
                "Ви не будете отримувати оновлення, але /myqueue працюватиме як раніше.",
                parse_mode='Markdown'
            )
            logger.info(f"Notifications disabled for user {user_id}")


async def post_init(application: Application) -> None:
    """
    Initialize the bot - fetch initial data and schedule periodic updates.
    """
    try:
        global schedule_data, last_fetch
        
        logger.info("🚀 Starting post_init - loading preferences and scheduling updates...")
        
        # Load saved user preferences
        await load_preferences()
        
        # Try to load cached schedule (with updatedOn timestamps)
        cached_schedule = load_schedule_cache()
        if cached_schedule:
            # For backward compatibility, cache might be old format (dict) or new format
            # Set for dnipro by default if old format
            if isinstance(cached_schedule, dict) and 'dnipro' not in cached_schedule:
                schedule_data['dnipro'] = cached_schedule
            else:
                schedule_data = cached_schedule
            logger.info("Using cached schedule data")
        
        # Don't fetch in post_init for webhook mode - it will be done after start
        # Only fetch for polling mode
        if not os.getenv('WEBHOOK_URL'):
            logger.info("Polling mode: fetching initial schedule in post_init")
            await update_schedule(application)
        
        # Calculate when next update should happen
        # Check all cities' last fetch times and use the oldest one
        from datetime import timezone as tz
        now = datetime.now(tz.utc)
        
        oldest_fetch_time = None
        for city_code in CITIES.keys():
            city_last_fetch = last_fetch.get(city_code)
            if city_last_fetch:
                if city_last_fetch.tzinfo is None:
                    city_last_fetch = city_last_fetch.replace(tzinfo=tz.utc)
                else:
                    city_last_fetch = city_last_fetch.astimezone(tz.utc)
                
                if oldest_fetch_time is None or city_last_fetch < oldest_fetch_time:
                    oldest_fetch_time = city_last_fetch
        
        if oldest_fetch_time:
            time_since_fetch = (now - oldest_fetch_time).total_seconds()
            
            if time_since_fetch >= UPDATE_INTERVAL:
                # Last fetch was too long ago, schedule next update immediately
                first_run = 10  # Run in 10 seconds
                logger.info("Last fetch was old, scheduling immediate update")
            else:
                # Schedule next update at the proper interval
                first_run = UPDATE_INTERVAL - time_since_fetch
                logger.info(f"Scheduling next update in {int(first_run/60)} minutes")
        else:
            # No last fetch, schedule for UPDATE_INTERVAL from now
            first_run = UPDATE_INTERVAL
            logger.info("No previous fetch found, scheduling update in 10 minutes")
        
        # Schedule periodic updates every 10 minutes
        job_queue = application.job_queue
        job_queue.run_repeating(
            update_schedule,
            interval=UPDATE_INTERVAL,
            first=first_run
        )
        
        logger.info("✅ post_init complete: Scheduled periodic updates every 10 minutes")
    except Exception as e:
        logger.error(f"❌ FATAL ERROR in post_init: {e}", exc_info=True)
        raise


async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle custom keyboard button presses from the reply keyboard.
    Works in both private and group chats.
    """
    text = update.message.text
    user_id = update.effective_user.id
    user_city = user_city_preferences.get(user_id)
    
    # Map button text to command handlers
    button_handlers = {
        "📋 Графік": schedule_command,
        "🔸 Моя черга": myqueue_command,
        "🏙️ Місто": city_command,
        "🏙️ Вибрати місто": city_command,
        "⚙️ Вибрати чергу": queue_command,
        "🔔 Сповіщення": notifications_command,
        "📊 Статус": status_command,
        "ℹ️ Довідка": help_command,
    }
    
    # Get the handler for this button text
    handler = button_handlers.get(text)
    if handler:
        # Check if user needs to select city first (except for city and help commands)
        if not user_city and handler not in [city_command, help_command]:
            await update.message.reply_text(
                "❌ Спочатку виберіть місто командою /city",
                reply_markup=get_main_keyboard(has_city=False)
            )
            return
        
        await handler(update, context)


def main() -> None:
    """
    Start the bot.
    """
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    # Create application
    application = Application.builder().token(token).post_init(post_init).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("city", city_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("myqueue", myqueue_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    
    # Register callback query handlers for inline buttons
    application.add_handler(CallbackQueryHandler(command_buttons_callback, pattern="^cmd_"))
    application.add_handler(CallbackQueryHandler(city_callback, pattern="^city_"))
    application.add_handler(CallbackQueryHandler(notifications_callback, pattern="^notif_"))
    application.add_handler(CallbackQueryHandler(queue_callback))
    
    # Register message handler for custom keyboard buttons
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    
    # Start health check server (always, for Koyeb health checks)
    async def start_health_server():
        async def health_check(request):
            return web.Response(text='OK', status=200)
        
        # Webhook handler for Telegram
        async def telegram_webhook(request):
            """Handle incoming webhook requests from Telegram"""
            try:
                update_dict = await request.json()
                update = Update.de_json(update_dict, application.bot)
                await application.process_update(update)
                return web.Response(text='OK', status=200)
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return web.Response(text='Error', status=500)
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)
        app.router.add_post('/webhook', telegram_webhook)  # Telegram webhook endpoint
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Use PORT environment variable from Koyeb, fallback to 8000 for local
        port = int(os.getenv('PORT', 8000))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"Health check server started on port {port}")
        
        # Set up webhook if running on Koyeb
        webhook_url = os.getenv('WEBHOOK_URL')
        if webhook_url:
            try:
                # Remove trailing slash from webhook_url to avoid double slashes
                webhook_url = webhook_url.rstrip('/')
                await application.bot.set_webhook(url=f"{webhook_url}/webhook")
                logger.info(f"Webhook set to: {webhook_url}/webhook")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
        
        return runner
    
    # Use webhook mode on Koyeb, polling locally
    if os.getenv('WEBHOOK_URL'):
        logger.info("Running in webhook mode (Koyeb)")
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Store runner for cleanup
        runner = None
        
        async def run_webhook():
            nonlocal runner
            try:
                # Start health server
                runner = await start_health_server()
                
                # Initialize and start application
                await application.initialize()
                await application.start()
                
                logger.info("Bot started in webhook mode")
                
                # Manually call post_init since it doesn't run automatically in custom webhook mode
                logger.info("Manually calling post_init for webhook mode...")
                await post_init(application)
                
                # Trigger initial schedule fetch immediately after bot starts
                logger.info("Triggering initial schedule fetch...")
                await update_schedule(application)
                
                # Run forever
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("Received shutdown signal")
            finally:
                logger.info("Shutting down gracefully...")
                
                # Stop the application first
                try:
                    await application.stop()
                    logger.info("Application stopped")
                except Exception as e:
                    logger.error(f"Error stopping application: {e}")
                
                # Clean up runner
                if runner:
                    try:
                        await runner.cleanup()
                        logger.info("Web runner cleaned up")
                    except Exception as e:
                        logger.error(f"Error cleaning up runner: {e}")
                
                # Shutdown the application
                try:
                    await application.shutdown()
                    logger.info("Application shutdown complete")
                except Exception as e:
                    logger.error(f"Error shutting down application: {e}")
        
        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            # Cancel all tasks
            for task in asyncio.all_tasks(loop):
                task.cancel()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            loop.run_until_complete(run_webhook())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            # Cancel all remaining tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for all tasks to complete cancellation
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Close the loop
            loop.close()
            logger.info("Event loop closed")
    else:
        logger.info("Running in polling mode")
        
        # For polling mode, start health server in a separate thread
        import threading
        health_server_started = threading.Event()
        
        def run_health_server():
            """Run health server in separate thread with its own event loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def start_server():
                runner = await start_health_server()
                health_server_started.set()
                logger.info("Health server started for polling mode")
                # Keep server running
                await asyncio.Event().wait()
            
            try:
                loop.run_until_complete(start_server())
            except KeyboardInterrupt:
                pass
            finally:
                loop.close()
        
        # Start health server in background thread
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        # Wait for health server to start
        health_server_started.wait(timeout=5)
        
        # Run polling (uses its own event loop)
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
