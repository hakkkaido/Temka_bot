#!/bin/bash

# ==============================================================================
# Универсальный установщик для проекта Temka_bot
# ==============================================================================

# --- Цвета для вывода ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Конфигурация ---
REPO_URL="https://github.com/hakkkaido/Temka_bot.git"
INSTALL_DIR="/opt/Temka_bot"
SERVICE_NAME="temka_bot"

# --- Функции ---
function print_info {
    echo -e "${GREEN}[INFO] $1${NC}"
}

function print_warn {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

function print_error {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# --- Начало выполнения ---
print_info "Запуск универсального установщика для Temka_bot..."

# 1. Проверка прав суперпользователя
if [ "$EUID" -ne 0 ]; then
  print_error "Пожалуйста, запустите этот скрипт с правами sudo."
fi

# 2. Установка системных зависимостей
print_info "Обновление списка пакетов и установка зависимостей (git, python3, pip, venv)..."
apt-get update > /dev/null
apt-get install -y git python3 python3-pip python3-venv > /dev/null
if [ $? -ne 0 ]; then
    print_error "Не удалось установить системные зависимости. Проверьте менеджер пакетов (скрипт использует apt-get)."
fi

# 3. Подготовка директории проекта
if [ -f "./main.py" ] && [ -f "./config.py" ] && [ -f "./install.sh" ]; then
    print_info "Текущая директория содержит проект Temka_bot. Устанавливаем из локальной копии."
    INSTALL_DIR="$(pwd)"
else
    if [ -d "$INSTALL_DIR" ]; then
        print_warn "Директория $INSTALL_DIR уже существует. Пропускаем клонирование."
    else
        print_info "Клонирование репозитория из $REPO_URL в $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        if [ $? -ne 0 ]; then
            print_error "Не удалось клонировать репозиторий."
        fi
    fi
fi

cd "$INSTALL_DIR"

# 4. Создание и активация виртуального окружения
print_info "Создание виртуального окружения Python в '$INSTALL_DIR/venv'..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    print_error "Не удалось создать виртуальное окружение."
fi

# 5. Установка Python-зависимостей
if [ -f "requirements.txt" ]; then
    print_info "Установка зависимостей из requirements.txt..."
    venv/bin/pip install -r requirements.txt > /dev/null
    if [ $? -ne 0 ]; then
        print_error "Не удалось установить Python-зависимости. Проверьте файл requirements.txt."
    fi
else
    print_warn "Файл requirements.txt не найден. Пропускаем установку Python-зависимостей."
fi

# 6. Настройка конфигурации (.env файл)
echo ""
echo "==========================================================="
echo "    Конфигурация"
echo "==========================================================="
echo ""
echo "Требуется следующая информация:"
echo ""
echo "❶ Telegram Bot Token"
echo "   Получите от @BotFather в Telegram"
echo ""
while true; do
    read -p "   Bot Token: " TELEGRAM_TOKEN
    if [[ "$TELEGRAM_TOKEN" =~ ^[0-9]+:.+$ ]]; then
        break
    fi
    print_warn "   Неверный формат. Должен быть: 123456:ABC-DEF..."
done

echo ""
echo "❷ Ваш Chat ID (User ID)"
echo "   Получите от @userinfobot в Telegram"
echo "   Это нужно для безопасности - только вы сможете использовать бота"
echo ""
while true; do
    read -p "   Chat ID: " TELEGRAM_CHAT_ID
    if [[ "$TELEGRAM_CHAT_ID" =~ ^[0-9]+$ ]]; then
        break
    fi
    print_warn "   Неверный формат. Должно быть число: 987654321"
done

echo ""
echo "❸ Groq API Key (опционально, для голосовых сообщений)"
echo "   Бесплатный ключ: https://console.groq.com/keys"
echo "   Нажмите Enter чтобы пропустить"
echo ""
read -sp "   Groq API Key: " GROQ_API_KEY
echo ""

echo ""
echo "❹ Google Gemini API Key (опционально, для интеграции с Gemini)"
echo "   Получите на https://ai.google.dev/"
echo "   Нажмите Enter чтобы пропустить"
echo ""
read -sp "   Gemini API Key: " GEMINI_API_KEY
echo ""

echo "❺ Хотите сделать бота доступным по ссылке для всех пользователей? (y/n)"
echo "   Если выбрать 'y', бот будет работать в публичном режиме и принимать сообщения от любых пользователей."
echo ""
read -p "   Публичный режим (y/n): " BOT_PUBLIC_CHOICE
if [[ "$BOT_PUBLIC_CHOICE" == "y" || "$BOT_PUBLIC_CHOICE" == "Y" ]]; then
    BOT_PUBLIC=true
else
    BOT_PUBLIC=false
fi

echo "" > .env # Создаем или очищаем .env файл
echo "TELEGRAM_TOKEN=\"$TELEGRAM_TOKEN\"" >> .env
if [[ "$BOT_PUBLIC" == "true" ]]; then
    echo "BOT_PUBLIC=true" >> .env
else
    echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID" >> .env
fi

if [ ! -z "$GROQ_API_KEY" ]; then
    echo "GROQ_API_KEY=\"$GROQ_API_KEY\"" >> .env
fi

if [ ! -z "$GEMINI_API_KEY" ]; then
    echo "GEMINI_API_KEY=\"$GEMINI_API_KEY\"" >> .env
fi

chmod 600 .env
print_info ".env файл успешно создан и защищен (chmod 600)."

# 7. Настройка systemd сервиса (для автозапуска)
read -p "Хотите создать systemd сервис для автозапуска бота? (y/n): " CREATE_SERVICE
if [[ "$CREATE_SERVICE" == "y" || "$CREATE_SERVICE" == "Y" ]]; then
    print_info "Создание systemd сервиса '$SERVICE_NAME'..."

    # Определяем основной скрипт
    if [ -f "main.py" ]; then
        MAIN_SCRIPT="main.py"
    elif [ -f "bot.py" ]; then
        MAIN_SCRIPT="bot.py"
    elif [ -f "run.py" ]; then
        MAIN_SCRIPT="run.py"
    else
        read -p "Введите имя основного скрипта (например, main.py): " MAIN_SCRIPT
    fi

    cat > /etc/systemd/system/$SERVICE_NAME.service << EOL
[Unit]
Description=Temka Telegram Bot
After=network.target

[Service]
User=$SUDO_USER
Group=$(id -gn $SUDO_USER)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/$MAIN_SCRIPT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

    print_info "Перезагрузка демона systemd и запуск сервиса..."
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    systemctl start $SERVICE_NAME

    print_info "Статус сервиса:"
    systemctl status $SERVICE_NAME --no-pager
else
    print_warn "Пропускаем создание systemd сервиса."
fi

print_info "==========================================================="
print_info "🎉 Установка успешно завершена!"
print_info "Проект находится в директории: $INSTALL_DIR"
if [[ "$CREATE_SERVICE" == "y" || "$CREATE_SERVICE" == "Y" ]]; then
    print_info "Бот запущен как сервис. Для просмотра логов используйте: journalctl -u $SERVICE_NAME -f"
else
    print_info "Для запуска бота вручную, перейдите в '$INSTALL_DIR' и выполните: ./venv/bin/python $MAIN_SCRIPT"
fi
print_info "==========================================================="
