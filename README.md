# Yasno Zrozumilo Telegram Bot

Telegram бот для отримання інформації про планові відключення електроенергії з API Yasno.

## Можливості

- 🔄 Автоматичне оновлення графіка кожні 30 хвилин
- 📋 Показ актуального графіка відключень за командою
- 🎯 **Фільтрація по черзі** - виберіть свою чергу (наприклад, 5.1) та бачте тільки її
- 💾 Збереження налаштувань черги для кожного користувача
- 💬 Робота в особистих повідомленнях та групових чатах
- 🕐 Перевірка статусу оновлення даних

## Встановлення

1. **Клонуйте репозиторій або створіть директорію:**
```bash
cd yasno-zrozumilo
```

2. **Створіть віртуальне середовище Python:**
```bash
python3 -m venv venv
source venv/bin/activate  # На macOS/Linux
# або
venv\Scripts\activate  # На Windows
```

3. **Встановіть залежності:**
```bash
pip install -r requirements.txt
```

4. **Налаштуйте бота:**
   - Створіть бота через [@BotFather](https://t.me/BotFather) в Telegram
   - Отримайте токен бота
   - Скопіюйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
   - Відредагуйте `.env` та вставте ваш токен:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   ```

## Запуск

```bash
python bot.py
```

Бот почне працювати і буде доступний в Telegram.

## Команди бота

- `/start` - Початок роботи з ботом
- `/schedule` - Показати актуальний графік відключень (всі черги)
- `/schedule 5.1` - Показати графік для конкретної черги
- `/queue` - Вибрати свою чергу (зберігається для користувача)
- `/myqueue` - Показати графік тільки для вашої черги
- `/status` - Перевірити статус оновлення даних
- `/help` - Показати довідку

### Приклад використання фільтрації

1. Виберіть свою чергу один раз: `/queue` → натисніть кнопку "5.1"
2. Тепер завжди використовуйте: `/myqueue` - побачите тільки вашу чергу!
3. Або перевірте іншу чергу: `/schedule 3.2`

## Використання в групових чатах

Бот підтримує роботу в групових чатах. Просто додайте його до групи і використовуйте команди як зазвичай.

## Структура проєкту

```
yasno-zrozumilo/
├── bot.py              # Головний файл бота
├── requirements.txt    # Залежності Python
├── .env.example       # Шаблон файлу з налаштуваннями
├── .gitignore         # Файли для ігнорування в Git
└── README.md          # Цей файл
```

## API

Бот використовує публічний API Yasno для отримання даних про планові відключення:
```
https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages
```

## Технології

- **python-telegram-bot** (v20.7) - Бібліотека для роботи з Telegram Bot API
- **requests** (v2.31.0) - HTTP-запити до API
- **python-dotenv** (v1.0.0) - Завантаження змінних середовища

## 🚀 Deployment (Free)

### Deploy to Koyeb (Recommended)

**100% FREE - No credit card required!**

See detailed guide: [KOYEB_DEPLOY.md](KOYEB_DEPLOY.md)

Quick start:

1. Push code to GitHub
2. Go to [app.koyeb.com](https://app.koyeb.com)
3. Create service from GitHub
4. Add `TELEGRAM_BOT_TOKEN` environment variable
5. Deploy! 🎉

Your bot will run 24/7 for free with auto-restarts and monitoring.

### 💾 Persistent Storage (Important!)

Koyeb free tier has ephemeral storage - user preferences reset on redeploy.

**Solution**: Use GitHub Gist (100% free) for persistent storage.

#### Setup Steps:

1. **Create GitHub Personal Access Token:**
   - Go to https://github.com/settings/tokens
   - Click **"Generate new token (classic)"**
   - Name: `Yasno Bot Storage`
   - Scope: Check only `gist`
   - Click **"Generate token"** and copy it

2. **Create a GitHub Gist:**
   - Go to https://gist.github.com
   - Click **"+ New gist"**
   - Filename: `user_preferences.json`
   - Content: `{}`
   - Create as **Secret gist**
   - Copy the Gist ID from URL: `https://gist.github.com/USERNAME/abc123...` (the last part)

3. **Add to Koyeb Environment Variables:**
   ```
   GITHUB_TOKEN=ghp_your_token_here
   GIST_ID=your_gist_id_here
   ```

Now user preferences persist across redeploys! ✅

## Розробка

Для розробки рекомендується:

1. Використовувати віртуальне середовище Python
2. Встановити всі залежності з `requirements.txt`
3. Не додавати файл `.env` до Git (він вже в `.gitignore`)

## Ліцензія

MIT

## Автор

Created for tracking Yasno power outage schedules in Ukraine 🇺🇦
