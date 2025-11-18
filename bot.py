#!/usr/bin/env python3
"""
Yasno Zrozumilo Telegram Bot
Fetches planned power outage schedules from Yasno API and displays them to users.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages"
UPDATE_INTERVAL = 1800  # 30 minutes in seconds

# Global storage for schedule data
schedule_data: Optional[Dict[str, Any]] = None
last_update: Optional[datetime] = None

# User preferences for queue filtering (user_id -> queue_name)
user_queue_preferences: Dict[int, Optional[str]] = {}

# User notification preferences (user_id -> chat_id)
# Stores chat IDs of users who want automatic notifications
user_notifications: Dict[int, int] = {}

# Previous schedule state for change detection
previous_schedule_data: Optional[Dict[str, Any]] = None


async def fetch_schedule() -> Optional[Dict[str, Any]]:
    """
    Fetch the power outage schedule from Yasno API.
    
    Returns:
        Dictionary with schedule data or None if request fails
    """
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info("Successfully fetched schedule from API")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching schedule: {e}")
        return None


def has_schedule_changed(old_data: Dict[str, Any], new_data: Dict[str, Any], queue_name: str) -> tuple[bool, list[str]]:
    """
    Check if schedule changed for a specific queue.
    
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
    
    # Check if updatedOn changed
    old_updated = old_queue.get('updatedOn', '')
    new_updated = new_queue.get('updatedOn', '')
    
    if old_updated != new_updated:
        changes.append(f"Графік оновлено: {new_updated[:16]}")
    
    # Check if tomorrow's schedule appeared
    old_tomorrow = old_queue.get('tomorrow', {})
    new_tomorrow = new_queue.get('tomorrow', {})
    
    old_status = old_tomorrow.get('status', '')
    new_status = new_tomorrow.get('status', '')
    
    # If tomorrow's schedule changed from WaitingForSchedule to having slots
    if old_status == 'WaitingForSchedule' and new_status != 'WaitingForSchedule':
        if 'slots' in new_tomorrow:
            changes.append("З'явився графік на завтра!")
    
    # Check if today's slots changed
    old_today_slots = old_queue.get('today', {}).get('slots', [])
    new_today_slots = new_queue.get('today', {}).get('slots', [])
    
    if old_today_slots != new_today_slots:
        changes.append("Змінився графік на сьогодні")
    
    return len(changes) > 0, changes


async def notify_users_of_changes(application: Application, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> None:
    """
    Notify users about schedule changes for their selected queues.
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


async def update_schedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Background task to update the schedule every 30 minutes.
    Also sends notifications to users if their queue schedule changed.
    """
    global schedule_data, last_update, previous_schedule_data
    
    logger.info("Updating schedule...")
    data = await fetch_schedule()
    
    if data:
        # Check for changes and notify users
        if schedule_data is not None and previous_schedule_data != data:
            await notify_users_of_changes(context.application, previous_schedule_data, data)
        
        previous_schedule_data = schedule_data  # Store previous state
        schedule_data = data
        last_update = datetime.now()
        logger.info(f"Schedule updated at {last_update}")
    else:
        logger.warning("Failed to update schedule")


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def format_schedule(data: Dict[str, Any], queue_filter: Optional[str] = None) -> str:
    """
    Format the schedule data into a readable message.
    
    Args:
        data: Schedule data from API
        queue_filter: Optional queue name to filter (e.g., "1.1")
        
    Returns:
        Formatted string for display
    """
    if not data:
        return "📋 Немає доступних даних про графік відключень"
    
    message = "⚡️ *Графік планових відключень*\n\n"
    
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
            message += f"📅 Сьогодні ({today.get('date', '')[:10]}):\n"
            
            if 'slots' in today:
                has_outages = False
                for slot in today['slots']:
                    if slot.get('type') == 'Definite':
                        has_outages = True
                        start_time = minutes_to_time(slot['start'])
                        end_time = minutes_to_time(slot['end'])
                        message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                
                if not has_outages:
                    message += "  ✅ Відключень немає\n"
        
        # Tomorrow's schedule
        if 'tomorrow' in queue_data:
            tomorrow = queue_data['tomorrow']
            message += f"📅 Завтра ({tomorrow.get('date', '')[:10]}):\n"
            
            status = tomorrow.get('status', '')
            if status == 'WaitingForSchedule':
                message += "  ⏳ Очікується графік\n"
            elif 'slots' in tomorrow:
                has_outages = False
                for slot in tomorrow['slots']:
                    if slot.get('type') == 'Definite':
                        has_outages = True
                        start_time = minutes_to_time(slot['start'])
                        end_time = minutes_to_time(slot['end'])
                        message += f"  🔴 {start_time} - {end_time} (відключення)\n"
                
                if not has_outages:
                    message += "  ✅ Відключень немає\n"
        
        message += "\n"
    
    return message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    """
    welcome_message = (
        "👋 Вітаю! Я бот Yasno Zrozumilo.\n\n"
        "Я надаю інформацію про планові відключення електроенергії.\n\n"
        "Доступні команди:\n"
        "/schedule - Показати актуальний графік відключень\n"
        "/queue - Вибрати свою чергу для фільтрації\n"
        "/myqueue - Показати графік тільки для вашої черги\n"
        "/notifications - Керувати сповіщеннями про оновлення\n"
        "/status - Статус оновлення даних\n"
        "/help - Допомога\n\n"
        "🔔 *Як використовувати сповіщення:*\n"
        "1. Виконайте /queue та виберіть вашу чергу\n"
        "2. Виконайте /notifications та включіть сповіщення\n"
        "3. Ви будете отримувати оновлення кожні 30 хвилин!\n\n"
        "Я працюю як в особистих повідомленнях, так і в групових чатах!"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    """
    help_message = (
        "ℹ️ *Допомога*\n\n"
        "*Команди:*\n"
        "/start - Початок роботи з ботом\n"
        "/schedule - Отримати актуальний графік відключень\n"
        "/queue - Вибрати свою чергу\n"
        "/myqueue - Показати графік вашої черги\n"
        "/notifications - Керувати сповіщеннями\n"
        "/status - Перевірити статус оновлення даних\n"
        "/help - Показати цю довідку\n\n"
        "*Сповіщення:*\n"
        "Коли ви вибрали чергу та включили сповіщення, ви будете отримувати:\n"
        "• Оновлення коли змінюється графік вашої черги\n"
        "• Сповіщення коли з'являється графік на завтра\n"
        "Перевірка відбувається кожні 30 хвилин.\n\n"
        "*Про бота:*\n"
        "Бот автоматично оновлює дані кожні 30 хвилин.\n"
        "Можна використовувати в груповому чаті."
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /schedule command - display the current schedule.
    Can accept queue as argument: /schedule 5.1
    """
    global schedule_data, last_update
    
    if schedule_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд."
        )
        return
    
    # Check if queue number provided as argument
    queue_filter = None
    if context.args and len(context.args) > 0:
        queue_filter = context.args[0]
    
    formatted_schedule = format_schedule(schedule_data, queue_filter)
    
    if last_update:
        time_info = f"\n\n🕐 Оновлено: {last_update.strftime('%d.%m.%Y %H:%M')}"
        formatted_schedule += time_info
    
    await update.message.reply_text(formatted_schedule, parse_mode='Markdown')


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /queue command - show queue selection keyboard.
    """
    global schedule_data
    
    if schedule_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд."
        )
        return
    
    # Create inline keyboard with all available queues
    keyboard = []
    queue_names = sorted(schedule_data.keys())
    
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
    
    user_id = update.effective_user.id
    current_queue = user_queue_preferences.get(user_id)
    
    message = "🔸 *Виберіть свою чергу відключень:*\n\n"
    if current_queue:
        message += f"Поточна черга: *{current_queue}*\n\n"
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
    queue_filter = user_queue_preferences.get(user_id)
    
    if not queue_filter:
        await update.message.reply_text(
            "❌ Ви ще не вибрали чергу.\n\n"
            "Використовуйте /queue щоб вибрати свою чергу."
        )
        return
    
    if schedule_data is None:
        await update.message.reply_text(
            "⏳ Завантажую дані... Спробуйте ще раз через кілька секунд."
        )
        return
    
    formatted_schedule = format_schedule(schedule_data, queue_filter)
    
    if last_update:
        time_info = f"\n\n🕐 Оновлено: {last_update.strftime('%d.%m.%Y %H:%M')}"
        formatted_schedule += time_info
    
    await update.message.reply_text(formatted_schedule, parse_mode='Markdown')


async def queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from queue selection buttons.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "queue_all":
        # Clear user preference
        user_queue_preferences[user_id] = None
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
        
        await query.edit_message_text(
            f"✅ Черга *{queue_name}* збережена!\n\n"
            f"Тепер команда /myqueue буде показувати тільки чергу {queue_name}.\n"
            f"🔔 Ви будете отримувати оновлення для цієї черги кожні 30 хвилин.\n\n"
            "Використовуйте:\n"
            f"• /myqueue - ваша черга ({queue_name})\n"
            "• /schedule - всі черги\n"
            f"• /schedule {queue_name} - конкретна черга\n"
            "• /notifications - керувати сповіщеннями",
            parse_mode='Markdown'
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /status command - show update status.
    """
    global schedule_data, last_update
    
    if last_update is None:
        status_message = "⏳ Дані ще не завантажені"
    else:
        time_since_update = datetime.now() - last_update
        minutes_ago = int(time_since_update.total_seconds() / 60)
        
        next_update = last_update + timedelta(seconds=UPDATE_INTERVAL)
        time_until_next = next_update - datetime.now()
        minutes_until = int(time_until_next.total_seconds() / 60)
        
        status_message = (
            f"✅ *Статус системи*\n\n"
            f"Останнє оновлення: {minutes_ago} хв тому\n"
            f"Наступне оновлення: через {minutes_until} хв\n"
            f"Дані: {'✅ Доступні' if schedule_data else '❌ Недоступні'}"
        )
    
    await update.message.reply_text(status_message, parse_mode='Markdown')


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
        "Оновлення перевіряються кожні 30 хвилин."
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
        
        await query.edit_message_text(
            f"✅ Сповіщення включені для черги *{queue_name}*\n\n"
            "Ви будете отримувати оновлення кожні 30 хвилин.",
            parse_mode='Markdown'
        )
        logger.info(f"Notifications enabled for user {user_id}, queue {queue_name}")
        
    elif callback_data == "notif_off":
        if user_id in user_notifications:
            queue_name = user_queue_preferences.get(user_id, "невідома")
            del user_notifications[user_id]
            
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
    # Fetch initial schedule
    await update_schedule(application)
    
    # Schedule periodic updates every 30 minutes
    job_queue = application.job_queue
    job_queue.run_repeating(
        update_schedule,
        interval=UPDATE_INTERVAL,
        first=UPDATE_INTERVAL
    )
    logger.info("Scheduled periodic updates every 30 minutes")


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
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("myqueue", myqueue_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    
    # Register callback query handlers for inline buttons
    application.add_handler(CallbackQueryHandler(notifications_callback, pattern="^notif_"))
    application.add_handler(CallbackQueryHandler(queue_callback))
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
