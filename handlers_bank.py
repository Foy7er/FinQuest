from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import database
import handlers_menu

# States
CHOOSING_ACTION, ENTERING_AMOUNT = range(2)

async def bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = database.get_user(update.effective_user.id)
    wallet = user[6]
    savings = user[7]
    
    text = (
        f"🏦 **Касса Сбережений**\n\n"
        f"💳 В кошельке: {wallet} монет\n"
        f"🔒 В сбережениях: {savings} монет\n\n"
        f"📈 Ставка: 5% в день\n"
        f"Что хочешь сделать?"
    )
    
    keyboard = [['📥 Положить', '📤 Снять'], ['🔙 Назад']]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text
    
    if action == '🔙 Назад':
        await handlers_menu.show_main_menu(update, context)
        return ConversationHandler.END
        
    if action not in ['📥 Положить', '📤 Снять']:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Выбери действие из меню.")
        return CHOOSING_ACTION
    
    context.user_data['bank_action'] = 'deposit' if action == '📥 Положить' else 'withdraw'
    
    # Get current balance for "All" button
    user = database.get_user(update.effective_user.id)
    wallet = user[6]
    savings = user[7]
    
    # Create quick buttons with "All" option
    if action == '📥 Положить':
        keyboard = [
            ['10', '20', '30'],
            [f'💰 Все ({wallet})'],
            ['🔙 Отмена']
        ]
        text = f"Сколько монет положить?\n💳 В кошельке: {wallet} монет"
    else:  # Снять
        keyboard = [
            ['10', '20', '30'],
            [f'💰 Все ({savings})'],
            ['🔙 Отмена']
        ]
        text = f"Сколько монет снять?\n🔒 В сбережениях: {savings} монет"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ENTERING_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '🔙 Отмена':
        await handlers_menu.show_main_menu(update, context)
        return ConversationHandler.END
    
    user = database.get_user(update.effective_user.id)
    wallet = user[6]
    savings = user[7]
    action = context.user_data['bank_action']
    
    # Handle "All" button
    if text.startswith('💰 Все'):
        amount = wallet if action == 'deposit' else savings
    else:
        # Parse number
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, введи положительное число или выбери кнопку.")
            return ENTERING_AMOUNT
    
    # Validate and process
    if action == 'deposit':
        if amount > wallet:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Недостаточно средств в кошельке!\n💳 У тебя: {wallet} монет\n💸 Нужно: {amount} монет")
            return ENTERING_AMOUNT
        
        database.update_balance(update.effective_user.id, -amount, is_savings=False)
        database.update_balance(update.effective_user.id, amount, is_savings=True)
        msg = f"✅ Успешно!\n📥 Положено в сбережения: {amount} монет"
        
    else:  # withdraw
        if amount > savings:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Недостаточно средств в сбережениях!\n🔒 У тебя: {savings} монет\n💸 Нужно: {amount} монет")
            return ENTERING_AMOUNT
            
        database.update_balance(update.effective_user.id, amount, is_savings=False)
        database.update_balance(update.effective_user.id, -amount, is_savings=True)
        msg = f"✅ Успешно!\n📤 Снято со счета: {amount} монет"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    await handlers_menu.show_main_menu(update, context)
    return ConversationHandler.END

def get_bank_conv_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🏦 Сбережения$'), bank_menu)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        },
        fallbacks=[CommandHandler('cancel', bank_menu)]
    )
