from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import MAINTENANCE_MODE, supabase
from menus import get_main_menu, get_inventory_menu, get_sales_menu, get_utang_menu

# -----------------------------------
# THE WIZARD STATES
# -----------------------------------
CATEGORY, ITEM_NAME, QUANTITY, PRICE = range(4)

async def add_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["🥤 Drinks", "🍫 Snacks"], ["🧼 Essentials", "📦 Others"], ["❌ Cancel"]]
    await update.message.reply_text(
        "✨ **Let's manage your stock!**\n\nFirst, what **Category** does this item belong to?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    )
    return CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END
    
    context.user_data['category'] = text
    await update.message.reply_text("Great! What is the **Name** of the item? (e.g., Coke 1.5L)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return ITEM_NAME

async def receive_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    context.user_data['item_name'] = text
    user_id = update.message.from_user.id

    # ==========================================
    # 🔍 NEW: SMART RESTOCK CHECK
    # ==========================================
    try:
        # We use .ilike() so "coke" and "Coke" are treated as the same item!
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", text).execute()
        existing_items = response.data

        if existing_items:
            # We found it! Save the existing info to the bot's memory
            existing_item = existing_items[0]
            context.user_data['existing_item'] = existing_item
            
            current_qty = existing_item['quantity']
            reply_msg = f"🔍 **I found this in your stock!**\nYou currently have **{current_qty} pcs** of {existing_item['item_name']}.\n\nHow many **NEW** pieces are you adding to the shelf?"
        else:
            # It is a brand new item
            context.user_data['existing_item'] = None
            reply_msg = f"Got it: {text}.\n\nHow many **Pieces** are you adding? (Please type a number, e.g., 10)"

        await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
        return QUANTITY

    except Exception as e:
        print(f"Error checking existing item: {e}")
        await update.message.reply_text("⚠️ Server Error. Please try again.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text("⚠️ Oops! Please type a valid number (e.g., 10). Try again:")
        return QUANTITY 

    # We call this "added_qty" because it might be brand new, or it might be restock
    added_qty = int(text)
    context.user_data['added_quantity'] = added_qty

    # ==========================================
    # 💰 NEW: SMART PRICE HANDLING
    # ==========================================
    existing_item = context.user_data.get('existing_item')

    if existing_item:
        old_price = existing_item['wholesale_price']
        context.user_data['old_price'] = old_price
        
        # We give them a special button so they don't have to re-type the old price!
        reply_msg = f"Got it. Your current wholesale cost for this is **₱{old_price}**.\n\nDo you want to keep this price? Click the button below, or type a **new price** if the cost went up/down."
        keyboard = [[f"Keep ₱{old_price}"], ["❌ Cancel"]]
    else:
        reply_msg = "Awesome. Finally, what is the **Wholesale Cost per piece**? (e.g., 60 or 15.50)"
        keyboard = [["❌ Cancel"]]

    await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return PRICE

async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    existing_item = context.user_data.get('existing_item')

    # Did they click the "Keep Price" button?
    if text.startswith("Keep ₱"):
        wholesale_price = context.user_data['old_price']
    else:
        try:
            wholesale_price = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ Oops! Please type a valid price (e.g., 60.50). Try again:")
            return PRICE

    category = context.user_data['category']
    item_name = context.user_data['item_name']
    added_qty = context.user_data['added_quantity']
    user_id = update.message.from_user.id
    retail_price = wholesale_price * 1.20 # 20% Markup

    # ==========================================
    # 💾 NEW: SAVE OR UPDATE LOGIC
    # ==========================================
    try:
        if existing_item:
            # MATH: Old Quantity + New Quantity
            final_qty = existing_item['quantity'] + added_qty
            
            # We UPDATE the existing row instead of making a new one
            supabase.table("inventory").update({
                "quantity": final_qty,
                "wholesale_price": wholesale_price,
                "retail_price": retail_price
            }).eq("id", existing_item['id']).execute()
            
            success_msg = f"✅ **Restock Successful!**\nAdded {added_qty} more to {item_name}.\nYou now have **{final_qty} pcs** in total.\nSelling price: ₱{retail_price:.2f}."
        
        else:
            # It's brand new! INSERT it.
            supabase.table("inventory").insert({
                "telegram_id": user_id, "category": category, "item_name": item_name,
                "quantity": added_qty, "wholesale_price": wholesale_price, "retail_price": retail_price
            }).execute()
            
            success_msg = f"✅ **New Item Added!**\nAdded {added_qty}x {item_name} to {category}.\nSelling price set to ₱{retail_price:.2f}."

        await update.message.reply_text(success_msg, reply_markup=get_inventory_menu())
    
    except Exception as e:
        print(f"DB Error: {e}")
        await update.message.reply_text("⚠️ Server Error: Could not save item.", reply_markup=get_inventory_menu())
    
    context.user_data.clear() 
    return ConversationHandler.END

# -----------------------------------
# THE NORMAL MENU BUTTONS
# -----------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if MAINTENANCE_MODE:
        await update.message.reply_text("🛠️ System Maintenance. Please check back later!")
        return 
    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"👋 Welcome to InventoryLink, {user_name}!\n\nMain Menu:", reply_markup=get_main_menu())

async def handle_ui_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if MAINTENANCE_MODE:
        await update.message.reply_text("🛠️ Maintenance mode.")
        return 

    user_text = update.message.text
    user_id = update.message.from_user.id 

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

    elif user_text == "👀 View Current Stock":
        await update.message.reply_text("📦 Fetching your organized inventory...")
        try:
            response = supabase.table("inventory").select("*").eq("telegram_id", user_id).execute()
            items = response.data
            
            if not items: 
                await update.message.reply_text("Your shelf is empty!", reply_markup=get_inventory_menu())
            else:
                grouped_items = {}
                for item in items:
                    cat = item.get("category", "📦 Others")
                    if cat not in grouped_items:
                        grouped_items[cat] = []
                    grouped_items[cat].append(item)
                
                inventory_text = "📊 **Your Current Stock:**\n\n"
                for cat, cat_items in grouped_items.items():
                    inventory_text += f"**{cat}**\n"
                    for item in cat_items:
                        inventory_text += f"   ▪️ {item['item_name']}: {item['quantity']} pcs (₱{item['retail_price']})\n"
                    inventory_text += "\n"
                await update.message.reply_text(inventory_text, reply_markup=get_inventory_menu())
        except Exception as e:
            await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())

    elif user_text in ["📸 Add via AI (Photo)", "✏️ Edit Item", "🗑️ Delete Item", "🛒 Record a Sale", "📈 View Sales Report", "➕ Add New Utang", "💳 Record Payment"]:
        await update.message.reply_text(f"*(Feature Coming Soon)*")
        
    elif user_text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("🤔 Please use the menu buttons.")