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
        ["⏱️ Edit Debt Limit (Days)"],
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
        ["🛒 Record a Sale", "📈 View Sales Report"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_utang_menu():
    keyboard = [
        ["➕ Add New Utang", "💳 Record Payment"],
        ["📋 View Active Debts", "🔍 Search Customer"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)