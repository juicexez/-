#!/usr/bin/env python3
"""
Telegram Bot - English to Russian Translator
Supports text, image (OCR), and voice message translation
"""

import os
import logging
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator
translator = GoogleTranslator(source='en', target='ru')

# Initialize speech recognizer
recognizer = sr.Recognizer()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Привет! Я бот-переводчик с английского на русский.\n\n"
        "Что я умею:\n"
        "📝 Переводить текстовые сообщения\n"
        "📷 Распознавать и переводить текст с фотографий\n"
        "🎤 Распознавать и переводить голосовые сообщения\n\n"
        "Просто отправьте мне текст, фото или голосовое сообщение на английском, "
        "и я переведу его на русский!\n\n"
        "Команды:\n"
        "/start - Показать это сообщение\n"
        "/help - Справка"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 Как пользоваться ботом:\n\n"
        "1️⃣ Текстовый перевод:\n"
        "Просто отправьте английский текст, и я сразу его переведу.\n\n"
        "2️⃣ Перевод с фото:\n"
        "Отправьте фото с английским текстом. Я распознаю текст и переведу его.\n\n"
        "3️⃣ Перевод голосовых:\n"
        "Отправьте голосовое сообщение на английском, я распознаю речь и переведу.\n\n"
        "💡 Советы:\n"
        "- Для фото используйте четкие изображения с хорошо читаемым текстом\n"
        "- Для голосовых говорите четко и не слишком быстро\n"
        "- Перевод происходит автоматически и очень быстро!"
    )
    await update.message.reply_text(help_text)


async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Translate text message from English to Russian."""
    try:
        text = update.message.text
        logger.info(f"Translating text: {text[:50]}...")

        # Translate text
        translation = translator.translate(text)

        # Send translation
        await update.message.reply_text(
            f"🔤 Перевод:\n\n{translation}",
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        logger.error(f"Error translating text: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при переводе текста. Попробуйте еще раз."
        )


async def translate_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract text from photo and translate it."""
    try:
        # Send processing message
        processing_msg = await update.message.reply_text("🔍 Распознаю текст на фото...")

        # Get the largest photo
        photo = update.message.photo[-1]

        # Download photo
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Open image with PIL
        image = Image.open(BytesIO(photo_bytes))

        # Extract text using OCR
        logger.info("Extracting text from image...")
        extracted_text = pytesseract.image_to_string(image, lang='eng')

        if not extracted_text.strip():
            await processing_msg.edit_text(
                "❌ Не удалось распознать текст на фото. Убедитесь, что текст четкий и читаемый."
            )
            return

        logger.info(f"Extracted text: {extracted_text[:50]}...")

        # Translate extracted text
        translation = translator.translate(extracted_text)

        # Send result
        result_message = (
            f"📷 Распознанный текст:\n{extracted_text}\n\n"
            f"🔤 Перевод:\n{translation}"
        )

        await processing_msg.edit_text(result_message)

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке фото. Попробуйте еще раз."
        )


async def translate_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recognize voice message and translate it."""
    try:
        # Send processing message
        processing_msg = await update.message.reply_text("🎤 Распознаю голосовое сообщение...")

        # Get voice file
        voice = update.message.voice
        voice_file = await voice.get_file()

        # Download voice message
        voice_bytes = await voice_file.download_as_bytearray()

        # Save temporarily as OGG
        temp_ogg = "/tmp/voice_message.ogg"
        temp_wav = "/tmp/voice_message.wav"

        with open(temp_ogg, 'wb') as f:
            f.write(voice_bytes)

        # Convert OGG to WAV
        logger.info("Converting audio format...")
        audio = AudioSegment.from_ogg(temp_ogg)
        audio.export(temp_wav, format="wav")

        # Recognize speech
        logger.info("Recognizing speech...")
        with sr.AudioFile(temp_wav) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='en-US')

        logger.info(f"Recognized text: {text}")

        # Translate text
        translation = translator.translate(text)

        # Send result
        result_message = (
            f"🎤 Распознанный текст:\n{text}\n\n"
            f"🔤 Перевод:\n{translation}"
        )

        await processing_msg.edit_text(result_message)

        # Clean up temporary files
        os.remove(temp_ogg)
        os.remove(temp_wav)

    except sr.UnknownValueError:
        logger.warning("Could not understand audio")
        await processing_msg.edit_text(
            "❌ Не удалось распознать речь. Попробуйте говорить четче или запишите заново."
        )
    except sr.RequestError as e:
        logger.error(f"Speech recognition error: {e}")
        await processing_msg.edit_text(
            "❌ Ошибка сервиса распознавания речи. Попробуйте позже."
        )
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке голосового сообщения."
        )


def main() -> None:
    """Start the bot."""
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("❌ Ошибка: Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")
        print("Создайте файл .env и добавьте туда токен бота:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return

    # Create application
    application = Application.builder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text))
    application.add_handler(MessageHandler(filters.PHOTO, translate_photo))
    application.add_handler(MessageHandler(filters.VOICE, translate_voice))

    # Start bot
    logger.info("Starting bot...")
    print("✅ Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
