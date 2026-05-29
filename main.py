import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

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
    edit_stock_limit_start, receive_stock_limit_value,
    edit_markup_percent_start, receive_markup_percent_value,
    manage_categories_start, process_category_action,
    receive_category_add_name, receive_category_rename_target,
    receive_category_rename_value, receive_category_delete_target,
    delete_store_start, receive_delete_store_confirm,
    ai_add_start, receive_ai_photo, confirm_ai_add,
    CATEGORY, ITEM_NAME, QUANTITY, PRICE, SALE_ITEM, SALE_QUANTITY, 
    EDIT_SEARCH, EDIT_CHOOSE_FIELD, EDIT_NEW_VALUE, DELETE_SEARCH, DELETE_CONFIRM, RENAME_STORE,
    AI_PHOTO, AI_CONFIRM, DELETE_STORE,
    UTANG_CUSTOMER, UTANG_CONTACT, UTANG_ITEM, UTANG_QTY, UTANG_CART_ACTION, UTANG_NOTES,
    PAYMENT_CUSTOMER, PAYMENT_AMOUNT,
    SEARCH_CUSTOMER_QUERY,
    EDIT_DEBT_LIMIT, EDIT_STOCK_LIMIT, EDIT_MARKUP_PERCENT,
    CATEGORY_ACTION, CATEGORY_ADD_NAME, CATEGORY_RENAME_TARGET, CATEGORY_RENAME_VALUE, CATEGORY_DELETE_TARGET,
    GET_STARTING_POT, GET_ACTUAL_CASH, GET_AUDIT_NOTES
)

# ==========================================
# 🌐 THE DUMMY SERVER (FIXES RENDER PORT TIMEOUT)
# ==========================================
def run_dummy_server():
    class HealthCheckHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is alive and healthy!")

    # Grab the port Render expects, or default to 10000
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌍 Dummy Web Server listening on port {port}...")
    server.serve_forever()


if __name__ == '__main__':
    print("🚀 Starting Secured InventoryLink Bot...")
    
    # 1. Start the dummy web server in the background FIRST
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()
    
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

    edit_stock_limit_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🚨 Edit Stock Alert Limit"]), edit_stock_limit_start)],
        states={
            EDIT_STOCK_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_stock_limit_value)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_stock_limit_value)]
    )

    edit_markup_percent_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💸 Edit Selling Price %"]), edit_markup_percent_start)],
        states={
            EDIT_MARKUP_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_markup_percent_value)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_markup_percent_value)]
    )

    manage_categories_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🗂️ Manage Categories"]), manage_categories_start)],
        states={
            CATEGORY_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_category_action)],
            CATEGORY_ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category_add_name)],
            CATEGORY_RENAME_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category_rename_target)],
            CATEGORY_RENAME_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category_rename_value)],
            CATEGORY_DELETE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category_delete_target)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Settings"]), process_category_action)]
    )

    # 8. AI SCANNER WIZARD
    ai_scanner_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["📸 Add via AI (Photo)"]), ai_add_start)],
        states={
            AI_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, receive_ai_photo)],
            AI_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_ai_add)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel"]), confirm_ai_add)]
    )

    # 9. ADD NEW UTANG WIZARD
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

    # 10. RECORD PAYMENT WIZARD
    record_payment_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💳 Record Payment"]), record_payment_start)],
        states={
            PAYMENT_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_customer_name)],
            PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_amount)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_payment_amount)]
    )

    # 11. SEARCH CUSTOMER WIZARD
    search_customer_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🔍 Search Customer"]), search_customer_start)],
        states={
            SEARCH_CUSTOMER_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_customer_query)],
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Cancel", "🔙 Back to Main Menu"]), receive_search_customer_query)]
    )

    # 12. DAILY AUDIT WIZARD
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
    app.add_handler(edit_stock_limit_wizard)
    app.add_handler(edit_markup_percent_wizard)
    app.add_handler(manage_categories_wizard)
    app.add_handler(ai_scanner_wizard)
    app.add_handler(add_utang_wizard)
    app.add_handler(record_payment_wizard)
    app.add_handler(search_customer_wizard)
    app.add_handler(audit_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ui_clicks))
    
    print("🤖 Bot is securely online! Open Telegram to test it.")
    app.run_polling()