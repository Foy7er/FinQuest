from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import database
import handlers_menu
import random
import sqlite3

# States
CHOOSING_ITEM = 0

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main market menu with Buy/Sell options"""
    msg = "📈 **Биржа Активов**\n\nЧто хочешь сделать?"
    
    keyboard = [
        [InlineKeyboardButton("💰 Купить", callback_data="show_buy")],
        [InlineKeyboardButton("💸 Продать", callback_data="show_sell")],
        [InlineKeyboardButton("🎒 Мой Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    return CHOOSING_ITEM

async def show_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show items available for purchase"""
    query = update.callback_query
    
    # Simulate price fluctuation
    conn = sqlite3.connect(database.DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM market_items')
    items = cursor.fetchall()
    
    # Randomly adjust prices slightly (+- 10%)
    for item in items:
        new_price = int(item[3] * random.uniform(0.9, 1.1))
        cursor.execute('UPDATE market_items SET current_price = ? WHERE id = ?', (new_price, item[0]))
    conn.commit()
    
    # Fetch updated items
    cursor.execute('SELECT * FROM market_items')
    items = cursor.fetchall()
    conn.close()
    
    msg = "💰 **Купить Активы**\n\nЦены меняются каждый раз!\n\n"
    keyboard = []
    
    for item in items:
        msg += f"📦 *{item[1]}* — {item[3]} монет\n_{item[2]}_\n\n"
        keyboard.append([InlineKeyboardButton(f"Купить {item[1]} ({item[3]} 💰)", callback_data=f"buy_{item[0]}")])
        
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="market_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup)
    return CHOOSING_ITEM

async def show_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show inventory items available for sale"""
    query = update.callback_query
    
    user = database.get_user(update.effective_user.id)
    items = database.get_inventory(user[0])
    
    if not items:
        msg = "💸 **Продать Активы**\n\nУ тебя нет предметов для продажи!"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="market_menu")]]
    else:
        msg = "💸 **Продать Активы**\n\nВыбери что продать (цена = 80% от стоимости):\n\n"
        keyboard = []
        
        # Get current market prices
        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        
        for item in items:
            # Get market price for this item
            cursor.execute('SELECT current_price FROM market_items WHERE name = ?', (item[0],))
            result = cursor.fetchone()
            if result:
                sell_price = int(result[0] * 0.8)  # Sell for 80% of market price
                msg += f"📦 *{item[0]}* (x{item[2]}) — {sell_price} монет\n"
                keyboard.append([InlineKeyboardButton(f"Продать {item[0]} ({sell_price} 💰)", callback_data=f"sell_{item[0]}")])
        
        conn.close()
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="market_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup)
    return CHOOSING_ITEM

async def handle_market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back":
        await query.delete_message()
        await handlers_menu.show_main_menu(update, context)
        return ConversationHandler.END
    
    if data == "market_menu":
        await market_menu(update, context)
        return CHOOSING_ITEM
    
    if data == "show_buy":
        await show_buy_menu(update, context)
        return CHOOSING_ITEM
    
    if data == "show_sell":
        await show_sell_menu(update, context)
        return CHOOSING_ITEM
        
    if data == "inventory":
        await show_inventory(update, context)
        return CHOOSING_ITEM
        
    if data.startswith("buy_"):
        item_id = int(data.split("_")[1])
        
        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM market_items WHERE id = ?', (item_id,))
        item = cursor.fetchone()
        conn.close()
        
        if not item:
            await query.edit_message_text(text="Товар не найден.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="market_menu")]]))
            return CHOOSING_ITEM
            
        user = database.get_user(update.effective_user.id)
        wallet = user[6]
        price = item[3]
        
        if wallet < price:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Недостаточно монет! Нужно {price}, а у тебя {wallet}.")
            return CHOOSING_ITEM
            
        # Buy item
        database.update_balance(update.effective_user.id, -price, is_savings=False)
        database.add_to_inventory(user[0], item_id)
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Ты купил {item[1]} за {price} монет!")
        
        # Refresh buy menu
        await show_buy_menu(update, context)
        return CHOOSING_ITEM
    
    if data.startswith("sell_"):
        item_name = data.replace("sell_", "")
        
        user = database.get_user(update.effective_user.id)
        
        # Get market price
        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id, current_price FROM market_items WHERE name = ?', (item_name,))
        result = cursor.fetchone()
        
        if not result:
            await query.edit_message_text(text="Предмет не найден на рынке.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="market_menu")]]))
            conn.close()
            return CHOOSING_ITEM
        
        item_id, market_price = result
        sell_price = int(market_price * 0.8)
        
        # Remove from inventory
        cursor.execute('SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?', (user[0], item_id))
        inv_result = cursor.fetchone()
        
        if not inv_result or inv_result[0] <= 0:
            await query.edit_message_text(text="У тебя нет этого предмета!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="market_menu")]]))
            conn.close()
            return CHOOSING_ITEM
        
        # Decrease quantity
        new_quantity = inv_result[0] - 1
        if new_quantity > 0:
            cursor.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?', (new_quantity, user[0], item_id))
        else:
            cursor.execute('DELETE FROM inventory WHERE user_id = ? AND item_id = ?', (user[0], item_id))
        
        conn.commit()
        conn.close()
        
        # Add money to wallet
        database.update_balance(update.effective_user.id, sell_price, is_savings=False)
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Ты продал {item_name} за {sell_price} монет!")
        
        # Refresh sell menu
        await show_sell_menu(update, context)
        return CHOOSING_ITEM

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = database.get_user(update.effective_user.id)
    items = database.get_inventory(user[0])
    
    if not items:
        msg = "🎒 **Твой Инвентарь**\n\nПусто! Купи что-нибудь на бирже."
    else:
        msg = "🎒 **Твой Инвентарь**\n\n"
        for item in items:
            msg += f"📦 *{item[0]}* (x{item[2]})\n_{item[1]}_\n\n"
            
    keyboard = [[InlineKeyboardButton("🔙 Назад к Бирже", callback_data="market_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown', reply_markup=reply_markup)

async def back_to_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await market_menu(update, context)
    return CHOOSING_ITEM

def get_market_conv_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📈 Биржа$'), market_menu)],
        states={
            CHOOSING_ITEM: [
                CallbackQueryHandler(handle_market_callback)
            ],
        },
        fallbacks=[CommandHandler('cancel', handlers_menu.show_main_menu)],
        per_message=False
    )
