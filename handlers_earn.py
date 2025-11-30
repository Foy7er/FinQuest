import random
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import database
import handlers_menu

# Try to import OpenAI for Groq
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv('GROQ_API_KEY'),
        base_url="https://api.groq.com/openai/v1"
    )
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False
    print("AI not available, using simple answer checking")

# States
CHOOSING_SUBJECT, ANSWERING_PROBLEM = range(2)

async def generate_question(subject_type, age):
    """Generate question using AI"""
    if not AI_AVAILABLE:
        print("AI not available for question generation")
        return None, None
    
    print(f"Generating {subject_type} question for age {age}...")
    
    prompts = {
        'math': f"""Создай математический пример для ребенка {age} лет.

ФОРМАТ (2 строки):
ВОПРОС: [пример]
ОТВЕТ: [число]

ПРИМЕРЫ ПРАВИЛЬНОЙ ГРАММАТИКИ:
ВОПРОС: Сколько будет 5 + 3?
ОТВЕТ: 8

ВОПРОС: 12 - 4 = ?
ОТВЕТ: 8""",
        
        'logic': f"""Создай простую загадку для ребенка {age} лет.

ПРАВИЛА:
- ТОЛЬКО русские слова
- Грамматически верно
- Простая формулировка

ФОРМАТ (2 строки):
ВОПРОС: [загадка]
ОТВЕТ: [слово]

ПРИМЕРЫ ХОРОШИХ ЗАГАДОК:
ВОПРОС: Что можно сломать, даже не трогая?
ОТВЕТ: обещание

ВОПРОС: Чем больше из неё берёшь, тем больше она становится?
ОТВЕТ: яма""",
        
        'world': f"""Создай простой вопрос о мире для ребенка {age} лет.

ПРАВИЛА:
- ТОЛЬКО русские слова (0% английских!)
- Грамматически верно
- Простой вопрос

ФОРМАТ (2 строки):
ВОПРОС: [вопрос]
ОТВЕТ: [слово]

ПРИМЕРЫ:
ВОПРОС: Какой спутник у Земли?
ОТВЕТ: Луна

ВОПРОС: Самое глубокое озеро в мире?
ОТВЕТ: Байкал"""
    }
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Создаёшь вопросы на ЧИСТОМ русском языке. ЗАПРЕЩЕНЫ английские буквы/слова. Грамматика важна. 2 строки."},
                {"role": "user", "content": prompts[subject_type]}
            ],
            temperature=0.6,
            max_tokens=80
        )
        
        result = response.choices[0].message.content.strip()
        print(f"AI response: {result}")
        
        # Parse with fallback
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        question = ""
        answer = ""
        
        for line in lines:
            if line.upper().startswith("ВОПРОС:"):
                question = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.upper().startswith("ОТВЕТ:"):
                answer = line.split(":", 1)[1].strip() if ":" in line else ""
        
        if question and answer:
            print(f"✅ Generated Q: {question}, A: {answer}")
            return question, answer.lower()
        else:
            print(f"❌ Failed to parse. Using fallback.")
            return None, None
    except Exception as e:
        print(f"Question generation error: {e}")
        return None, None

async def start_earning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['🔢 Математика', '🧩 Логика'], ['🌍 Окружающий мир', '🔙 Назад']]
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
    age = user[9] if user and len(user) > 9 else 10
    
    # Try AI generation first
    q, a = None, None
    
    if subject == '🔢 Математика':
        q, a = await generate_question('math', age)
        reward = random.randint(15, 30)
        
        # Fallback to hardcoded
        if not q or not a:
            if age < 8:
                n1, n2 = random.randint(1, 10), random.randint(1, 10)
                op = random.choice(['+', '-'])
                if op == '-' and n1 < n2: n1, n2 = n2, n1
            elif age < 12:
                n1, n2 = random.randint(10, 50), random.randint(2, 10)
                op = random.choice(['+', '-', '*'])
            else:
                n1, n2 = random.randint(20, 100), random.randint(5, 20)
                op = random.choice(['+', '-', '*', '/'])
                if op == '/': n1 = n1 * n2
                
            if op == '+': ans = n1 + n2
            elif op == '-': ans = n1 - n2
            elif op == '*': ans = n1 * n2
            elif op == '/': ans = n1 // n2
            
            q = f"{n1} {op} {n2} = ?"
            a = str(ans)
        
    elif subject == '🧩 Логика':
        q, a = await generate_question('logic', age)
        reward = random.randint(20, 40)
        
        # Fallback
        if not q or not a:
            puzzles = [
                ("Что можно сломать, даже если не трогать?", "обещание"),
                ("Чем больше из нее берешь, тем больше она становится?", "яма"),
                ("В комнате горело 5 свечей. 2 погасли. Сколько осталось?", "2"),
            ]
            q, a = random.choice(puzzles)

    elif subject == '🌍 Окружающий мир':
        q, a = await generate_question('world', age)
        reward = random.randint(10, 20)
        
        # Fallback
        if not q or not a:
            questions = [
                ("Сколько планет в Солнечной системе?", "8"),
                ("Самое глубокое озеро в мире?", "байкал"),
                ("Какой газ мы выдыхаем?", "углекислый"),
            ]
            q, a = random.choice(questions)
        
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите предмет из меню.")
        return CHOOSING_SUBJECT

    context.user_data['ans'] = a
    context.user_data['reward'] = reward
    context.user_data['question'] = q

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"❓ {q}\n\n(Награда: {reward} монет)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ANSWERING_PROBLEM

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ans = update.message.text.strip()
    correct_ans = str(context.user_data.get('ans'))
    reward = context.user_data.get('reward')
    question = context.user_data.get('question', '')
    
    # Try AI checking first if available
    if AI_AVAILABLE:
        try:
            prompt = f"""Проверь ответ.

Вопрос: {question}
Правильный ответ: {correct_ans}
Ответ ученика: {user_ans}

ПРАВИЛА ПРОВЕРКИ:
✅ ПРИНИМАЙ: опечатки ("бойкал"="байкал"), разные падежи, числа словами
❌ ОТКЛОНЯЙ ВСЕГДА: "-", "?", "!", "не понял", "не знаю", "незнаю", "хз", любую бессмыслицу

ФОРМАТ ОТВЕТА (2-3 строки, БЕЗ английских слов!):
ПРАВИЛЬНО или НЕПРАВИЛЬНО
Факт про правильный ответ (ТОЛЬКО на русском!)
(если неверно) Правильный ответ: [ответ]

ПРИМЕРЫ:

Ответ "не понял" на любой вопрос:
НЕПРАВИЛЬНО
[Факт про правильный ответ]
Правильный ответ: [ответ]

Ответ "бойкал" на "Самое глубокое озеро?":
ПРАВИЛЬНО
Байкал - самое глубокое озеро, глубина 1642 метра."""

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Учитель. НЕ принимай 'не знаю','не понял','?','-'. Принимай опечатки. Пиши факты ТОЛЬКО на РУССКОМ языке. ЗАПРЕЩЕНЫ английские буквы."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05,
                max_tokens=85
            )
            
            ai_response = response.choices[0].message.content.strip()
            print(f"AI check response: {ai_response}")
            
            # Parse correctness
            response_lower = ai_response.lower()
            if "правильно" in response_lower:
                pos_correct = response_lower.find("правильно")
                pos_incorrect = response_lower.find("неправильно")
                is_correct = (pos_incorrect == -1) or (pos_correct < pos_incorrect)
            else:
                is_correct = False
            
            # AGGRESSIVE filtering - remove ALL service lines
            lines = ai_response.split('\n')
            clean_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                line_lower = line_stripped.lower()
                
                # Skip ALL service keywords
                skip_keywords = [
                    'правильно', 'неправильно',
                    'проверка', 'ответ ученика', 'ответ учащегося',
                    'вопрос:', 'ответ:', 'задача:', 'задание:'
                ]
                
                should_skip = False
                for keyword in skip_keywords:
                    if keyword in line_lower and len(line_stripped) < 60:  # Short lines with keywords = service lines
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # If CORRECT answer, skip "правильный ответ:"
                if is_correct and 'правильный ответ' in line_lower:
                    continue
                
                # Add meaningful lines
                if line_stripped and len(line_stripped) > 3:
                    clean_lines.append(line_stripped)
            
            explanation = '\n'.join(clean_lines).strip()
            
            if is_correct:
                database.update_balance(update.effective_user.id, reward)
                message = f"✅ Правильно! Ты заработал {reward} монет."
                if explanation:
                    message += f"\n\n💡 {explanation}"
            else:
                message = f"❌ Неверно."
                if explanation:
                    message += f"\n\n💡 {explanation}"
                if "правильный ответ:" not in explanation.lower():
                    message += f"\n\n💡 Правильный ответ: {correct_ans}"
                    
        except Exception as e:
            print(f"AI Error: {e}")
            if user_ans.lower().strip() == correct_ans.lower().strip():
                database.update_balance(update.effective_user.id, reward)
                message = f"✅ Правильно! Ты заработал {reward} монет."
            else:
                message = f"❌ Неверно. Правильный ответ: {correct_ans}."
    else:
        if user_ans.lower().strip() == correct_ans.lower().strip():
            database.update_balance(update.effective_user.id, reward)
            message = f"✅ Правильно! Ты заработал {reward} монет."
        else:
            message = f"❌ Неверно. Правильный ответ: {correct_ans}."
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    await handlers_menu.show_main_menu(update, context)
    return ConversationHandler.END

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
