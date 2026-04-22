# 🤖 Gemini Bot

Персональный AI-ассистент в Telegram на базе **Google Gemini API** (Gemma 3).

**Основано на:** [QwenClaw](https://github.com/a-prs/qwenclaw), но вместо Qwen используется Google Gemini.

## ✨ Возможности

- 💬 Общение с AI (Gemma 3 модель)
- 📋 Управление сессиями (создание, переключение, закрытие)
- 🎙️ Распознавание голосовых сообщений (Groq Whisper API, опционально)
- 💾 История сообщений в БД (SQLite)
- 📱 Inline-клавиатура для управления
- ⚡ Очередь запросов (макс. 5 одновременно)

## 📋 Требования

- Ubuntu/Debian (или любая Linux система)
- Python 3.10+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Google Gemini API ключ (от [ai.google.dev](https://ai.google.dev/))
- Ваш Chat ID (от [@userinfobot](https://t.me/userinfobot))

## 🚀 Установка (3 шага)

### 1️⃣ Клонируйте репозиторий
```bash
git clone https://github.com/hakkkaido/Temka_bot.git
cd Temka_bot
```

### 2️⃣ Установите зависимости
```bash
pip install -q -U google-genai aiogram python-dotenv httpx
```

### 3️⃣ Настройте `.env` файл
Создайте `.env` в корневой директории:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=models/gemma-3-1b-it
GEMINI_MAX_TURNS=15
GEMINI_TIMEOUT=600

# Groq Whisper (опционально для голоса)
GROQ_API_KEY=your_groq_api_key

# Директория работы
WORK_DIR=./workspace
```

## 🧪 Тестирование

Проверьте что всё настроено корректно:
```bash
python test_setup.py
```

Вывод должен показать:
- ✅ Configuration Check (все параметры)
- ✅ Gemini API Connection (успешное подключение)
- ✅ Database Check (инициализация БД)
- ✅ Module Import Check (все модули загружены)

## ▶️ Запуск бота

```bash
python main.py
```

Бот начнёт получать сообщения от вас в Telegram!

## 📱 Команды Telegram

| Команда | Описание |
|---------|---------|
| `/start` | Начать работу |
| `/menu` | Показать меню |
| `/new` | Создать новую сессию |
| `/sessions` | Список всех сессий |
| `/status` | Статус бота |
| `/setup` | Настроить Groq API (опционально) |

## 🎮 Управление через кнопки

- **📋 Сессии** — переключение между сессиями
- **➕ Новая** — создать новую сессию
- **📊 Статус** — просмотр текущего состояния
- **🗑 Закрыть все** — закрыть все сессии

## 🔧 Файлы проекта

```
├── main.py                 # Главный обработчик Telegram
├── gemini_runner.py        # Работа с Gemini API
├── config.py               # Конфигурация (переменные окружения)
├── db.py                   # SQLite база данных
├── formatting.py           # Форматирование Markdown → HTML
├── voice.py                # Распознавание голоса (Groq)
├── scheduler.py            # Планировщик задач (опционально)
├── test_setup.py           # Проверка конфигурации
├── requirements.txt        # Зависимости Python
├── .env.example            # Пример `.env` файла
└── workspace/              # Рабочая директория
    └── schedules.json      # Планируемые задачи
```

## 📚 API Ключи (как получить)

### Google Gemini API
1. Перейти на [ai.google.dev](https://ai.google.dev/)
2. Нажать "Get API key"
3. Скопировать ключ

### Telegram Bot Token
1. Написать [@BotFather](https://t.me/BotFather)
2. Команда `/newbot`
3. Скопировать токен

### Groq API (для голосовых сообщений)
1. Перейти на [console.groq.com/keys](https://console.groq.com/keys)
2. Создать новый ключ
3. Скопировать в `.env` (или настроить потом через `/setup`)

## 🎙️ Голосовые сообщения

Способ 1 (при запуске):
```bash
# Добавить GROQ_API_KEY в .env
GROQ_API_KEY=gsk_your_key_here
```

Способ 2 (во время работы):
```
/setup
# Отправить ваш Groq API ключ
```

## 🐳 Запуск в контейнере Docker (опционально)

```bash
docker build -t gemini-bot .
docker run --env-file .env gemini-bot
```

## 📊 Структура БД

### Таблица `sessions`
```
- session_id (PRIMARY KEY)
- name
- summary
- status (idle/active/done)
- created_at
- last_message_at
```

### Таблица `history`
```
- id (PRIMARY KEY)
- role (user/assistant)
- text
- session_id (FOREIGN KEY)
- created_at
```

## 🔐 Безопасность

- Бот доступен **только вам** (по TELEGRAM_CHAT_ID)
- Все сообщения сохраняются локально (SQLite)
- Никаких логов из Telegram API

## 🐛 Отладка

Видеть логи:
```bash
LOGLEVEL=DEBUG python main.py
```

Проверить конфигурацию:
```bash
cat .env
python test_setup.py
```

## 📝 Лицензия

MIT (см. файл LICENSE)

## 🔗 Оригинальные проекты

- [QwenClaw](https://github.com/a-prs/qwenclaw) — исходная конфигурация
- [Gemini API](https://ai.google.dev/) — генерация текста
- [Groq API](https://groq.com/) — распознавание речи

## 💡 Примеры использования

### Простой чат
```
You: Привет!
Bot: Привет! Как дела? Чем я могу тебе помочь?
```

### Продолжение разговора (в одной сессии)
```
You: Расскажи мне о Python
Bot: Python — это язык программирования...
You: А как его установить?
Bot: Есть несколько способов установки Python...
```

### Переключение сессий
```
/sessions → выбрать другую → продолжить разговор
```

---

**Сделано с ❤️ как adaptation от QwenClaw для Google Gemini**
