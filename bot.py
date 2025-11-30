import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

import database
import handlers_start

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    # Initialize Database
    database.init_db()
    print("Database initialized.")

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        exit(1)

    application = ApplicationBuilder().token(token).build()
    
    # Add Handlers
    application.add_handler(handlers_start.get_conv_handler())
    application.add_handler(CommandHandler('reset', handlers_start.reset))
    
    import handlers_earn
    import handlers_bank
    import handlers_market
    import handlers_shop
    
    application.add_handler(handlers_earn.get_earn_conv_handler())
    application.add_handler(handlers_bank.get_bank_conv_handler())
    application.add_handler(handlers_market.get_market_conv_handler())
    
    # Menu Handlers
    import handlers_menu
    # application.add_handler(MessageHandler(filters.Regex('^💰 Фин-Заработок$'), handlers_menu.placeholder)) # Replaced by conv handler
    application.add_handler(MessageHandler(filters.Regex('^👛 Кошелек$'), handlers_menu.wallet_info))
    # application.add_handler(MessageHandler(filters.Regex('^🏦 Сбережения$'), handlers_menu.placeholder)) # Replaced by conv handler
    # application.add_handler(MessageHandler(filters.Regex('^📈 Биржа$'), handlers_menu.placeholder)) # Replaced by conv handler
    application.add_handler(handlers_shop.get_shop_handler())
    application.add_handler(handlers_shop.get_shop_callback_handler())
    application.add_handler(MessageHandler(filters.Regex('^👤 Герой$'), handlers_menu.hero_info))
    
    # ... (handlers setup remains the same)

    # Check if running in Cloud (Render)
    webhook_url = os.getenv('RENDER_EXTERNAL_URL') # Render sets this automatically
    port = int(os.getenv('PORT', '8443'))

    if webhook_url:
        # Webhook Mode (for Render)
        print(f"Starting Webhook on port {port}...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{webhook_url}/{token}"
        )
    else:
        # Polling Mode (Local)
        print("Bot is running in POLLING mode...")
        application.run_polling()
