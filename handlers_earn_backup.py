import random
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import database
import handlers_menu
from openai import OpenAI

# Configure Groq AI
client = OpenAI(
    api_key=os.getenv('GROQ_API_KEY'),
    base_url="https://api.groq.com/openai/v1"
)

# States
CHOOSING_SUBJECT, ANSWERING_PROBLEM = range(2)

# AI Question Generator
async def generate_question(subject_type, age):
    """Generate a unique question using AI based on subject and age"""
    
    prompts = {
        'math': f"Создай математический пример для ребенка {age} лет. Формат ответа (две строки):\nВОПРОС: [пример]\nОТВЕТ: [только число]",
        'logic': f"Придумай короткую логическую загадку для ребенка {age} лет. Формат ответа (две строки):\nВОПРОС: [загадка]\nОТВЕТ: [ответ одним словом]",
        'world': f"Задай вопрос об окружающем мире для ребенка {age} лет. Формат ответа (две строки):\nВОПРОС: [вопрос]\nОТВЕТ: [короткий ответ]",
        'capitals': "Выбери случайную страну и задай вопрос о её столице. Формат ответа (две строки):\nВОПРОС: [Столица какой страны?]\nОТВЕТ: [город]",
        'flags': "Опиши флаг случайной страны (цвета, расположение). Формат ответа (две строки):\nВОПРОС: [описание флага]\nОТВЕТ: [страна]",
        'history': "Задай исторический вопрос о важной дате. Формат ответа (две строки):\nВОПРОС: [вопрос о годе события]\nОТВЕТ: [год]",
        'science': "Задай научный вопрос (биология, химия, физика). Формат ответа (две строки):\nВОПРОС: [научный вопрос]\nОТВЕТ: [краткий ответ]"
    }
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Ты создаешь образовательные вопросы для детей. Отвечай СТРОГО в заданном формате. Вопросы должны быть интересными и разнообразными."},
                {"role": "user", "content": prompts[subject_type]}
            ],
            temperature=0.9,  # High temperature for variety
            max_tokens=150
        )
        
        result = response.choices[0].message.content.strip()
        lines = result.split('\n')
        
        # Parse question and answer
        question = ""
        answer = ""
        for line in lines:
            if "ВОПРОС:" in line:
                question = line.replace("ВОПРОС:", "").strip()
            elif "ОТВЕТ:" in line:
                answer = line.replace("ОТВЕТ:", "").strip()
        
        if question and answer:
            return question, answer.lower()
        else:
            # Fallback if parsing failed
            return None, None
            
    except Exception as e:
        print(f"Question generation error: {e}")
        return None, None

async def start_earning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get user's purchased games
    user = database.get_user(update.effective_user.id)
    user_id = user[0]
    purchased_games = database.get_purchased_games(user_id)
    
    # Build keyboard with purchased games
    keyboard = [['🔢 Математика', '🧩 Логика'], ['🌍 Окружающий мир']]
    
    # Add purchased premium games
    if 'capitals' in purchased_games:
        keyboard.append(['🌍 Угадай столицу'])
    if 'flags' in purchased_games:
        keyboard.append(['🏴 Угадай флаг'])
    if 'history' in purchased_games:
        keyboard.append(['🎭 Исторические даты'])
    if 'science' in purchased_games:
        keyboard.append(['🧬 Наука и технологии'])
    
    keyboard.append(['🔙 Назад'])
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите предмет для заработка:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CHOOSING_SUBJECT

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text
    
    if subject == '🔙 Назад':
        await handlers_menu.show_main_menu(update, context)
        return ConversationHandler.END
        
    user = database.get_user(update.effective_user.id)
    age = user[3]
    
    # Generate questions using AI
    if subject == '🔢 Математика':
            op = random.choice(['+', '-'])
            if op == '-' and a < b: a, b = b, a
        elif age < 12:
            a, b = random.randint(10, 50), random.randint(2, 10)
            op = random.choice(['+', '-', '*'])
        else:
            a, b = random.randint(20, 100), random.randint(5, 20)
            op = random.choice(['+', '-', '*', '/'])
            if op == '/': a = a * b # Ensure integer division
            
        if op == '+': ans = a + b
        elif op == '-': ans = a - b
        elif op == '*': ans = a * b
        elif op == '/': ans = a // b
        
        context.user_data['ans'] = str(ans)
        context.user_data['reward'] = random.randint(15, 30)
        question = f"{a} {op} {b} = ?"
        context.user_data['question'] = question
        
    elif subject == '🧩 Логика':
        puzzles = [
            ("Что можно сломать, даже если не трогать?", "обещание"),
            ("Чем больше из нее берешь, тем больше она становится?", "яма"),
            ("В комнате горело 5 свечей. 2 погасли. Сколько осталось?", "2"),
            ("Шли два отца и два сына, нашли три апельсина. Стали делить — всем по одному досталось. Как это могло быть?", "дед отец сын"),
            ("Что становится больше, когда его перевернешь вверх ногами?", "6"),
            ("Что тяжелее: килограмм ваты или килограмм железа?", "одинаково"),
        ]
        
        # Track asked questions to avoid repeats
        if 'asked_logic' not in context.user_data:
            context.user_data['asked_logic'] = set()
        
        # Filter out already asked questions
        available = [p for p in puzzles if p[0] not in context.user_data['asked_logic']]
        
        # If all questions were asked, reset
        if not available:
            context.user_data['asked_logic'] = set()
            available = puzzles
        
        q, a = random.choice(available)
        context.user_data['asked_logic'].add(q)
        context.user_data['ans'] = a
        context.user_data['reward'] = random.randint(20, 40)
        question = f"Загадка:\n{q}"
        context.user_data['question'] = question

    elif subject == '🌍 Окружающий мир':
        # Age-based question pools
        if age < 8:
            questions = [
                ("Сколько ног у паука?", "8"),
                ("Какого цвета солнце?", "желтое"),
                ("Сколько дней в неделе?", "7"),
                ("Какое животное дает молоко?", "корова"),
            ]
        elif age < 12:
            questions = [
                ("Сколько планет в Солнечной системе?", "8"),
                ("Самое глубокое озеро в мире?", "байкал"),
                ("Какой газ мы выдыхаем?", "углекислый"),
                ("Столица России?", "москва"),
                ("Сколько континентов на Земле?", "6"),
            ]
        else:
            questions = [
                ("Сколько планет в Солнечной системе?", "8"),
                ("Самое глубокое озеро в мире?", "байкал"),
                ("Какой газ необходим для дыхания?", "кислород"),
                ("В каком году началась Вторая мировая война?", "1939"),
                ("Сколько хромосом у человека?", "46"),
            ]
        
        # Track asked questions to avoid repeats
        if 'asked_questions' not in context.user_data:
            context.user_data['asked_questions'] = set()
        
        # Filter out already asked questions
        available = [q for q in questions if q[0] not in context.user_data['asked_questions']]
        
        # If all questions were asked, reset
        if not available:
            context.user_data['asked_questions'] = set()
            available = questions
        
        q, a = random.choice(available)
        context.user_data['asked_questions'].add(q)
        context.user_data['ans'] = a.lower()
        context.user_data['reward'] = random.randint(10, 20)
        question = f"Вопрос:\n{q}"
        context.user_data['question'] = question
    
    # Premium Games (2x-3x rewards)
    elif subject == '🌍 Угадай столицу':
        capitals = [
            ("Франция", "париж"), ("Германия", "берлин"), ("Италия", "рим"),
            ("Испания", "мадрид"), ("Япония", "токио"), ("Китай", "пекин"),
            ("Бразилия", "бразилиа"), ("Канада", "оттава"), ("Австралия", "канберра"),
            ("Египет", "каир"), ("Турция", "анкара"), ("Польша", "варшава")
        ]
        q, a = random.choice(capitals)
        context.user_data['ans'] = a.lower()
        context.user_data['reward'] = random.randint(20, 40)  # 2x reward
        question = f"Столица:\n{q}"
        context.user_data['question'] = question
    
    elif subject == '🏴 Угадай флаг':
        flags = [
            ("Красный, белый, синий (горизонтально)", "россия"),
            ("Красный с желтыми звездами", "китай"),
            ("Красный, белый (горизонтально)", "польша"),
            ("Синий, желтый (горизонтально)", "украина"),
            ("Зеленый, белый, красный (вертикально)", "италия"),
            ("Красный с белым крестом", "швейцария")
        ]
        q, a = random.choice(flags)
        context.user_data['ans'] = a.lower()
        context.user_data['reward'] = random.randint(20, 40)  # 2x reward
        question = f"Флаг:\n{q}"
        context.user_data['question'] = question
    
    elif subject == '🎭 Исторические даты':
        history = [
            ("В каком году началась Вторая мировая война?", "1939"),
            ("В каком году человек впервые высадился на Луну?", "1969"),
            ("В каком году пала Берлинская стена?", "1989"),
            ("В каком году был основан СССР?", "1922"),
            ("В каком году открыли Америку?", "1492")
        ]
        q, a = random.choice(history)
        context.user_data['ans'] = a
        context.user_data['reward'] = random.randint(30, 60)  # 3x reward
        question = f"История:\n{q}"
        context.user_data['question'] = question
    
    elif subject == '🧬 Наука и технологии':
        science = [
            ("Сколько хромосом у человека?", "46"),
            ("Какая планета самая большая в Солнечной системе?", "юпитер"),
            ("Кто изобрел лампочку?", "эдисон"),
            ("Скорость света в км/с (округленно)?", "300000"),
            ("Химический символ золота?", "au")
        ]
        q, a = random.choice(science)
        context.user_data['ans'] = a.lower()
        context.user_data['reward'] = random.randint(30, 60)  # 3x reward
        question = f"Наука:\n{q}"
        context.user_data['question'] = question
        
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите предмет из меню.")
        return CHOOSING_SUBJECT

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"❓ {question}\n\n(Награда: {context.user_data['reward']} монет)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ANSWERING_PROBLEM

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ans = update.message.text.strip()
    correct_ans = str(context.user_data.get('ans'))
    reward = context.user_data.get('reward')
    question = context.user_data.get('question', '')
    
    # Use AI to check the answer
    prompt = f"""Ты проверяешь ответ ученика на вопрос.

Вопрос: {question}
Правильный ответ: {correct_ans}
Ответ ученика: {user_ans}

КРИТИЧЕСКИ ВАЖНО:
1. Проверяй ТОЛЬКО СМЫСЛ! Опечатки, грамматика, лишние буквы — ИГНОРИРУЙ ПОЛНОСТЬЮ!
2. Если ученик имел в виду правильный ответ (даже с опечатками) — это ПРАВИЛЬНО!
3. НИКОГДА не упоминай опечатки, грамматику или написание в объяснении!
4. Давай ТОЛЬКО полезную информацию и факты!

Примеры:
- "обешвние" = "обещание" → ПРАВИЛЬНО (опечатка не важна)
- "углекисли" = "углекислый" → ПРАВИЛЬНО (опечатка не важна)
- "семь" вместо "восемь" → НЕПРАВИЛЬНО (неверный смысл)

Ответь СТРОГО в формате (две строки):
ПРАВИЛЬНО или НЕПРАВИЛЬНО
Интересный факт или совет (БЕЗ упоминания опечаток!). Например: "Обещание легко сломать словами, но трудно восстановить доверие" или "В Солнечной системе 8 планет: Меркурий, Венера, Земля, Марс, Юпитер, Сатурн, Уран, Нептун"

Пиши на русском языке."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Current working model
            messages=[
                {"role": "system", "content": "Ты строгий, но справедливый учитель. Отвечай кратко и по делу на русском языке."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        ai_response = response.choices[0].message.content.strip()
        
        # Simple parsing - check first line
        first_line = ai_response.split('\n')[0].lower()
        is_correct = "правильно" in first_line and "неправильно" not in first_line
        
        # Get explanation (everything after first line)
        lines = ai_response.split('\n')
        explanation = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
        
        if is_correct:
            database.update_balance(update.effective_user.id, reward)
            message = f"✅ Правильно! Ты заработал {reward} монет."
            if explanation:
                message += f"\n\n💡 {explanation}"
        else:
            message = f"❌ Неверно."
            if explanation:
                message += f"\n\n💡 {explanation}"
            else:
                message += f"\n\n💡 Правильный ответ: {correct_ans}"
            
    except Exception as e:
        # Fallback to simple comparison if AI fails
        print(f"AI Error: {e}")
        if user_ans.lower() == correct_ans.lower():
            database.update_balance(update.effective_user.id, reward)
            message = f"✅ Правильно! Ты заработал {reward} монет."
        else:
            message = f"❌ Неверно. Правильный ответ: {correct_ans}."
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )
    
    # Return to subject selection instead of main menu
    keyboard = [['🔢 Математика', '🧩 Логика'], ['🌍 Окружающий мир', '🔙 Назад']]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите предмет для заработка:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CHOOSING_SUBJECT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отменено.")
    await handlers_menu.show_main_menu(update, context)
    return ConversationHandler.END

def get_earn_conv_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^💰 Фин-Заработок$'), start_earning)],
        states={
            CHOOSING_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_subject)],
            ANSWERING_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
