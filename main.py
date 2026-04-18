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


async def query_gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        return "Gemini API не настроен. Пожалуйста, установите GEMINI_API_KEY в .env."

    url = config.GEMINI_API_URL
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": config.GEMINI_API_KEY,
    }

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

    url = config.GEMINI_IMAGEN_API_URL
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": config.GEMINI_API_KEY,
    }

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
        "/image <описание> - Сгенерировать изображение\n\n",
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
