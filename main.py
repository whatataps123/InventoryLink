from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, AIORateLimiter
from config import TELEGRAM_TOKEN
from handlers import (
    start_command, handle_ui_clicks, 
    add_manual_start, receive_category, receive_item_name, receive_quantity, receive_price,
    record_sale_start, receive_sale_item, receive_sale_quantity,
    add_utang_start, receive_utang_customer_name, receive_utang_contact, receive_utang_item,
    receive_utang_quantity, handle_utang_cart_action, receive_utang_notes,
    record_payment_start, receive_payment_customer_name, receive_payment_amount,
    search_customer_start, receive_search_customer_query,
    handle_view_sales_report, process_report_selection,
    start_daily_audit, process_starting_pot,
    process_actual_cash, process_audit_notes, cancel_daily_audit,
    edit_item_start, receive_edit_search, receive_edit_field, receive_edit_value, 
    delete_item_start, receive_delete_search, receive_delete_confirm, 
    rename_store_start, receive_new_store_name,
    edit_debt_limit_start, receive_debt_limit_value,
    delete_store_start, receive_delete_store_confirm,
    ai_add_start, receive_ai_photo, confirm_ai_add, # <-- NEW AI IMPORTS
    CATEGORY, ITEM_NAME, QUANTITY, PRICE, SALE_ITEM, SALE_QUANTITY, 
    EDIT_SEARCH, EDIT_CHOOSE_FIELD, EDIT_NEW_VALUE, DELETE_SEARCH, DELETE_CONFIRM, RENAME_STORE,
    AI_PHOTO, AI_CONFIRM, DELETE_STORE,
    UTANG_CUSTOMER, UTANG_CONTACT, UTANG_ITEM, UTANG_QTY, UTANG_CART_ACTION, UTANG_NOTES,
    PAYMENT_CUSTOMER, PAYMENT_AMOUNT,
    SEARCH_CUSTOMER_QUERY,
    EDIT_DEBT_LIMIT,
    GET_STARTING_POT, GET_ACTUAL_CASH, GET_AUDIT_NOTES
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

    # 6. DELETE STORE WIZARD
    delete_store_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🧾 Delete Store"]), delete_store_start)],
        states={
            DELETE_STORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_store_confirm)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), receive_delete_store_confirm)]
    )

    # 7. DEBT LIMIT SETTINGS WIZARD
    edit_debt_limit_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["⏱️ Edit Debt Limit (Days)"]), edit_debt_limit_start)],
        states={
            EDIT_DEBT_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_debt_limit_value)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_debt_limit_value)]
    )

    # 6. AI SCANNER WIZARD
    ai_scanner_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["📸 Add via AI (Photo)"]), ai_add_start)],
        states={
            # Notice we use filters.PHOTO here so it explicitly waits for an image!
            AI_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, receive_ai_photo)],
            AI_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_ai_add)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), confirm_ai_add)]
    )

    # 7. ADD NEW UTANG WIZARD
    add_utang_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["➕ Add New Utang"]), add_utang_start)],
        states={
            UTANG_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utang_customer_name)],
            UTANG_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utang_contact)],
            UTANG_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utang_item)],
            UTANG_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utang_quantity)],
            UTANG_CART_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utang_cart_action)],
            UTANG_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utang_notes)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_utang_notes)]
    )

    # 8. RECORD PAYMENT WIZARD
    record_payment_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💳 Record Payment"]), record_payment_start)],
        states={
            PAYMENT_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_customer_name)],
            PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_amount)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_payment_amount)]
    )

    # 9. SEARCH CUSTOMER WIZARD
    search_customer_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🔍 Search Customer"]), search_customer_start)],
        states={
            SEARCH_CUSTOMER_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_customer_query)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_search_customer_query)]
    )

    # 10. DAILY AUDIT WIZARD
    audit_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🔒 Close & Audit"]), start_daily_audit)],
        states={
            GET_STARTING_POT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_starting_pot)],
            GET_ACTUAL_CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_actual_cash)],
            GET_AUDIT_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_audit_notes)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "❌ Cancel Audit"]), cancel_daily_audit)],
    )

    # ATTACH EVERYTHING
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(add_item_wizard)
    app.add_handler(record_sale_wizard)
    app.add_handler(edit_item_wizard)
    app.add_handler(delete_item_wizard)
    app.add_handler(rename_store_wizard)
    app.add_handler(delete_store_wizard)
    app.add_handler(edit_debt_limit_wizard)
    app.add_handler(ai_scanner_wizard)
    app.add_handler(add_utang_wizard)
    app.add_handler(record_payment_wizard)
    app.add_handler(search_customer_wizard)
    app.add_handler(audit_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ui_clicks))
    
    print("🤖 Bot is securely online! Open Telegram to test it.")
    app.run_polling()