from telegram import ReplyKeyboardMarkup

def get_main_menu():
    keyboard = [
        ["📦 1. Inventory", "💰 2. Sales"],
        ["📝 3. Utang (Credit)", "❓ 4. Help / About"],
        ["❌ Exit"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inventory_menu():
    keyboard = [
        ["👀 View Current Stock"],
        ["⌨️ Add Manual (Type)", "📸 Add via AI (Photo)"],
        ["✏️ Edit Item", "🗑️ Delete Item"],
        ["🔙 Back to Main Menu"]
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
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)