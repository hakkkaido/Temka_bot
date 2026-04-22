# 🚀 START HERE - НАЧНИ ОТСЮДА!

Добро пожаловать в **Gemini Bot** — адаптацию QwenClaw для Google Gemini API.

## ⚡ Быстрый старт (2 минуты)

### 1. Запустить бота
```bash
cd /workspaces/Temka_bot
python main.py
```

### 2. Открыть Telegram
Напиши боту: `/start`

### 3. Начать общаться!
Просто пиши сообщения и получай ответы от AI.

---

## 📚 Документация

### 📖 **ГЛАВНЫЙ ФАЙЛ** (начни с него!)
- [`GEMINI_BOT_README.md`](./GEMINI_BOT_README.md) — полное руководство на русском

### 📊 Другие документы
- [`REPORT.txt`](./REPORT.txt) — подробный отчёт о проделанной работе
- [`CHANGELOG.md`](./CHANGELOG.md) — что изменилось относительно QwenClaw
- [`requirements.txt`](./requirements.txt) — список зависимостей

---

## ✅ Проверка системы

Убедись что всё работает:
```bash
python test_setup.py
```

Должно вывести: ✅ ALL TESTS PASSED!

---

## 🎮 Основные команды Telegram

| Команда | Действие |
|---------|----------|
| `/start` | Начать |
| `/menu` | Главное меню |
| `/new` | Новая сессия |
| `/sessions` | Список сессий |
| `/status` | Статус бота |
| `/setup` | Настроить голос (опционально) |

---

## 🔧 Настройка API ключей

Все ключи уже в `.env` файле:
- ✅ Telegram Bot Token
- ✅ Google Gemini API
- ✅ Groq API (для голоса)

**Если нужно изменить:**
```bash
nano .env
# Отредактируй нужные значения
# Ctrl+O → Enter → Ctrl+X
```

---

## 🧪 Тестирование

```bash
# Проверить конфигурацию
python test_setup.py

# Запустить бота
python main.py

# В другом терминале можно проверить лог:
tail -f bot.log
```

---

## 📊 Файлы проекта

**Главные файлы:**
- `main.py` — обработчик Telegram команд
- `gemini_runner.py` — работа с Google Gemini API
- `config.py` — конфигурация

**Вспомогательные:**
- `db.py` — база данных (SQLite)
- `formatting.py` — форматирование (Markdown → HTML)
- `voice.py` — распознавание голоса (Groq)
- `scheduler.py` — планировщик задач

**Конфигурация:**
- `.env` — твои API ключи
- `.env.example` — пример конфигурации
- `requirements.txt` — зависимости

**Документация:**
- `GEMINI_BOT_README.md` — ГЛАВНЫЙ ФАЙЛ 📖
- `REPORT.txt` — подробный отчёт
- `CHANGELOG.md` — история изменений

---

## ❓ Частые вопросы

**Q: Почему используется Gemma 3 вместо Gemini?**
A: Бесплатная квота на Gemini-2.0-flash исчерпана. Gemma 3 работает столь же хорошо.

**Q: Как включить распознавание голоса?**
A: `/setup` в Telegram и отправь свой Groq API ключ. 
   Или добавь в `.env`: `GROQ_API_KEY=gsk_...`

**Q: Где сохраняются сообщения?**
A: В SQLite базе: `/workspaces/Temka_bot/data/bot.db`

**Q: Как удалить сессию?**
A: `/sessions` → выбери сессию → нажми ❌

**Q: Сколько сессий одновременно?**
A: Неограниченно, но максимум 5 запросов в очереди.

---

## 🎯 Что дальше?

1. ✅ Прочитай [`GEMINI_BOT_README.md`](./GEMINI_BOT_README.md)
2. ✅ Запусти `python test_setup.py` (проверка конфигурации)
3. ✅ Запусти `python main.py` (старт бота)
4. ✅ Напиши боту в Telegram: `/start`
5. ✅ Наслаждайся разговором с AI! 🎉

---

## 🆘 Если что-то не работает

1. **Проверь конфигурацию:**
   ```bash
   python test_setup.py
   ```

2. **Убедись что `.env` заполнен:**
   ```bash
   cat .env
   ```

3. **Проверь логи при запуске:**
   ```bash
   python main.py  # Логи в консоль
   ```

4. **Проверь что Python 3.10+:**
   ```bash
   python --version
   ```

---

## 📞 Контакты и ссылки

- **Исходный проект:** https://github.com/a-prs/qwenclaw
- **Google Gemini:** https://ai.google.dev/
- **Telegram Bot API:** https://core.telegram.org/bots/api

---

**Приятного использования! 🚀**

Created with ❤️ as adaptation of QwenClaw for Google Gemini
