from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import database
import handlers_menu

# Available shop games with prices and multipliers
SHOP_GAMES = {
    'capitals': {
        'name': '🌍 Угадай столицу',
        'description': 'Угадывай столицы стран мира',
        'price': 50,
        'reward_multiplier': 2.0
    },
    'flags': {
        'name': '🏴 Угадай флаг',
        'description': 'Определи страну по флагу',
        'price': 50,
        'reward_multiplier': 2.0
    },
    'history': {
        'name': '🎭 Исторические даты',
        'description': 'Проверь знания истории',
        'price': 75,
        'reward_multiplier': 3.0
    },
    'science': {
        'name': '🧬 Наука и технологии',
        'description': 'Вопросы о науке',
        'price': 75,
        'reward_multiplier': 3.0
    }
}

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show shop with available games"""
    user = database.get_user(update.effective_user.id)
    user_id = user[0]
    wallet = user[6]
    purchased = database.get_purchased_games(user_id)
    
    msg = f"🛒 **Магазин Игр**\n\n💳 Твой баланс: {wallet} монет\n\n"
    msg += "Покупай игры с ПОВЫШЕННЫМИ наградами!\n\n"
    
    keyboard = []
    for game_id, game in SHOP_GAMES.items():
        if game_id in purchased:
            status = "✅ Куплено"
            button_text = f"{game['name']} {status}"
            callback = f"owned_{game_id}"
        else:
            status = f"💰 {game['price']} монет"
            button_text = f"{game['name']} - {status}"
            callback = f"buy_{game_id}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shop button clicks"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "back":
        await query.delete_message()
        await handlers_menu.show_main_menu(update, context)
        return
    
    if data.startswith("buy_"):
        game_id = data.replace("buy_", "")
        game = SHOP_GAMES[game_id]
        
        user = database.get_user(update.effective_user.id)
        user_id = user[0]
        wallet = user[6]
        
        if wallet < game['price']:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Недостаточно монет!\n💳 У тебя: {wallet}\n💸 Нужно: {game['price']}"
            )
            return
        
        # Purchase game
        database.update_balance(update.effective_user.id, -game['price'], is_savings=False)
        database.purchase_game(user_id, game_id)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Покупка успешна!\n\n{game['name']} теперь доступна в разделе 💰 Фин-Заработок!\n\n🎁 Награда x{game['reward_multiplier']}"
        )
        
        # Refresh shop
        await shop_menu(update, context)
    
    elif data.startswith("owned_"):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Эта игра уже куплена! Играй в разделе 💰 Фин-Заработок"
        )

def get_shop_handler():
    """Create message handler for shop"""
    return MessageHandler(filters.Regex('^🛒 Магазин$'), shop_menu)

def get_shop_callback_handler():
    """Create callback handler for shop"""
    return CallbackQueryHandler(handle_shop_callback, pattern="^(buy_|owned_|back)$")
