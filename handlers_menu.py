from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

import database

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['💰 Фин-Заработок', '👛 Кошелек'],
        ['🏦 Сбережения', '📈 Биржа'],
        ['🛒 Магазин', '👤 Герой']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Главное меню:",
        reply_markup=reply_markup
    )

async def wallet_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = database.get_user(update.effective_user.id)
    if user:
        balance = user[6]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Твой кошелек:\n💳 Баланс: {balance} монет")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ошибка: Пользователь не найден.")

async def hero_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = database.get_user(update.effective_user.id)
    if user:
        char_class = user[4]
        level = user[5]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Твой герой:\n🧙 Класс: {char_class}\n⭐ Уровень: {level}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ошибка: Пользователь не найден.")

async def placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Этот раздел еще в разработке! 🛠️")
