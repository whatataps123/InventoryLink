from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
# Import our other files!
from config import MAINTENANCE_MODE
from menus import get_main_menu, get_inventory_menu, get_sales_menu, get_utang_menu

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if MAINTENANCE_MODE:
        await update.message.reply_text("🛠️ System Maintenance. Please check back later!")
        return 

    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"👋 Welcome to InventoryLink, {user_name}!\n\nMain Menu:", reply_markup=get_main_menu())

async def handle_ui_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if MAINTENANCE_MODE:
        await update.message.reply_text("🛠️ System Maintenance. Please check back later!")
        return 

    user_text = update.message.text

    # --- MAIN MENU ---
    if user_text == "📦 1. Inventory":
        await update.message.reply_text("📦 **Inventory Dashboard**", reply_markup=get_inventory_menu())
    elif user_text == "💰 2. Sales":
        await update.message.reply_text("💰 **Sales Dashboard**", reply_markup=get_sales_menu())
    elif user_text == "📝 3. Utang (Credit)":
        await update.message.reply_text("📝 **Utang Dashboard**", reply_markup=get_utang_menu())
    elif user_text == "❓ 4. Help / About":
        await update.message.reply_text("🤖 **About InventoryLink**\nYour digital Sari-Sari store assistant!", reply_markup=get_main_menu())
    elif user_text == "❌ Exit":
        await update.message.reply_text("Goodbye! 👋 Type /start to open the app again.", reply_markup=ReplyKeyboardRemove())

    # --- INVENTORY MENU ---
    elif user_text == "👀 View Current Stock":
        await update.message.reply_text("*(Feature Coming Soon: Will fetch items from database)*")
    elif user_text in ["⌨️ Add Manual (Type)", "📸 Add via AI (Photo)", "✏️ Edit Item", "🗑️ Delete Item"]:
        await update.message.reply_text(f"*(Feature Coming Soon: {user_text.replace(' ', ' ', 1)})*")

    # --- OTHER MENUS & BACK BUTTON ---
    elif user_text in ["🛒 Record a Sale", "📈 View Sales Report", "➕ Add New Utang", "💳 Record Payment"]:
        await update.message.reply_text(f"*(Feature Coming Soon)*")
    elif user_text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("🤔 Please use the menu buttons.")