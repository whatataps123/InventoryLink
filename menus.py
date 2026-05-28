from telegram import ReplyKeyboardMarkup

def get_main_menu():
    keyboard = [
        ["📦 Inventory", "💰 Sales"],
        ["📝 Utang (Credit)", "📊 View Web Dashboard"],
        ["⚙️ Settings", "❓ Help / About"],
        ["❌ Exit"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_settings_menu():
    keyboard = [
        ["🏷️ Rename Store", "🧾 Delete Store"],
        ["⏱️ Edit Debt Limit (Days)", "🚨 Edit Stock Alert Limit"],
        ["💸 Edit Selling Price %", "🗂️ Manage Categories"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inventory_menu():
    keyboard = [
        ["👀 View Current Stock", "⌨️ Add Manual (Type)"],
        ["📸 Add via AI (Photo)", "✏️ Edit Item"],
        ["🗑️ Delete Item", "🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_sales_menu():
    keyboard = [
        ["🛒 Record a Sale"],
        ["📈 View Sales Report", "🔒 Close & Audit"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_sales_report_menu():
    keyboard = [
        ["☀️ Today's Drawer Summary", "📅 Lookup a Day"],
        ["📊 View Dashboard", "🚨 Critical Out-Of-Stock"],
        ["🔙 Back to Sales Menu"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_utang_menu():
    keyboard = [
        ["➕ Add New Utang", "💳 Record Payment"],
        ["📋 View Active Debts", "🔍 Search Customer"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
