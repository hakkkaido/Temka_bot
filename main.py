"""Gemini Bot — Personal AI assistant via Telegram + Google Gemini."""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
)
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

import config
from config import BOT_TOKEN, ADMIN_CHAT_ID, MESSAGE_QUEUE_MAX
from db import (
    init_db,
    create_session,
    get_session,
    get_active_sessions,
    set_session_done,
    set_session_active,
    set_session_idle,
    save_message,
)
from gemini_runner import run_gemini, is_busy, queue_length
from formatting import md_to_telegram_html, split_message
from voice import transcribe_voice
from scheduler import run_scheduler, _load_schedules

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Track which session user is focused on
user_focus: dict[int, str] = {}  # chat_id -> session_id

# Track pending setup state
_awaiting_setup: dict[int, str] = {}  # chat_id -> what we're waiting for (e.g. "groq_key")

SESSIONS_PER_PAGE = 5


# ==================== Security ====================

def is_admin(message: Message) -> bool:
    return message.chat.id == ADMIN_CHAT_ID


def is_admin_cb(callback: CallbackQuery) -> bool:
    return callback.message.chat.id == ADMIN_CHAT_ID


# ==================== Keyboards ====================

def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Сессии", callback_data="sessions:0"),
            InlineKeyboardButton(text="➕ Новая", callback_data="new_session"),
        ],
        [
            InlineKeyboardButton(text="📊 Статус", callback_data="status"),
            InlineKeyboardButton(text="🗑 Закрыть все", callback_data="close_all"),
        ],
    ])


def build_sessions_keyboard(sessions: list[dict], page: int = 0, focus_id: str = None) -> InlineKeyboardMarkup:
    total = len(sessions)
    start = page * SESSIONS_PER_PAGE
    end = start + SESSIONS_PER_PAGE
    page_sessions = sessions[start:end]

    buttons = []
    for s in page_sessions:
        icon = {"active": "⚡", "idle": "💤"}.get(s["status"], "❓")
        marker = "👉 " if s["session_id"] == focus_id else ""
        name = s["name"][:28] + ".." if len(s["name"]) > 28 else s["name"]

        buttons.append([
            InlineKeyboardButton(
                text=f"{marker}{icon} {name}",
                callback_data=f'switch:{s["session_id"]}',
            ),
            InlineKeyboardButton(text="❌", callback_data=f'close:{s["session_id"]}'),
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"sessions:{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="Вперед ➡", callback_data=f"sessions:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== Text extraction ====================

async def extract_text(message: Message) -> tuple[str | None, str | None]:
    """Extract text and optional image path from message.

    Returns:
        (text, image_path) — image_path is set when photo is attached
    """
    image_path = None

    # Download photo if present
    if message.photo:
        photo = message.photo[-1]  # highest resolution
        file = await bot.get_file(photo.file_id)
        ext = "jpg"
        save_path = config.WORK_DIR / f"image_{photo.file_id[-8:]}.{ext}"
        config.WORK_DIR.mkdir(parents=True, exist_ok=True)
        await bot.download_file(file.file_path, destination=str(save_path))
        image_path = str(save_path)
        logger.info(f"Photo saved: {image_path}")

    if message.text:
        return message.text, image_path

    if message.voice or message.audio:
        voice_obj = message.voice or message.audio
        transcript = await transcribe_voice(voice_obj, bot)
        if transcript is None:
            return None, None  # Groq not configured
        return transcript, image_path

    if message.caption:
        return message.caption, image_path

    if image_path:
        return "Опиши изображение", image_path

    return None, None


# ==================== Commands ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message):
        return

    voice_status = "✅ Groq" if config.GROQ_API_KEY else "❌ /setup"
    gemini_status = "✅ Gemini" if config.GEMINI_API_KEY else "❌ /setup"
    
    await message.reply(
        f"🤖 <b>Gemini Bot</b> — твой AI-ассистент\n\n"
        f"Gemini — мощный языковой AI\n"
        f"🎙 Голосовые: {voice_status}\n"
        f"💬 {gemini_status}\n\n"
        f"Просто напиши мне.",
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(),
    )


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    if not is_admin(message):
        return
    await message.reply(
        "🎮 <b>Панель управления</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(),
    )


@dp.message(Command("new"))
async def cmd_new(message: Message):
    if not is_admin(message):
        return
    user_focus[message.chat.id] = "__force_new__"
    await message.reply(
        "Send your message — it will start a new session.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_new")],
        ]),
    )


@dp.message(Command("sessions"))
async def cmd_sessions(message: Message):
    if not is_admin(message):
        return
    sessions = get_active_sessions()
    if not sessions:
        await message.reply(
            "No active sessions.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Новая", callback_data="new_session")],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]),
        )
        return

    focus_id = user_focus.get(message.chat.id)
    await message.reply(
        f"<b>Sessions</b> ({len(sessions)} active)",
        parse_mode=ParseMode.HTML,
        reply_markup=build_sessions_keyboard(sessions, 0, focus_id),
    )


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message):
        return
    await _send_status(message.chat.id)


@dp.message(Command("setup"))
async def cmd_setup(message: Message):
    if not is_admin(message):
        return
    
    if not config.GROQ_API_KEY:
        _awaiting_setup[message.chat.id] = "groq_key"
        await message.reply(
            "Send your Groq API key for voice transcription (or /skip to skip):"
        )
    else:
        await message.reply("Setup already done.")


@dp.message(Command("skip"))
async def cmd_skip(message: Message):
    if not is_admin(message):
        return
    
    chat_id = message.chat.id
    if chat_id in _awaiting_setup:
        del _awaiting_setup[chat_id]
        await message.reply("Skipped. Groq is optional.")
    else:
        await message.reply("Nothing to skip.")


# ==================== Text handler ====================

@dp.message(F.text | F.voice | F.audio | F.photo)
async def handle_message(message: Message):
    if not is_admin(message):
        logger.warning(f"Unauthorized access from {message.chat.id}")
        return

    # Check if user is waiting for API key setup
    if message.chat.id in _awaiting_setup:
        waiting_for = _awaiting_setup[message.chat.id]
        if waiting_for == "groq_key" and message.text:
            config.set_env_var("GROQ_API_KEY", message.text)
            config.reload_groq_key()
            del _awaiting_setup[message.chat.id]
            await message.reply("✅ Groq API key saved. Voice transcription enabled.")
            return

    # Extract text from message
    text, image_path = await extract_text(message)
    if not text:
        await message.reply("No text found in message.")
        return

    # Get or create session
    chat_id = message.chat.id
    focus = user_focus.get(chat_id)

    if focus == "__force_new__":
        session_id = str(uuid.uuid4())
        user_focus[chat_id] = session_id
        create_session(session_id, text[:50])
    elif focus and (session := get_session(focus)):
        session_id = focus
    else:
        # Create new session if none focused
        session_id = str(uuid.uuid4())
        user_focus[chat_id] = session_id
        create_session(session_id, text[:50])

    set_session_active(session_id)

    # Send to Gemini
    status_msg = await message.reply("⏳ Processing...")

    async def on_result(result_text: str, sid: str):
        set_session_idle(sid)
        
        # Format response
        formatted = md_to_telegram_html(result_text)
        chunks = split_message(formatted, max_len=4000)

        try:
            # Edit first chunk
            await status_msg.edit_text(chunks[0], parse_mode=ParseMode.HTML)
            # Send remaining chunks
            for chunk in chunks[1:]:
                await message.reply(chunk, parse_mode=ParseMode.HTML)
        except TelegramBadRequest as e:
            logger.error(f"Telegram error: {e}")
            # Fallback: send as plain text
            for chunk in chunks:
                await message.reply(chunk[:4000])

    gemini_status = await run_gemini(
        text,
        session_id=session_id,
        on_result=on_result,
    )

    if gemini_status["status"] == "queue_full":
        await status_msg.edit_text(
            "❌ Queue full (limit: 5). Try again later.",
        )
    elif gemini_status["status"] == "queued":
        pos = gemini_status.get("position", "?")
        await status_msg.edit_text(f"⏳ Queued (position: {pos})")


# ==================== Callbacks ====================

@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    await callback.message.edit_text(
        "🎮 <b>Панель управления</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "new_session")
async def cb_new_session(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    user_focus[callback.message.chat.id] = "__force_new__"
    await callback.message.edit_text(
        "Send a message to start a new session.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="menu")],
        ]),
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel_new")
async def cb_cancel_new(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    chat_id = callback.message.chat.id
    if user_focus.get(chat_id) == "__force_new__":
        del user_focus[chat_id]
    await callback.message.edit_text(
        "Cancelled.",
        reply_markup=build_main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("sessions:"))
async def cb_sessions(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    page = int(callback.data.split(":")[1])
    sessions = get_active_sessions()
    focus_id = user_focus.get(callback.message.chat.id)
    await callback.message.edit_text(
        f"<b>Sessions</b> ({len(sessions)} active)",
        parse_mode=ParseMode.HTML,
        reply_markup=build_sessions_keyboard(sessions, page, focus_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("switch:"))
async def cb_switch(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    session_id = callback.data.split(":")[1]
    user_focus[callback.message.chat.id] = session_id
    session = get_session(session_id)
    await callback.message.edit_text(
        f"✅ Switched to: <b>{session['name']}</b>\n"
        f"Status: {session['status']}\n"
        f"Summary: {session['summary'] or '(empty)'}",
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("close:"))
async def cb_close(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    session_id = callback.data.split(":")[1]
    set_session_done(session_id)
    if user_focus.get(callback.message.chat.id) == session_id:
        del user_focus[callback.message.chat.id]
    sessions = get_active_sessions()
    focus_id = user_focus.get(callback.message.chat.id)
    await callback.message.edit_text(
        f"<b>Sessions</b> ({len(sessions)} active) — closed",
        parse_mode=ParseMode.HTML,
        reply_markup=build_sessions_keyboard(sessions, 0, focus_id),
    )
    await callback.answer()


@dp.callback_query(F.data == "close_all")
async def cb_close_all(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    sessions = get_active_sessions()
    for s in sessions:
        set_session_done(s["session_id"])
    user_focus.pop(callback.message.chat.id, None)
    await callback.message.edit_text(
        f"✅ Closed {len(sessions)} session(s).",
        reply_markup=build_main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery):
    if not is_admin_cb(callback):
        return
    await _send_status(callback.message.chat.id)
    await callback.answer()


async def _send_status(chat_id: int):
    busy = is_busy()
    queue = queue_length()
    sessions = get_active_sessions()
    
    status_text = (
        f"🔧 <b>Status</b>\n\n"
        f"Gemini: {'🟢 Ready' if not busy else '🔴 Busy'}\n"
        f"Queue: {queue}/5\n"
        f"Sessions: {len(sessions)} active\n"
    )
    
    if sessions:
        status_text += "\n<b>Sessions:</b>\n"
        for s in sessions[:5]:
            icon = {"active": "⚡", "idle": "💤"}.get(s["status"], "❓")
            status_text += f"{icon} {s['name'][:30]}\n"
    
    await bot.send_message(
        chat_id,
        status_text,
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(),
    )


# ==================== Main ====================

async def main():
    init_db()
    
    # Set up commands
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="menu", description="Show menu"),
        BotCommand(command="new", description="Create new session"),
        BotCommand(command="sessions", description="List sessions"),
        BotCommand(command="status", description="Show status"),
        BotCommand(command="setup", description="Setup optional APIs"),
    ])

    logger.info("Starting Gemini Bot...")
    
    # Start scheduler in background
    asyncio.create_task(run_scheduler(bot, ADMIN_CHAT_ID))
    
    # Start dispatcher
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
#!/usr/bin/env python3
"""
Temka Bot - Telegram bot with Gemini + Groq API integration.
"""

import logging
import os
import tempfile
import base64
from typing import Dict

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_chat_allowed(chat_id: int) -> bool:
    return config.BOT_PUBLIC or chat_id in config.AUTHORIZED_CHAT_IDS


def extract_gemini_text(response: Dict) -> str:
    if not isinstance(response, dict):
        return str(response)

    if "candidates" in response and isinstance(response["candidates"], list):
        for candidate in response["candidates"]:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list):
                    texts = []
                    for part in parts:
                        if isinstance(part, dict):
                            if "text" in part and isinstance(part["text"], str):
                                texts.append(part["text"])
                            elif "content" in part and isinstance(part["content"], dict):
                                nested = part["content"].get("text")
                                if isinstance(nested, str):
                                    texts.append(nested)
                    if texts:
                        return "\n".join(texts).strip()
            if isinstance(content, list):
                texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("text")]
                if texts:
                    return "\n".join(texts).strip()
            if isinstance(content, str):
                return content.strip()

    if "output" in response:
        output = response["output"]
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, dict):
                if "content" in first:
                    content = first["content"]
                    if isinstance(content, list):
                        texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("text")]
                        return "\n".join(texts).strip()
                    if isinstance(content, str):
                        return content.strip()
                if "text" in first:
                    return first["text"].strip()

    if "text" in response and isinstance(response["text"], str):
        return response["text"].strip()

    if "transcription" in response and isinstance(response["transcription"], str):
        return response["transcription"].strip()

    return str(response)


def build_gemini_request(url: str) -> tuple[str, Dict[str, str]]:
    headers = {"Content-Type": "application/json"}
    if config.GEMINI_API_KEY:
        if config.GEMINI_API_KEY.startswith("ya29.") or config.GEMINI_API_KEY.startswith("ya29_"):
            headers["Authorization"] = f"Bearer {config.GEMINI_API_KEY}"
        else:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}key={config.GEMINI_API_KEY}"
    return url, headers


async def query_gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        return "Gemini API не настроен. Пожалуйста, установите GEMINI_API_KEY в .env."

    url, headers = build_gemini_request(config.GEMINI_API_URL)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "temperature": 0.7,
        "maxOutputTokens": 512,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                text = await response.text()
                if response.status != 200:
                    logger.error(f"Gemini API error {response.status}: {text}")
                    return f"Ошибка Gemini API: {response.status}"

                data = await response.json()
                result = extract_gemini_text(data)
                return result or "Gemini вернул пустой ответ."
    except Exception as exc:
        logger.exception("Gemini request failed")
        return f"Ошибка при обращении к Gemini: {exc}"


async def generate_image_gemini(prompt: str) -> bytes:
    if not config.GEMINI_API_KEY:
        raise ValueError("Gemini API не настроен.")

    url, headers = build_gemini_request(config.GEMINI_IMAGEN_API_URL)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                text = await response.text()
                if response.status != 200:
                    logger.error(f"Gemini Imagen API error {response.status}: {text}")
                    raise Exception(f"Ошибка Gemini Imagen API: {response.status}")

                data = await response.json()
                if "candidates" in data and isinstance(data["candidates"], list):
                    for candidate in data["candidates"]:
                        if not isinstance(candidate, dict):
                            continue
                        content = candidate.get("content")
                        if isinstance(content, dict):
                            parts = content.get("parts")
                            if isinstance(parts, list):
                                for part in parts:
                                    if not isinstance(part, dict):
                                        continue
                                    inline_data = part.get("inlineData")
                                    if isinstance(inline_data, dict):
                                        image_data = inline_data.get("data")
                                        if image_data:
                                            return base64.b64decode(image_data)
                raise Exception("Не удалось получить изображение.")
    except Exception as exc:
        logger.exception("Gemini image generation failed")
        raise Exception(f"Ошибка при генерации изображения: {exc}")


async def transcribe_groq(file_path: str) -> str:
    if not config.GROQ_API_KEY:
        return "Groq API не настроен. Пожалуйста, установите GROQ_API_KEY в .env."

    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                open(file_path, "rb"),
                filename=os.path.basename(file_path),
                content_type="audio/ogg"
            )

            async with session.post(config.GROQ_API_URL, headers=headers, data=form, timeout=120) as response:
                text = await response.text()
                if response.status != 200:
                    logger.error(f"Groq API error {response.status}: {text}")
                    return f"Ошибка Groq API: {response.status}"

                data = await response.json()
                if "text" in data:
                    return data["text"].strip()
                if "transcription" in data:
                    return data["transcription"].strip()
                if "results" in data:
                    results = data["results"]
                    if isinstance(results, list) and results:
                        first = results[0]
                        if isinstance(first, dict) and "alternatives" in first:
                            alternatives = first["alternatives"]
                            if isinstance(alternatives, list) and alternatives:
                                return alternatives[0].get("transcript", "").strip()

                return str(data)
    except Exception as exc:
        logger.exception("Groq transcription failed")
        return f"Ошибка при расшифровке аудио: {exc}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        logger.warning(f"Unauthorized access attempt from chat {chat_id}")
        return

    bot_link = None
    try:
        bot_link = f"https://t.me/{context.bot.username}"
    except Exception:
        bot_link = None

    voice_status = "✅ Включен (Groq)" if config.GROQ_API_KEY else "❌ Отключен"
    gemini_status = "✅ Доступен" if config.GEMINI_API_KEY else "❌ Недоступен"
    image_status = "✅ Доступен" if config.GEMINI_API_KEY else "❌ Недоступен"
    public_status = "Да" if config.BOT_PUBLIC else "Нет"

    message = [
        "Привет! 🤖\n",
        "Я Temka Bot — ваш AI-помощник в Telegram.\n\n",
        "Доступные команды:\n",
        "/start - Начать\n",
        "/help - Справка\n",
        "/update - Обновить ключи API\n",
        "/image <описание> - Сген8515722063:AAHfMaBe8Z1QriX1RF4eto8ilQRFsoDRmy8ерировать изображение\n\n",
        "Интеграции:\n",
        f"🎙️ Голосовые: {voice_status}\n",
        f"🤖 Gemini AI: {gemini_status}\n",
        f"🎨 Генерация изображений: {image_status}\n",
        f"🌐 Доступен по ссылке: {public_status}\n",
    ]

    if bot_link:
        message.append(f"Ссылка на бота: {bot_link}\n")

    await update.message.reply_text("".join(message))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return

    await update.message.reply_text(
        "📖 Справка:\n\n"
        "Я умею отвечать на текстовые сообщения через Google Gemini и расшифровывать голосовые через Groq.\n"
        "Также могу генерировать изображения по описанию.\n\n"
        "Команды:\n"
        "/start - Начать\n"
        "/help - Справка\n"
        "/update - Обновить ключи API\n"
        "/image <описание> - Сгенерировать изображение\n\n"
        "Просто отправьте мне сообщение или голосовое сообщение.\n"
        "Если бот открыт для всех, используйте ссылку t.me/<your_bot_username>."
    )


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return

    config.reload_groq_key()
    config.reload_gemini_key()
    await update.message.reply_text("✅ Ключи API обновлены.")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return

    if not config.GEMINI_API_KEY:
        await update.message.reply_text("Gemini API не настроен. Пожалуйста, установите GEMINI_API_KEY в .env.")
        return

    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пожалуйста, укажите описание для генерации изображения. Пример: /image красивый закат над горами")
        return

    await update.message.reply_text("🎨 Генерирую изображение...")

    try:
        image_data = await generate_image_gemini(prompt)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name

        try:
            with open(temp_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=f"Изображение по запросу: {prompt}")
        finally:
            os.remove(temp_path)
    except Exception as exc:
        await update.message.reply_text(f"Ошибка при генерации изображения: {exc}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        logger.warning(f"Unauthorized message from chat {chat_id}")
        return

    user_message = update.message.text.strip()
    logger.info(f"User {update.effective_user.id} sent: {user_message}")

    if not config.GEMINI_API_KEY:
        await update.message.reply_text(
            "Gemini API не настроен. Отправьте текст или голосовое сообщение после настройки GEMINI_API_KEY."
        )
        return

    reply_text = await query_gemini(user_message)
    await update.message.reply_text(reply_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        logger.warning(f"Unauthorized voice message from chat {chat_id}")
        return

    if not config.GROQ_API_KEY:
        await update.message.reply_text(
            "Groq API не настроен. Пожалуйста, добавьте GROQ_API_KEY в .env."
        )
        return

    await update.message.reply_text("🔄 Загружаю голосовое сообщение и расшифровываю...")
    voice = update.message.voice
    voice_file = await voice.get_file()

    with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        await voice_file.download_to_drive(temp_path)
        transcription = await transcribe_groq(temp_path)
        if config.GEMINI_API_KEY:
            answer = await query_gemini(transcription)
            await update.message.reply_text(
                f"📄 Транскрипция:\n{transcription}\n\n🤖 Ответ Gemini:\n{answer}"
            )
        else:
            await update.message.reply_text(f"📄 Транскрипция:\n{transcription}")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def main() -> None:
    logger.info("Starting Temka Bot...")
    logger.info(f"Public mode: {'enabled' if config.BOT_PUBLIC else 'disabled'}")
    logger.info(f"Authorized chat IDs: {config.AUTHORIZED_CHAT_IDS}")
    logger.info(f"Voice (Groq): {'enabled' if config.GROQ_API_KEY else 'disabled'}")
    logger.info(f"Gemini: {'enabled' if config.GEMINI_API_KEY else 'disabled'}")
    logger.info(f"Image generation (Gemini): {'enabled' if config.GEMINI_API_KEY else 'disabled'}")

    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
