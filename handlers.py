from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import MAINTENANCE_MODE, supabase
from menus import get_main_menu, get_inventory_menu, get_sales_menu, get_utang_menu

# -----------------------------------
# THE WIZARD STATES (Now with Rename Store)
# -----------------------------------
CATEGORY, ITEM_NAME, QUANTITY, PRICE, SALE_ITEM, SALE_QUANTITY, EDIT_SEARCH, EDIT_CHOOSE_FIELD, EDIT_NEW_VALUE, DELETE_SEARCH, DELETE_CONFIRM, RENAME_STORE = range(12)

# ==========================================
# 1. THE MANUAL ADD WIZARD
# ==========================================
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
    await update.message.reply_text("Great! What is the **Name** of the item?", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return ITEM_NAME

async def receive_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    context.user_data['item_name'] = text
    user_id = update.message.from_user.id

    try:
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", text).execute()
        existing_items = response.data

        if existing_items:
            existing_item = existing_items[0]
            context.user_data['existing_item'] = existing_item
            current_qty = existing_item['quantity']
            reply_msg = f"🔍 **We found this in your stock!**\nYou currently have **{current_qty} pcs** of {existing_item['item_name']}.\n\nHow many **NEW** pieces are you adding?"
        else:
            context.user_data['existing_item'] = None
            reply_msg = f"Got it: {text}.\n\nHow many **Pieces** are you adding? (Please type a number)"

        await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
        return QUANTITY
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error. Please try again.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text("⚠️ Oops! Please type a valid number. Try again:")
        return QUANTITY 

    added_qty = int(text)
    context.user_data['added_quantity'] = added_qty
    existing_item = context.user_data.get('existing_item')

    if existing_item:
        old_price = existing_item['wholesale_price']
        context.user_data['old_price'] = old_price
        reply_msg = f"Got it. Your current wholesale cost is **₱{old_price}**.\n\nKeep this price, or type a new one?"
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

    if text.startswith("Keep ₱"):
        wholesale_price = context.user_data['old_price']
    else:
        try:
            wholesale_price = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ Oops! Please type a valid price. Try again:")
            return PRICE

    category = context.user_data['category']
    item_name = context.user_data['item_name']
    added_qty = context.user_data['added_quantity']
    user_id = update.message.from_user.id
    retail_price = wholesale_price * 1.20 

    try:
        if existing_item:
            final_qty = existing_item['quantity'] + added_qty
            supabase.table("inventory").update({
                "quantity": final_qty, "wholesale_price": wholesale_price, "retail_price": retail_price
            }).eq("id", existing_item['id']).execute()
            success_msg = f"✅ **Restock Successful!**\nAdded {added_qty} more to {item_name}.\nYou now have **{final_qty} pcs**.\nSelling price: ₱{retail_price:.2f}."
        else:
            supabase.table("inventory").insert({
                "telegram_id": user_id, "category": category, "item_name": item_name,
                "quantity": added_qty, "wholesale_price": wholesale_price, "retail_price": retail_price
            }).execute()
            success_msg = f"✅ **New Item Added!**\nAdded {added_qty}x {item_name} to {category}.\nSelling price set to ₱{retail_price:.2f}."

        await update.message.reply_text(success_msg, reply_markup=get_inventory_menu())
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error: Could not save item.", reply_markup=get_inventory_menu())
    
    context.user_data.clear() 
    return ConversationHandler.END

# ==========================================
# 2. THE SALES CHECKOUT WIZARD
# ==========================================
async def record_sale_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛒 **Checkout Counter**\n\nWhat item did you sell? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return SALE_ITEM

async def receive_sale_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_sales_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    try:
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", f"%{text}%").execute()
        items = response.data

        if not items:
            await update.message.reply_text("⚠️ We couldn't find that item. Please check the spelling or click Cancel:", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
            return SALE_ITEM
        
        if len(items) > 1:
            exact_match = next((item for item in items if item['item_name'].lower() == text.lower()), None)
            if exact_match:
                sold_item = exact_match
            else:
                keyboard = [[item['item_name']] for item in items]
                keyboard.append(["❌ Cancel"])
                await update.message.reply_text("🔍 We found a few items. Please click the exact one:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return SALE_ITEM 
        else:
            sold_item = items[0]
        
        context.user_data['sold_item'] = sold_item
        reply_msg = f"🛒 **Selling: {sold_item['item_name']}**\n💰 Price: ₱{sold_item['retail_price']}\n📦 Current Stock: {sold_item['quantity']} pcs\n\nHow many pieces did you sell?"
        await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
        return SALE_QUANTITY

    except Exception as e:
        await update.message.reply_text("⚠️ Server Error.", reply_markup=get_sales_menu())
        return ConversationHandler.END

async def receive_sale_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_sales_menu())
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text("⚠️ Please type a valid number.")
        return SALE_QUANTITY

    qty_sold = int(text)
    sold_item = context.user_data['sold_item']
    current_stock = sold_item['quantity']

    if qty_sold > current_stock:
        await update.message.reply_text(f"⚠️ You only have {current_stock} pcs left! Please type a smaller number or Cancel.")
        return SALE_QUANTITY

    user_id = update.message.from_user.id
    new_stock = current_stock - qty_sold
    total_price = qty_sold * float(sold_item['retail_price'])

    try:
        supabase.table("inventory").update({"quantity": new_stock}).eq("id", sold_item['id']).execute()
        supabase.table("sales_log").insert({
            "telegram_id": user_id, "item_name": sold_item['item_name'],
            "quantity_sold": qty_sold, "total_amount": total_price, "payment_type": "Cash"
        }).execute()
        success_msg = f"✅ **Sale Recorded Successfully!**\n\nSold: {qty_sold}x {sold_item['item_name']}\nTotal Earned: **₱{total_price:.2f}**\nRemaining Stock: {new_stock} pcs."
        await update.message.reply_text(success_msg, reply_markup=get_sales_menu())
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error while saving sale.", reply_markup=get_sales_menu())

    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 3. THE EDIT ITEM WIZARD
# ==========================================
async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ **Edit Item**\n\nWhich item do you need to fix? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return EDIT_SEARCH

async def receive_edit_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    try:
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", f"%{text}%").execute()
        items = response.data

        if not items:
            await update.message.reply_text("⚠️ We couldn't find that item. Try again or click Cancel:", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
            return EDIT_SEARCH
        
        if len(items) > 1:
            exact_match = next((item for item in items if item['item_name'].lower() == text.lower()), None)
            if exact_match:
                edit_item = exact_match
            else:
                keyboard = [[item['item_name']] for item in items]
                keyboard.append(["❌ Cancel"])
                await update.message.reply_text("🔍 We found a few items. Please click the exact one:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return EDIT_SEARCH 
        else:
            edit_item = items[0]
        
        context.user_data['edit_item'] = edit_item
        keyboard = [["📦 Fix Quantity", "💰 Fix Wholesale Price"], ["❌ Cancel"]]
        reply_msg = f"✏️ **Editing: {edit_item['item_name']}**\nCurrent Quantity: {edit_item['quantity']}\nCurrent Cost: ₱{edit_item['wholesale_price']}\n\nWhat would you like to change?"
        await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return EDIT_CHOOSE_FIELD

    except Exception as e:
        await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

async def receive_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    context.user_data['edit_field'] = text
    await update.message.reply_text(f"Got it. What is the **NEW** value for {text.replace(' Fix ', '')}? (Type a number)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return EDIT_NEW_VALUE

async def receive_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    edit_item = context.user_data['edit_item']
    edit_field = context.user_data['edit_field']

    try:
        if edit_field == "📦 Fix Quantity":
            new_value = int(text)
            supabase.table("inventory").update({"quantity": new_value}).eq("id", edit_item['id']).execute()
            msg = f"✅ Success! **{edit_item['item_name']}** quantity is now **{new_value} pcs**."
            
        elif edit_field == "💰 Fix Wholesale Price":
            new_value = float(text)
            new_retail = new_value * 1.20 # Recalculate the 20% markup
            supabase.table("inventory").update({"wholesale_price": new_value, "retail_price": new_retail}).eq("id", edit_item['id']).execute()
            msg = f"✅ Success! **{edit_item['item_name']}** cost is now **₱{new_value}**.\nSelling price updated to **₱{new_retail:.2f}**."
            
        await update.message.reply_text(msg, reply_markup=get_inventory_menu())
    except ValueError:
        await update.message.reply_text("⚠️ Please type a valid number. Try again:")
        return EDIT_NEW_VALUE
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())

    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 4. THE DELETE ITEM WIZARD
# ==========================================
async def delete_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🗑️ **Delete Item**\n\nWhich item do you want to permanently remove? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
    return DELETE_SEARCH

async def receive_delete_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    try:
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", f"%{text}%").execute()
        items = response.data

        if not items:
            await update.message.reply_text("⚠️ We couldn't find that item.", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
            return DELETE_SEARCH
        
        if len(items) > 1:
            exact_match = next((item for item in items if item['item_name'].lower() == text.lower()), None)
            if exact_match:
                delete_item = exact_match
            else:
                keyboard = [[item['item_name']] for item in items]
                keyboard.append(["❌ Cancel"])
                await update.message.reply_text("🔍 We found a few items. Please click the one to delete:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return DELETE_SEARCH 
        else:
            delete_item = items[0]
        
        context.user_data['delete_item'] = delete_item
        keyboard = [["⚠️ YES, DELETE IT"], ["❌ Cancel"]]
        reply_msg = f"🗑️ **WARNING!**\nAre you sure you want to completely delete **{delete_item['item_name']}** from your database?"
        await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return DELETE_CONFIRM

    except Exception as e:
        await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

async def receive_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    delete_item = context.user_data['delete_item']

    if text == "⚠️ YES, DELETE IT":
        try:
            supabase.table("inventory").delete().eq("id", delete_item['id']).execute()
            await update.message.reply_text(f"✅ **Deleted!** {delete_item['item_name']} has been removed.", reply_markup=get_inventory_menu())
        except Exception as e:
            await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())
    else:
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())

    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 5. RENAME STORE WIZARD
# ==========================================
async def rename_store_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏷️ **Rename Your Store**\n\nWhat would you like to call your store?",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)
    )
    return RENAME_STORE

async def receive_new_store_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_main_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    
    try:
        supabase.table("stores").update({"store_name": text}).eq("telegram_id", user_id).execute()
        await update.message.reply_text(f"✅ **Success!**\nYour store is now named: **{text}**", reply_markup=get_main_menu())
    except Exception as e:
        print(f"Rename Error: {e}")
        await update.message.reply_text("⚠️ Server Error while renaming.", reply_markup=get_main_menu())
        
    return ConversationHandler.END

# ==========================================
# 6. THE NORMAL MENU BUTTONS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if MAINTENANCE_MODE:
        await update.message.reply_text("🛠️ System Maintenance. Please check back later!")
        return 
    
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    try:
        response = supabase.table("stores").select("*").eq("telegram_id", user_id).execute()
        
        if not response.data:
            supabase.table("stores").insert({
                "telegram_id": user_id,
                "owner_name": user_name,
                "store_name": f"{user_name}'s Sari-Sari Store" 
            }).execute()
            print(f"🎉 New store registered: {user_name}'s Sari-Sari Store")

        await update.message.reply_text(f"👋 Welcome to InventoryLink, {user_name}!\n\nMain Menu:", reply_markup=get_main_menu())
    
    except Exception as e:
        print(f"Registration Error: {e}")
        await update.message.reply_text("⚠️ Server Error during registration.", reply_markup=get_main_menu())


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
        about_text = (
            "🤖 **About InventoryLink**\n\n"
            "InventoryLink is a simple Telegram bot that helps Sari-Sari store owners track stock and sales directly from their phones. "
            "We built it to replace messy notebooks with a fast, cloud-synced digital assistant."
        )
        await update.message.reply_text(about_text, reply_markup=get_main_menu())
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

    # ==========================================
    # 🔗 THE DASHBOARD MAGIC LINK LOGIC
    # ==========================================
    elif user_text == "📊 View Web Dashboard":
        base_url = "http://localhost:8501" 
        magic_link = f"{base_url}/?store_id={user_id}"
        reply_msg = (
            "📊 **Your Personal Dashboard is ready!**\n\n"
            "Click the secure link below to view your real-time store analytics:\n"
            f"👉 {magic_link}\n\n"
            "*(Do not share this link with anyone!)*"
        )
        await update.message.reply_text(reply_msg, reply_markup=get_main_menu())

    elif user_text in ["📸 Add via AI (Photo)", "📈 View Sales Report", "➕ Add New Utang", "💳 Record Payment"]:
        await update.message.reply_text(f"*(Feature Coming Soon)*")
        
    elif user_text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("🤔 Please use the menu buttons.")