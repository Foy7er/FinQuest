from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import database
import handlers_menu

# States for the registration conversation
CHOOSING_NAME, CHOOSING_CLASS, CHOOSING_AGE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = database.get_user(update.effective_user.id)
    if user:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"С возвращением, {user[3]}! Твой баланс: {user[6]} монет."
        )
        await handlers_menu.show_main_menu(update, context)
        return ConversationHandler.END
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Добро пожаловать в FinQuest! 🚀\n\nЗдесь ты научишься управлять деньгами и прокачаешь своего героя.\n\nДля начала, придумай имя своему персонажу:"
    )
    return CHOOSING_NAME

async def choose_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['char_name'] = name
    
    reply_keyboard = [['Маг', 'Инженер', 'Воин']]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Отличное имя, {name}!\n\nТеперь выбери класс персонажа:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING_CLASS

async def choose_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    char_class = update.message.text
    if char_class not in ['Маг', 'Инженер', 'Воин']:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, выбери класс из меню.")
        return CHOOSING_CLASS
    
    context.user_data['char_class'] = char_class
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Сколько тебе лет? (Напиши число, например: 10)",
        reply_markup=ReplyKeyboardRemove()
    )
    return CHOOSING_AGE

async def choose_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 5 or age > 99:
             await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, введи реальный возраст.")
             return CHOOSING_AGE
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, введи число.")
        return CHOOSING_AGE

    context.user_data['age'] = age
    char_name = context.user_data['char_name']
    char_class = context.user_data['char_class']
    
    # Save to database
    database.add_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
        character_name=char_name,
        character_class=char_class,
        age=age
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Герой создан! \nИмя: {char_name}\nКласс: {char_class}\nВозраст: {age}\n\nТеперь ты готов к финансовым приключениям!",
    )
    await handlers_menu.show_main_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Регистрация отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Resetting user {update.effective_user.id}")
    database.delete_user(update.effective_user.id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Твой профиль сброшен! Напиши /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_name)],
            CHOOSING_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_class)],
            CHOOSING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_age)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('reset', reset)]
    )
