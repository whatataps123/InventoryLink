from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, AIORateLimiter
from config import TELEGRAM_TOKEN
from handlers import (
    start_command, handle_ui_clicks, 
    add_manual_start, receive_category, receive_item_name, receive_quantity, receive_price,
    record_sale_start, receive_sale_item, receive_sale_quantity,
    edit_item_start, receive_edit_search, receive_edit_field, receive_edit_value, 
    delete_item_start, receive_delete_search, receive_delete_confirm, 
    CATEGORY, ITEM_NAME, QUANTITY, PRICE, SALE_ITEM, SALE_QUANTITY, 
    EDIT_SEARCH, EDIT_CHOOSE_FIELD, EDIT_NEW_VALUE, DELETE_SEARCH, DELETE_CONFIRM ,
    rename_store_start, receive_new_store_name, RENAME_STORE
)

if __name__ == '__main__':
    print("🚀 Starting Secured InventoryLink Bot...")
    
    # ==========================================
    # 🛡️ THE SECURITY UPDATE
    # We add AIORateLimiter() to our ApplicationBuilder!
    # ==========================================
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).rate_limiter(AIORateLimiter()).build()
    
    # 1. ADD WIZARD
    add_item_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["⌨️ Add Manual (Type)"]), add_manual_start)],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category)],
            ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_item_name)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_price)] 
    )

    # 2. SALE WIZARD
    record_sale_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🛒 Record a Sale"]), record_sale_start)],
        states={
            SALE_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sale_item)],
            SALE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sale_quantity)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_sale_quantity)]
    )

    # 3. EDIT WIZARD
    edit_item_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["✏️ Edit Item"]), edit_item_start)],
        states={
            EDIT_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_search)],
            EDIT_CHOOSE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_field)],
            EDIT_NEW_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_value)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_edit_value)]
    )

    # 4. DELETE WIZARD
    delete_item_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🗑️ Delete Item"]), delete_item_start)],
        states={
            DELETE_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_search)],
            DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_confirm)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_delete_confirm)]
    )

    # 5. RENAME STORE WIZARD
    rename_store_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🏷️ Rename Store"]), rename_store_start)],
        states={
            RENAME_STORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_store_name)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_new_store_name)]
    )

    # ATTACH EVERYTHING
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(add_item_wizard)
    app.add_handler(record_sale_wizard)
    app.add_handler(edit_item_wizard)
    app.add_handler(delete_item_wizard)
    app.add_handler(rename_store_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ui_clicks))
    
    print("🤖 Bot is securely online! Open Telegram to test it.")
    app.run_polling()