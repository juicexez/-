#!/usr/bin/env python3
"""
Telegram Bot - English to Russian Translator & Homework Helper
Supports text, image (OCR), and voice message translation
Also helps with English homework and exercises
"""

import os
import logging
import re
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Tesseract path for Windows (если Tesseract не в PATH)
# Раскомментируй и укажи свой путь, если нужно:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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

# Conversation states for homework helper
CHOOSING_TASK, WAITING_EXERCISE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Привет! Я многофункциональный бот для изучения английского языка!\n\n"
        "🔤 ПЕРЕВОДЧИК:\n"
        "📝 Переводить текстовые сообщения\n"
        "📷 Распознавать и переводить текст с фотографий\n"
        "🎤 Распознавать и переводить голосовые сообщения\n\n"
        "📚 ПОМОЩНИК С ДОМАШКОЙ:\n"
        "✏️ Грамматические упражнения\n"
        "📖 Проверка и объяснение ошибок\n"
        "✍️ Помощь с написанием эссе\n"
        "💬 Практика разговорных фраз\n"
        "📋 Словарные упражнения\n\n"
        "Команды:\n"
        "/start - Показать это сообщение\n"
        "/help - Справка\n"
        "/homework - Помощь с домашним заданием 📝\n"
        "/check - Проверить текст на ошибки ✅\n"
        "/explain - Объяснить грамматическое правило 📖"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 ПОЛНОЕ РУКОВОДСТВО\n\n"
        "🔤 ПЕРЕВОДЧИК:\n"
        "1️⃣ Текст - просто отправьте английский текст\n"
        "2️⃣ Фото - отправьте фото с текстом\n"
        "3️⃣ Голос - запишите голосовое на английском\n\n"
        "📚 ПОМОЩЬ С ДОМАШКОЙ:\n"
        "• /homework - выбрать тип задания\n"
        "• /check <текст> - проверить на ошибки\n"
        "• /explain <тема> - объяснить правило\n\n"
        "✏️ Типы заданий:\n"
        "- Грамматика (времена, формы глаголов)\n"
        "- Словарь (перевод, синонимы, примеры)\n"
        "- Эссе и сочинения (структура, проверка)\n"
        "- Упражнения на перевод\n"
        "- Заполнение пропусков\n"
        "- Разговорная практика (диалоги, фразы)\n\n"
        "💡 ПРИМЕРЫ:\n"
        "/homework - начать помощь с ДЗ\n"
        "/check She go to school - проверить\n"
        "/explain present perfect - объяснение\n\n"
        "📝 Просто отправьте текст для перевода или\n"
        "используйте команды для помощи с учебой!"
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


async def homework_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start homework help conversation."""
    keyboard = [
        [
            InlineKeyboardButton("✏️ Грамматика", callback_data='hw_grammar'),
            InlineKeyboardButton("📖 Словарь", callback_data='hw_vocabulary')
        ],
        [
            InlineKeyboardButton("✍️ Эссе/Сочинение", callback_data='hw_essay'),
            InlineKeyboardButton("🔄 Упражнение на перевод", callback_data='hw_translation')
        ],
        [
            InlineKeyboardButton("📝 Заполнить пропуски", callback_data='hw_fillblanks'),
            InlineKeyboardButton("💬 Разговорная практика", callback_data='hw_speaking')
        ],
        [
            InlineKeyboardButton("❓ Другое задание", callback_data='hw_other')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📚 Помощь с домашним заданием по английскому\n\n"
        "Выберите тип задания, с которым нужна помощь:",
        reply_markup=reply_markup
    )
    return CHOOSING_TASK


async def homework_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle homework type selection."""
    query = update.callback_query
    await query.answer()

    task_type = query.data

    instructions = {
        'hw_grammar': (
            "✏️ Помощь с грамматикой\n\n"
            "Отправьте мне:\n"
            "• Грамматическое правило для объяснения\n"
            "• Упражнение для выполнения\n"
            "• Предложение для проверки\n\n"
            "Примеры:\n"
            "- Объясни Present Perfect\n"
            "- Choose: He (go/goes/went) to school yesterday\n"
            "- She have been there (проверь на ошибки)"
        ),
        'hw_vocabulary': (
            "📖 Помощь со словами\n\n"
            "Отправьте мне:\n"
            "• Слово для перевода и примеров\n"
            "• Список слов для изучения\n"
            "• Упражнение на словарный запас\n\n"
            "Примеры:\n"
            "- Что значит 'magnificent'?\n"
            "- Синонимы слова 'beautiful'\n"
            "- Примеры использования 'however'"
        ),
        'hw_essay': (
            "✍️ Помощь с эссе/сочинением\n\n"
            "Отправьте мне:\n"
            "• Тему эссе для плана\n"
            "• Ваш текст для проверки\n"
            "• Вопрос по структуре\n\n"
            "Примеры:\n"
            "- Помоги написать эссе про мою семью\n"
            "- Проверь мое эссе: [ваш текст]\n"
            "- Как начать эссе про каникулы?"
        ),
        'hw_translation': (
            "🔄 Упражнение на перевод\n\n"
            "Отправьте:\n"
            "• Текст для перевода с объяснением\n"
            "• Проверку вашего перевода\n\n"
            "Примеры:\n"
            "- Переведи и объясни: Я хожу в школу каждый день\n"
            "- Правильно ли: I go to school everyday?"
        ),
        'hw_fillblanks': (
            "📝 Заполнить пропуски\n\n"
            "Отправьте упражнение с пропусками\n"
            "Используйте ___ для обозначения пропусков\n\n"
            "Пример:\n"
            "She ___ (to go) to the park yesterday.\n"
            "I ___ (to be) a student."
        ),
        'hw_speaking': (
            "💬 Разговорная практика\n\n"
            "Отправьте:\n"
            "• Ситуацию для диалога\n"
            "• Фразы для проверки\n"
            "• Тему для обсуждения\n\n"
            "Примеры:\n"
            "- Диалог в магазине\n"
            "- Как спросить дорогу?\n"
            "- Фразы для знакомства"
        ),
        'hw_other': (
            "❓ Другое задание\n\n"
            "Просто опишите или отправьте фото вашего задания,\n"
            "и я постараюсь помочь!"
        )
    }

    context.user_data['task_type'] = task_type
    await query.edit_message_text(instructions.get(task_type, instructions['hw_other']))
    return WAITING_EXERCISE


async def process_homework(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the homework exercise."""
    user_input = update.message.text
    task_type = context.user_data.get('task_type', 'hw_other')

    processing_msg = await update.message.reply_text("🔄 Обрабатываю задание...")

    try:
        result = await solve_exercise(user_input, task_type)
        await processing_msg.edit_text(result)
    except Exception as e:
        logger.error(f"Error processing homework: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке задания. Попробуйте переформулировать запрос."
        )

    return ConversationHandler.END


async def solve_exercise(text: str, task_type: str) -> str:
    """Solve different types of exercises."""

    # Grammar exercises
    if task_type == 'hw_grammar':
        return solve_grammar(text)

    # Vocabulary exercises
    elif task_type == 'hw_vocabulary':
        return solve_vocabulary(text)

    # Essay help
    elif task_type == 'hw_essay':
        return solve_essay(text)

    # Translation exercises
    elif task_type == 'hw_translation':
        return solve_translation(text)

    # Fill in the blanks
    elif task_type == 'hw_fillblanks':
        return solve_fill_blanks(text)

    # Speaking practice
    elif task_type == 'hw_speaking':
        return solve_speaking(text)

    # Other
    else:
        return solve_general(text)


def solve_grammar(text: str) -> str:
    """Help with grammar exercises."""
    text_lower = text.lower()

    # Detect exercise type
    if 'choose' in text_lower or '/' in text:
        # Multiple choice exercise
        return solve_multiple_choice(text)

    # Check for tense questions
    tenses = {
        'present simple': 'Present Simple используется для регулярных действий и фактов.\nФормула: Subject + V1/Vs\nПример: I work. She works.',
        'present continuous': 'Present Continuous для действий происходящих сейчас.\nФормула: Subject + am/is/are + Ving\nПример: I am working now.',
        'present perfect': 'Present Perfect для действий, связанных с настоящим.\nФормула: Subject + have/has + V3\nПример: I have finished my homework.',
        'past simple': 'Past Simple для действий в прошлом.\nФормула: Subject + V2\nПример: I worked yesterday.',
        'past continuous': 'Past Continuous для длительных действий в прошлом.\nФормула: Subject + was/were + Ving\nПример: I was working at 5 PM.',
        'future simple': 'Future Simple для будущих действий.\nФормула: Subject + will + V1\nПример: I will work tomorrow.',
    }

    for tense, explanation in tenses.items():
        if tense in text_lower:
            return f"📖 {tense.upper()}\n\n{explanation}\n\n💡 Нужна помощь с упражнением? Пришлите конкретное задание!"

    # General grammar help
    return (
        "✏️ Помощь с грамматикой\n\n"
        f"Ваш запрос: {text}\n\n"
        "💡 Для лучшей помощи:\n"
        "- Укажите конкретное правило\n"
        "- Отправьте упражнение с вариантами ответов\n"
        "- Напишите предложение для проверки\n\n"
        "Пример: Choose: She (go/goes/went) to school yesterday"
    )


def solve_multiple_choice(text: str) -> str:
    """Solve multiple choice grammar exercises."""
    # Extract options in parentheses
    match = re.search(r'\((.*?)\)', text)
    if not match:
        return "❌ Не могу найти варианты ответов. Укажите их в скобках: (go/goes/went)"

    options = match.group(1).split('/')
    text_before = text[:match.start()].lower()

    # Detect verb forms
    answer = None
    explanation = ""

    # Check for time markers
    if any(word in text_before for word in ['yesterday', 'last', 'ago']):
        # Past tense
        for opt in options:
            if opt.endswith('ed') or opt in ['went', 'was', 'were', 'had', 'did']:
                answer = opt
                explanation = "Используется Past Simple, так как есть указание на прошлое (yesterday/last/ago)"
                break

    elif any(word in text for word in ['tomorrow', 'next', 'will']):
        # Future
        for opt in options:
            if not opt.endswith('s') and not opt.endswith('ed'):
                answer = opt
                explanation = "Используется Future Simple (will + V1) или Present Simple для будущего"
                break

    elif any(word in text for word in ['now', 'at the moment', 'currently']):
        # Present Continuous
        for opt in options:
            if opt.endswith('ing'):
                answer = opt
                explanation = "Используется Present Continuous для действия происходящего сейчас"
                break

    elif any(word in text for word in ['he', 'she', 'it']) and not any(word in text for word in ['they', 'i', 'we', 'you']):
        # 3rd person singular
        for opt in options:
            if opt.endswith('s') and not opt.endswith('es'):
                answer = opt
                explanation = "Для he/she/it в Present Simple добавляется -s"
                break

    if not answer:
        answer = options[0]
        explanation = "Рекомендуемый вариант (проверьте контекст)"

    result = (
        f"✅ Ответ: {answer}\n\n"
        f"📖 Объяснение:\n{explanation}\n\n"
        f"📝 Полное предложение:\n{text[:match.start()]}{answer}{text[match.end():]}"
    )

    return result


def solve_vocabulary(text: str) -> str:
    """Help with vocabulary."""
    # Translate and give examples
    try:
        translation = translator.translate(text)
        result = (
            f"📖 Слово/фраза: {text}\n\n"
            f"🔤 Перевод: {translation}\n\n"
            f"💡 Для получения примеров использования, синонимов или объяснения - "
            f"напишите 'примеры {text}' или 'синонимы {text}'"
        )
        return result
    except:
        return "❌ Не удалось обработать запрос. Попробуйте переформулировать."


def solve_essay(text: str) -> str:
    """Help with essay writing."""
    if len(text.split()) < 5:
        # Topic provided, give structure
        return (
            f"✍️ Структура эссе на тему: {text}\n\n"
            f"📋 Рекомендуемая структура:\n\n"
            f"1️⃣ ВВЕДЕНИЕ (Introduction)\n"
            f"- Представьте тему\n"
            f"- Напишите тезис (главную мысль)\n\n"
            f"2️⃣ ОСНОВНАЯ ЧАСТЬ (Body)\n"
            f"- Параграф 1: Первый аргумент + примеры\n"
            f"- Параграф 2: Второй аргумент + примеры\n"
            f"- Параграф 3: Третий аргумент (опционально)\n\n"
            f"3️⃣ ЗАКЛЮЧЕНИЕ (Conclusion)\n"
            f"- Обобщите главные мысли\n"
            f"- Завершающее предложение\n\n"
            f"💡 Полезные фразы:\n"
            f"- To begin with... (Для начала...)\n"
            f"- Furthermore... (Более того...)\n"
            f"- In conclusion... (В заключение...)\n"
            f"- In my opinion... (По моему мнению...)"
        )
    else:
        # Essay text provided, check it
        return check_text(text, detailed=True)


def solve_translation(text: str) -> str:
    """Help with translation exercises."""
    try:
        # Translate to English
        translator_ru_en = GoogleTranslator(source='ru', target='en')
        english = translator_ru_en.translate(text)

        # Translate back for comparison
        russian = translator.translate(english)

        result = (
            f"🔄 ПЕРЕВОД С ОБЪЯСНЕНИЕМ\n\n"
            f"📝 Исходный текст:\n{text}\n\n"
            f"✅ Правильный перевод:\n{english}\n\n"
            f"🔍 Проверка (обратный перевод):\n{russian}\n\n"
            f"💡 Совет: Сравните обратный перевод с оригиналом, "
            f"чтобы убедиться в точности."
        )
        return result
    except:
        return "❌ Ошибка при переводе. Проверьте текст и попробуйте снова."


def solve_fill_blanks(text: str) -> str:
    """Help with fill-in-the-blanks exercises."""
    # Find all blanks marked with ___ or (verb)
    blanks = re.findall(r'___|\([^)]+\)', text)

    if not blanks:
        return (
            "❌ Не найдены пропуски!\n\n"
            "Используйте ___ или (подсказка) для обозначения пропусков\n\n"
            "Пример:\nShe ___ (go) to school yesterday."
        )

    result = "📝 РЕШЕНИЕ УПРАЖНЕНИЯ\n\n"
    result += f"Задание:\n{text}\n\n"
    result += "Ответы:\n\n"

    # Simple logic for common patterns
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        if '___' in line or '(' in line:
            answer = analyze_blank_context(line)
            result += f"{i}. {answer}\n"

    result += "\n💡 Проверьте согласование времен и правильность форм глаголов!"

    return result


def analyze_blank_context(line: str) -> str:
    """Analyze context to suggest answer for blank."""
    line_lower = line.lower()

    # Check for verb in parentheses
    verb_match = re.search(r'\(([^)]+)\)', line)
    if verb_match:
        verb = verb_match.group(1).replace('to ', '')

        # Detect tense from context
        if any(word in line_lower for word in ['yesterday', 'last', 'ago']):
            if verb == 'be':
                return f"was/were (Past Simple)"
            elif verb == 'go':
                return "went (Past Simple)"
            else:
                return f"{verb}ed (Past Simple)"

        elif any(word in line_lower for word in ['now', 'currently']):
            return f"am/is/are {verb}ing (Present Continuous)"

        elif any(word in line_lower for word in ['he ', 'she ', 'it ']):
            return f"{verb}s (Present Simple, 3rd person)"

        else:
            return f"{verb} (base form)"

    return "проверьте контекст"


def solve_speaking(text: str) -> str:
    """Help with speaking practice."""
    text_lower = text.lower()

    situations = {
        'магазин': (
            "🛍️ ДИАЛОГ В МАГАЗИНЕ\n\n"
            "👤 Покупатель:\n"
            "- Excuse me, how much is this? (Извините, сколько это стоит?)\n"
            "- Can I try this on? (Могу я это примерить?)\n"
            "- Do you have this in a different size/color? (Есть ли это другого размера/цвета?)\n"
            "- I'll take it. (Я возьму это)\n\n"
            "👔 Продавец:\n"
            "- Can I help you? (Чем могу помочь?)\n"
            "- What size do you need? (Какой размер вам нужен?)\n"
            "- The fitting room is over there (Примерочная вон там)\n"
            "- That'll be $50 (С вас 50 долларов)"
        ),
        'дорог': (
            "🗺️ КАК СПРОСИТЬ ДОРОГУ\n\n"
            "❓ Вопросы:\n"
            "- Excuse me, how do I get to...? (Как пройти к...?)\n"
            "- Where is the nearest...? (Где ближайший...?)\n"
            "- Is it far from here? (Это далеко отсюда?)\n"
            "- Can you show me on the map? (Можете показать на карте?)\n\n"
            "➡️ Направления:\n"
            "- Go straight (Идите прямо)\n"
            "- Turn left/right (Поверните налево/направо)\n"
            "- It's on your left/right (Это слева/справа от вас)\n"
            "- Take the first/second street (Сверните на первую/вторую улицу)"
        ),
        'знаком': (
            "👋 ФРАЗЫ ДЛЯ ЗНАКОМСТВА\n\n"
            "Начало разговора:\n"
            "- Hi! My name is... What's your name? (Привет! Меня зовут... Как тебя зовут?)\n"
            "- Nice to meet you! (Приятно познакомиться!)\n"
            "- Where are you from? (Откуда ты?)\n\n"
            "Общие вопросы:\n"
            "- What do you do? (Чем ты занимаешься?)\n"
            "- What are your hobbies? (Какие у тебя хобби?)\n"
            "- Do you like...? (Тебе нравится...?)\n\n"
            "Завершение:\n"
            "- It was nice talking to you! (Было приятно поговорить!)\n"
            "- See you later! (Увидимся!)"
        )
    }

    for key, dialog in situations.items():
        if key in text_lower:
            return dialog

    # General speaking help
    return (
        "💬 РАЗГОВОРНАЯ ПРАКТИКА\n\n"
        "Популярные темы:\n"
        "- Магазин (напишите 'магазин')\n"
        "- Спросить дорогу (напишите 'дорога')\n"
        "- Знакомство (напишите 'знакомство')\n\n"
        "Или опишите ситуацию, и я помогу с фразами!"
    )


def solve_general(text: str) -> str:
    """Handle general homework questions."""
    return (
        "📚 ОБЩАЯ ПОМОЩЬ\n\n"
        f"Ваш вопрос:\n{text}\n\n"
        "💡 Я могу помочь с:\n"
        "- Переводом текста\n"
        "- Объяснением слов и фраз\n"
        "- Грамматическими правилами\n"
        "- Проверкой текста\n\n"
        "Используйте /homework для выбора конкретного типа задания!"
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check text for errors."""
    if context.args:
        text = ' '.join(context.args)
    else:
        await update.message.reply_text(
            "Используйте: /check <ваш текст>\n\n"
            "Пример: /check She go to school yesterday"
        )
        return

    result = check_text(text)
    await update.message.reply_text(result)


def check_text(text: str, detailed: bool = False) -> str:
    """Check text for common errors."""
    errors = []
    suggestions = []

    # Check for common mistakes
    # Subject-verb agreement
    patterns = [
        (r'\b(he|she|it)\s+\w+(?<!s)\b(?!\s+(is|was|has|does))', 'Возможно, нужно добавить -s к глаголу (he/she/it + Vs)'),
        (r'\b(I|you|we|they)\s+\w+s\b', 'Возможно, не нужно -s (I/you/we/they + V)'),
    ]

    for pattern, message in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(message)

    # Check for double spaces
    if '  ' in text:
        errors.append('Найдены двойные пробелы')

    # Check capitalization
    if text and not text[0].isupper():
        errors.append('Предложение должно начинаться с заглавной буквы')

    # Check ending punctuation
    if text and text[-1] not in '.!?':
        errors.append('Не хватает знака препинания в конце')

    # Generate result
    if errors:
        result = "✅ ПРОВЕРКА ТЕКСТА\n\n"
        result += f"Ваш текст:\n{text}\n\n"
        result += "⚠️ Найденные проблемы:\n"
        for i, error in enumerate(errors, 1):
            result += f"{i}. {error}\n"
        result += "\n💡 Исправьте и отправьте снова для повторной проверки!"
    else:
        result = f"✅ Отлично! Явных ошибок не найдено.\n\nВаш текст:\n{text}"

    return result


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain grammar rule."""
    if not context.args:
        await update.message.reply_text(
            "📖 Объяснение грамматических правил\n\n"
            "Используйте: /explain <тема>\n\n"
            "Примеры:\n"
            "/explain present perfect\n"
            "/explain articles\n"
            "/explain prepositions"
        )
        return

    topic = ' '.join(context.args).lower()
    explanation = explain_grammar_topic(topic)
    await update.message.reply_text(explanation)


def explain_grammar_topic(topic: str) -> str:
    """Explain a grammar topic."""
    topics = {
        'present perfect': (
            "📖 PRESENT PERFECT\n\n"
            "🎯 Формула: have/has + V3 (Past Participle)\n\n"
            "✅ Использование:\n"
            "1. Действие в прошлом, результат в настоящем\n"
            "   I have finished my homework (Я закончил домашку - и она готова)\n\n"
            "2. Опыт в жизни\n"
            "   I have been to London (Я был в Лондоне)\n\n"
            "3. Период времени от прошлого до настоящего\n"
            "   I have lived here for 5 years\n\n"
            "⏰ Маркеры времени:\n"
            "already, just, yet, ever, never, for, since, recently\n\n"
            "❌ НЕ используется с точным временем в прошлом:\n"
            "✗ I have seen him yesterday\n"
            "✓ I saw him yesterday"
        ),
        'articles': (
            "📖 АРТИКЛИ (A / AN / THE)\n\n"
            "🔹 A / AN (неопределенный артикль)\n"
            "- Используется с исчисляемыми в единственном числе\n"
            "- A: перед согласными (a book, a car)\n"
            "- AN: перед гласными (an apple, an hour)\n\n"
            "🔹 THE (определенный артикль)\n"
            "- Конкретный предмет: the book (та самая книга)\n"
            "- Уникальные вещи: the sun, the moon\n"
            "- Превосходная степень: the best\n\n"
            "🔹 Без артикля:\n"
            "- Множественное число в общем смысле: Books are useful\n"
            "- Неисчисляемые: Water is important\n"
            "- Имена, города: Moscow, John"
        ),
        'prepositions': (
            "📖 ПРЕДЛОГИ (PREPOSITIONS)\n\n"
            "📍 Предлоги места:\n"
            "- in: внутри (in the room, in Moscow)\n"
            "- on: на поверхности (on the table)\n"
            "- at: в точке (at school, at home)\n"
            "- under: под (under the table)\n"
            "- next to: рядом с\n\n"
            "⏰ Предлоги времени:\n"
            "- in: месяцы, годы, части дня (in May, in 2023, in the morning)\n"
            "- on: дни, даты (on Monday, on July 5th)\n"
            "- at: точное время (at 5 o'clock, at night)\n\n"
            "💡 Частые ошибки:\n"
            "✓ at night (НЕ in the night)\n"
            "✓ on Monday (НЕ in Monday)\n"
            "✓ in the morning (НЕ at the morning)"
        ),
    }

    for key, explanation in topics.items():
        if key in topic:
            return explanation

    return (
        f"📖 Тема: {topic}\n\n"
        "Доступные темы для объяснения:\n"
        "- present perfect\n"
        "- articles (a/an/the)\n"
        "- prepositions\n"
        "- past simple\n"
        "- future simple\n\n"
        "Или используйте /homework для интерактивной помощи!"
    )


async def cancel_homework(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel homework conversation."""
    await update.message.reply_text(
        "❌ Помощь с домашкой отменена.\n\nИспользуйте /homework для новой помощи!"
    )
    return ConversationHandler.END


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

    # Homework conversation handler
    homework_conv = ConversationHandler(
        entry_points=[CommandHandler('homework', homework_command)],
        states={
            CHOOSING_TASK: [CallbackQueryHandler(homework_callback)],
            WAITING_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_homework)]
        },
        fallbacks=[CommandHandler('cancel', cancel_homework)]
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("explain", explain_command))
    application.add_handler(homework_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text))
    application.add_handler(MessageHandler(filters.PHOTO, translate_photo))
    application.add_handler(MessageHandler(filters.VOICE, translate_voice))

    # Start bot
    logger.info("Starting bot...")
    print("✅ Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
