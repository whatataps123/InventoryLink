from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from handlers import start_command, handle_ui_clicks

if __name__ == '__main__':
    print("🚀 Starting InventoryLink Modular Bot...")
    
    # Build the application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Attach our logic handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ui_clicks))
    
    print("🤖 Bot is online! Open Telegram to test it.")
    app.run_polling()