from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler
from config import TELEGRAM_TOKEN
from handlers import (
    start_command, handle_ui_clicks, 
    add_manual_start, receive_category, receive_item_name, receive_quantity, receive_price,
    CATEGORY, ITEM_NAME, QUANTITY, PRICE
)

if __name__ == '__main__':
    print("🚀 Starting InventoryLink Modular Bot...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # 1. BUILD THE WIZARD
    add_item_wizard = ConversationHandler(
        # How to start the wizard:
        entry_points=[MessageHandler(filters.Text(["⌨️ Add Manual (Type)"]), add_manual_start)],
        # The steps:
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category)],
            ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_item_name)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
        },
        # How to forcefully break out if something goes wrong
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_price)]
    )

    # 2. ATTACH EVERYTHING TO THE ENGINE (Wizard first!)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(add_item_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ui_clicks))
    
    print("🤖 Bot is online! Open Telegram to test it.")
    app.run_polling()