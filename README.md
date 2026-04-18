# Temka Bot

Простой и мощный Telegram бот на Python для создания интеллектуальных чатботов.

## 🚀 Быстрый старт

### ⚡ Самый быстрый способ (одна команда)

```bash
curl -fsSL https://raw.githubusercontent.com/hakkkaido/Temka_bot/main/install.sh -o /tmp/install.sh && sudo bash /tmp/install.sh
```

Эта команда скачает и запустит установщик, который:
- Установит все необходимые зависимости (Python, Git и т.д.)
- Клонирует проект (или установит из текущей директории)
- Создаст виртуальное окружение Python
- Запросит необходимые API ключи
- Опционально создаст systemd сервис для автозапуска

### Требования
- Linux или macOS (для Windows используйте WSL2)
- Интернет-соединение
- Права администратора (sudo)

### Способ 2: Автоматическая установка (из текущей директории)

```bash
sudo bash install.sh
```

Если вы уже скачали проект, просто перейдите в его директорию и запустите установщик.

### Способ 3: Ручная установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/hakkkaido/Temka_bot.git
   cd Temka_bot
   ```

2. **Создайте виртуальное окружение:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Создайте файл `.env`:**
   ```bash
   cp .env.example .env
   ```
   
   Отредактируйте `.env` и добавьте **обязательные** параметры:
   ```env
   TELEGRAM_TOKEN=123456789:ABCDefGHIJKLmnoPQRstUVwxyz
   TELEGRAM_CHAT_ID=987654321
   ```

5. **Запустите бота:**
   ```bash
   python main.py
   ```

## 📝 Конфигурация

### 1️⃣ Получение Telegram токена

1. Откройте Telegram и найдите бота **@BotFather**
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и получите токен
4. Добавьте токен в файл `.env`:
   ```env
   TELEGRAM_TOKEN=123456789:ABCDefGHIJKLmnoPQRstUVwxyz
   ```

### 2️⃣ Получение вашего Chat ID (КРИТИЧНО для безопасности)

⚠️ **Это важно!** Chat ID нужен для того, чтобы **только вы** могли использовать бота.

1. Откройте Telegram и найдите бота **@userinfobot**
2. Отправьте ему любое сообщение
3. Бот отправит вам ваш ID (это число вроде `987654321`)
4. Добавьте это число в файл `.env`:
   ```env
   TELEGRAM_CHAT_ID=987654321
   ```

**Без этого параметра бот работать не будет!**

### 3️⃣ Groq API Key (опционально, для голосовых сообщений)

1. Откройте https://console.groq.com/keys
2. Создайте бесплатный API ключ
3. Добавьте в файл `.env`:
   ```env
   GROQ_API_KEY=gsk_your_key_here
   ```

### 4️⃣ Google Gemini API Key (опционально, для AI интеграции и генерации изображений)

1. Откройте https://ai.google.dev/
2. Создайте API ключ
3. Добавьте в файл `.env`:
   ```env
   GEMINI_API_KEY=your_key_here
   ```

### Полный файл .env

Скопируйте `.env.example` в `.env` и отредактируйте:

```env
# ====================================
# Telegram Configuration (Required)
# ====================================

TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# ====================================
# Optional: LLM API Keys
# ====================================

# GROQ_API_KEY=gsk_your_key_here
# GEMINI_API_KEY=your_key_here
```

## 🏃 Запуск

### Локально
```bash
python main.py
```

### С помощью systemd (после установки через install.sh)
```bash
# Просмотр статуса
systemctl status temka_bot

# Просмотр логов
journalctl -u temka_bot -f

# Остановка/запуск
systemctl stop temka_bot
systemctl start temka_bot
```

## 📦 Зависимости

- **python-telegram-bot** - библиотека для работы с Telegram API
- **python-dotenv** - загрузка переменных из `.env`
- **aiohttp** - асинхронные HTTP запросы

Полный список в [requirements.txt](requirements.txt)

## 🛠 Разработка

### Структура проекта
```
Temka_bot/
├── main.py              # Основной файл бота с обработчиками команд
├── config.py            # Управление конфигурацией и переменными
├── requirements.txt     # Python зависимости
├── .env.example         # Пример конфигурации
├── .gitignore           # Git ignore правила
├── install.sh           # Скрипт автоматической установки
└── README.md            # Этот файл
```

### Безопасность

- **TELEGRAM_CHAT_ID** — ограничивает доступ только вашему чату. Без него бот отклонит все сообщения от других пользователей
- **.env файл** — содержит чувствительные данные и должен быть в `.gitignore`
- **chmod 600** — install.sh автоматически ограничивает права доступа к `.env` файлу

### Добавление новых команд

Добавьте в `main.py`:

```python
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """My custom command."""
    # Check authorization
    if update.effective_chat.id != config.ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text("Ответ на команду")

# В функции main()
application.add_handler(CommandHandler("mycommand", my_command))
```

### Интеграция с API

Используйте переменные из `config.py`:

```python
from config import GROQ_API_KEY, GEMINI_API_KEY

if GROQ_API_KEY:
    # use Groq API
    pass

if GEMINI_API_KEY:
    # use Gemini API
    pass
```

## 🐛 Решение проблем

### "TELEGRAM_TOKEN environment variable is not set"
- Убедитесь, что файл `.env` существует в корневой директории
- Проверьте, что в нем указан `TELEGRAM_TOKEN=ваш_токен`

### "TELEGRAM_CHAT_ID environment variable is not set"
- Это **обязательный** параметр. Получите его через @userinfobot в Telegram
- Добавьте в `.env`: `TELEGRAM_CHAT_ID=ваш_id`

### "У вас нет доступа к этому боту"
- Проверьте, что TELEGRAM_CHAT_ID в `.env` совпадает с вашим ID
- Используйте @userinfobot чтобы узнать правильный ID

### "ModuleNotFoundError: No module named 'telegram'"
```bash
# Активируйте виртуальное окружение
source venv/bin/activate
# Переустановите зависимости
pip install -r requirements.txt
```

### Бот не отвечает
- Проверьте интернет соединение
- Убедитесь, что токен правильный (полученный от @BotFather)
- Просмотрите логи: `python main.py` (вывод ошибок в консоль)
- Проверьте, что ваш Chat ID указан правильно в `.env`

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

## 👨‍💻 Автор

[hakkkaido](https://github.com/hakkkaido)

## 🤝 Вклад

Приветствуются pull requests! Для больших изменений сначала откройте issue.

## 📞 Поддержка

Если у вас есть вопросы, создайте [issue](https://github.com/hakkkaido/Temka_bot/issues) на GitHub.

---

**Удачи в разработке! 🚀**

