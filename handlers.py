from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import os
import re
from datetime import datetime, timezone, timedelta

from config import MAINTENANCE_MODE, supabase
from menus import get_main_menu, get_inventory_menu, get_sales_menu, get_sales_report_menu, get_utang_menu, get_settings_menu
from ai_scanner import analyze_receipt

# -----------------------------------
# THE WIZARD STATES
# -----------------------------------
CATEGORY, ITEM_NAME, QUANTITY, PRICE, SALE_ITEM, SALE_QUANTITY, EDIT_SEARCH, EDIT_CHOOSE_FIELD, EDIT_NEW_VALUE, DELETE_SEARCH, DELETE_CONFIRM, RENAME_STORE, AI_PHOTO, AI_CONFIRM, DELETE_STORE, UTANG_CUSTOMER, UTANG_CONTACT, UTANG_ITEM, UTANG_QTY, UTANG_CART_ACTION, UTANG_NOTES, PAYMENT_CUSTOMER, PAYMENT_AMOUNT, SEARCH_CUSTOMER_QUERY, EDIT_DEBT_LIMIT, EDIT_STOCK_LIMIT, EDIT_MARKUP_PERCENT, CATEGORY_ACTION, CATEGORY_ADD_NAME, CATEGORY_RENAME_TARGET, CATEGORY_RENAME_VALUE, CATEGORY_DELETE_TARGET, GET_STARTING_POT, GET_ACTUAL_CASH, GET_AUDIT_NOTES = range(35)

PHT = timezone(timedelta(hours=8))
DEFAULT_LOW_STOCK_LIMIT = 5
DEFAULT_RETAIL_MARKUP_PERCENT = 20
INVENTORY_CATEGORIES = [
    "🥤 Beverages",
    "🍽️ Food & Snacks",
    "🌾 Rice, Grains & Staples",
    "🧂 Cooking & Condiments",
    "🥫 Canned & Packaged Goods",
    "🧼 Household & Cleaning",
    "🧴 Personal Care",
    "💊 Health & Baby Care",
    "📱 Load & Services",
    "🧾 School & Office Supplies",
    "📦 Others",
]


def _store_categories(telegram_id):
    merged = INVENTORY_CATEGORIES.copy()
    seen = {category.lower() for category in merged}
    try:
        response = supabase.table("stores").select("inventory_categories").eq("telegram_id", telegram_id).limit(1).execute()
        if response.data:
            categories = response.data[0].get("inventory_categories")
            if isinstance(categories, list) and categories:
                for category in categories:
                    name = str(category).strip()
                    key = name.lower()
                    if name and key not in seen:
                        merged.append(name)
                        seen.add(key)
    except Exception as error:
        print(f"Category settings lookup warning: {error}")
    return merged


def _save_store_categories(telegram_id, categories):
    cleaned = []
    seen = set()
    for category in categories:
        name = str(category).strip()
        key = name.lower()
        if name and key not in seen:
            cleaned.append(name)
            seen.add(key)
    if "📦 Others" not in cleaned:
        cleaned.append("📦 Others")
    supabase.table("stores").update({"inventory_categories": cleaned}).eq("telegram_id", telegram_id).execute()
    return cleaned


def _category_keyboard(telegram_id=None, include_cancel=True):
    categories = _store_categories(telegram_id) if telegram_id else INVENTORY_CATEGORIES
    rows = [categories[i:i + 2] for i in range(0, len(categories), 2)]
    if include_cancel:
        rows.append(["❌ Cancel"])
    return rows


def _normalize_category(value, telegram_id=None):
    if not value:
        return "📦 Others"

    cleaned = str(value).strip().lower()
    categories = _store_categories(telegram_id) if telegram_id else INVENTORY_CATEGORIES
    for category in categories:
        label = re.sub(r"^[^\w#]+", "", category).strip().lower()
        if cleaned == category.lower() or cleaned == label:
            return category

    aliases = {
        "beverage": "🥤 Beverages",
        "beverages": "🥤 Beverages",
        "drinks": "🥤 Beverages",
        "soft drinks": "🥤 Beverages",
        "juice": "🥤 Beverages",
        "water": "🥤 Beverages",
        "coffee": "🥤 Beverages",
        "milk": "🥤 Beverages",
        "creamer": "🥤 Beverages",
        "snacks": "🍽️ Food & Snacks",
        "food": "🍽️ Food & Snacks",
        "foods": "🍽️ Food & Snacks",
        "chips": "🍽️ Food & Snacks",
        "junk food": "🍽️ Food & Snacks",
        "biscuits": "🍽️ Food & Snacks",
        "bread": "🍽️ Food & Snacks",
        "noodles": "🍽️ Food & Snacks",
        "instant noodles": "🍽️ Food & Snacks",
        "rice": "🌾 Rice, Grains & Staples",
        "grains": "🌾 Rice, Grains & Staples",
        "staples": "🌾 Rice, Grains & Staples",
        "sugar": "🌾 Rice, Grains & Staples",
        "flour": "🌾 Rice, Grains & Staples",
        "salt": "🧂 Cooking & Condiments",
        "soy sauce": "🧂 Cooking & Condiments",
        "vinegar": "🧂 Cooking & Condiments",
        "oil": "🧂 Cooking & Condiments",
        "condiments": "🧂 Cooking & Condiments",
        "canned goods": "🥫 Canned & Packaged Goods",
        "canned food": "🥫 Canned & Packaged Goods",
        "packaged goods": "🥫 Canned & Packaged Goods",
        "cleaning": "🧼 Household & Cleaning",
        "laundry": "🧼 Household & Cleaning",
        "detergent": "🧼 Household & Cleaning",
        "dishwashing": "🧼 Household & Cleaning",
        "household": "🧼 Household & Cleaning",
        "toiletries": "🧴 Personal Care",
        "personal care": "🧴 Personal Care",
        "soap": "🧴 Personal Care",
        "shampoo": "🧴 Personal Care",
        "toothpaste": "🧴 Personal Care",
        "medicine": "💊 Health & Baby Care",
        "health": "💊 Health & Baby Care",
        "baby care": "💊 Health & Baby Care",
        "diapers": "💊 Health & Baby Care",
        "cigarettes": "🚬 Tobacco",
        "tobacco": "🚬 Tobacco",
        "load": "📱 Load & Services",
        "e-load": "📱 Load & Services",
        "services": "📱 Load & Services",
        "school supplies": "🧾 School & Office Supplies",
        "office supplies": "🧾 School & Office Supplies",
    }
    return aliases.get(cleaned, "📦 Others")


def _format_currency(value):
    return f"₱{float(value):,.2f}"


def _parse_iso_datetime(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _clear_credit_context(context: ContextTypes.DEFAULT_TYPE):
    for key in [
        "utang_account",
        "utang_customer_name",
        "utang_contact_info",
        "utang_cart",
        "utang_selected_item",
        "utang_pre_balance",
        "payment_target_account",
        "payment_candidates",
    ]:
        context.user_data.pop(key, None)


def _now_pht():
    return datetime.now(PHT)


def _parse_pht_datetime(value):
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return None
    return parsed.astimezone(PHT)


def _sales_rows_for_store(telegram_id):
    response = supabase.table("sales_log").select("*").eq("telegram_id", telegram_id).execute()
    return response.data or []


def _inventory_rows_for_store(telegram_id):
    response = supabase.table("inventory").select("item_name, quantity, wholesale_price, retail_price").eq("telegram_id", telegram_id).execute()
    return response.data or []


def _store_low_stock_limit(telegram_id):
    try:
        response = supabase.table("stores").select("low_stock_limit").eq("telegram_id", telegram_id).limit(1).execute()
        if response.data:
            return int(response.data[0].get("low_stock_limit") or DEFAULT_LOW_STOCK_LIMIT)
    except Exception as error:
        print(f"Low stock limit lookup warning: {error}")
    return DEFAULT_LOW_STOCK_LIMIT


def _store_retail_markup_percent(telegram_id):
    try:
        response = supabase.table("stores").select("retail_markup_percent").eq("telegram_id", telegram_id).limit(1).execute()
        if response.data:
            return float(response.data[0].get("retail_markup_percent") or DEFAULT_RETAIL_MARKUP_PERCENT)
    except Exception as error:
        print(f"Selling price percentage lookup warning: {error}")
    return DEFAULT_RETAIL_MARKUP_PERCENT


def _retail_price_from_wholesale(wholesale_price, telegram_id):
    markup_percent = _store_retail_markup_percent(telegram_id)
    return float(wholesale_price) * (1 + (markup_percent / 100))


async def _send_low_stock_alert(update: Update, telegram_id, item_name, new_stock):
    limit = _store_low_stock_limit(telegram_id)
    if int(new_stock) > limit:
        return

    if int(new_stock) <= 0:
        status = "OUT OF STOCK"
        action = "Restock this item as soon as possible."
    else:
        status = "LOW STOCK"
        action = f"Stock is at or below your alert limit of {limit} pcs."

    await update.effective_message.reply_text(
        "🚨 AUTOMATED STOCK ALERT\n\n"
        f"Item: {item_name}\n"
        f"Status: {status}\n"
        f"Remaining Stock: {int(new_stock)} pcs\n"
        f"Alert Limit: {limit} pcs\n\n"
        f"{action}"
    )


def _sales_rows_for_date(telegram_id, target_date, payment_type=None):
    rows = []
    for row in _sales_rows_for_store(telegram_id):
        sale_dt = _parse_pht_datetime(row.get("sale_date"))
        if not sale_dt or sale_dt.date() != target_date:
            continue
        if payment_type and row.get("payment_type") != payment_type:
            continue
        rows.append(row)
    return rows


def _inventory_wholesale_map(telegram_id):
    return {
        row.get("item_name"): float(row.get("wholesale_price") or 0)
        for row in _inventory_rows_for_store(telegram_id)
        if row.get("item_name")
    }


def _summarize_sales_rows(sales_rows, wholesale_map):
    total_cash = 0.0
    total_credit = 0.0
    total_revenue = 0.0
    total_profit = 0.0
    item_totals = {}

    for row in sales_rows:
        amount = float(row.get("total_amount") or 0)
        qty = int(row.get("quantity_sold") or 0)
        item_name = row.get("item_name") or "Unknown"
        payment_type = (row.get("payment_type") or "Cash").strip().lower()

        total_revenue += amount
        if payment_type == "credit":
            total_credit += amount
        else:
            total_cash += amount

        cogs = wholesale_map.get(item_name, 0.0) * qty
        total_profit += amount - cogs

        if item_name not in item_totals:
            item_totals[item_name] = {"quantity": 0, "revenue": 0.0}
        item_totals[item_name]["quantity"] += qty
        item_totals[item_name]["revenue"] += amount

    top_items = sorted(item_totals.items(), key=lambda pair: (pair[1]["quantity"], pair[1]["revenue"]), reverse=True)

    return {
        "cash": total_cash,
        "credit": total_credit,
        "revenue": total_revenue,
        "profit": total_profit,
        "count": len(sales_rows),
        "top_items": top_items,
    }


def _audit_summary_message(starting_pot, cash_sales, expected_cash, actual_cash, discrepancy, notes):
    status_emoji = "🟢" if discrepancy == 0 else "🚨" if discrepancy < 0 else "🟡"
    status_text = (
        "PERFECTLY RECONCILED"
        if discrepancy == 0
        else "CASH SHORTAGE (LEAKAGE)"
        if discrepancy < 0
        else "OVER-CASH DISCREPANCY"
    )
    notes_text = notes if notes else "None"
    return (
        f"🔒 STORE DRAWER AUDIT COMPLETE\n"
        f"📅 Date: {datetime.now(PHT).strftime('%B %d, %Y')}\n"
        f"─────────────────────────\n"
        f"📥 Starting Change Pot: {_format_currency(starting_pot)}\n"
        f"📈 Expected Cash Sales: {_format_currency(cash_sales)}\n"
        f"💵 Conceptual Total: {_format_currency(expected_cash)}\n"
        f"─────────────────────────\n"
        f"🔎 Actual Cash Counted: {_format_currency(actual_cash)}\n"
        f"{status_emoji} Status: {status_text}\n"
        f"📊 Discrepancy: {_format_currency(discrepancy)}\n"
        f"─────────────────────────\n"
        f"📝 Audit Note: {notes_text}\n"
        f"─────────────────────────\n"
        f"Excellent! Your EOD numbers are secured."
    )


def _sales_report_message(telegram_id, report_date):
    wholesale_map = _inventory_wholesale_map(telegram_id)
    rows = _sales_rows_for_date(telegram_id, report_date)
    summary = _summarize_sales_rows(rows, wholesale_map)
    yesterday_summary = _summarize_sales_rows(_sales_rows_for_date(telegram_id, report_date - timedelta(days=1)), wholesale_map)

    lines = [
        f"📊 SALES REPORT: {report_date.strftime('%B %d, %Y')}",
        "─────────────────────────",
        f"💰 Total Cash in Drawer: {_format_currency(summary['cash'])}",
        f"📝 Uncollected Credit (Utang): {_format_currency(summary['credit'])}",
        f"📈 Total Gross Revenue: {_format_currency(summary['revenue'])}",
        f"✨ Estimated Profit (Tubo): {_format_currency(summary['profit'])}",
        f"🧾 Total Transactions: {summary['count']} sales logged",
    ]

    if yesterday_summary["revenue"] > 0:
        dod = ((summary["revenue"] - yesterday_summary["revenue"]) / yesterday_summary["revenue"]) * 100
        direction = "up" if dod >= 0 else "down"
        lines.append(f"📊 DoD Performance: {dod:.2f}% {direction} vs previous day")
    else:
        lines.append("📊 DoD Performance: Baseline unavailable (no sales on previous day)")

    lines.append("─────────────────────────")
    if not rows:
        lines.append("No sales were recorded on this day.")
    else:
        top_items = summary["top_items"][:5]
        if top_items:
            lines.append("🏆 Top Items:")
            for idx, (item_name, stats) in enumerate(top_items, start=1):
                lines.append(f"{idx}. {item_name} — {int(stats['quantity'])} pcs | {_format_currency(stats['revenue'])}")

        out_of_stock = [row for row in _inventory_rows_for_store(telegram_id) if int(row.get("quantity") or 0) <= 0]
        lines.append(f"🚨 Out-of-Stock Items: {len(out_of_stock)}")

    return "\n".join(lines)


async def _send_audit_actual_cash_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expected_cash = context.user_data["starting_pot"] + context.user_data["today_cash_sales"]
    context.user_data["expected_cash"] = expected_cash
    await update.effective_message.reply_text(
        f"📝 Starting Pot: {_format_currency(context.user_data['starting_pot'])}\n"
        f"📈 Logged Today's Cash Sales: {_format_currency(context.user_data['today_cash_sales'])}\n"
        f"💰 Expected Cash in Drawer: {_format_currency(expected_cash)}\n\n"
        "Now, count all physical paper bills and coins currently inside your drawer.\n"
        "Enter the total counted amount (Actual Cash in hand):",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel Audit"]], resize_keyboard=True),
    )


async def _save_daily_audit(update: Update, context: ContextTypes.DEFAULT_TYPE, notes):
    user_id = update.effective_user.id
    try:
        supabase.table("daily_drawer_audits").insert({
            "telegram_id": user_id,
            "starting_drawer_pot": context.user_data["starting_pot"],
            "expected_cash": context.user_data["expected_cash"],
            "actual_cash_counted": context.user_data["actual_cash"],
            "discrepancy": context.user_data["discrepancy"],
            "audit_notes": notes,
        }).execute()

        summary = _audit_summary_message(
            context.user_data["starting_pot"],
            context.user_data["today_cash_sales"],
            context.user_data["expected_cash"],
            context.user_data["actual_cash"],
            context.user_data["discrepancy"],
            notes,
        )
        await update.effective_message.reply_text(summary, reply_markup=get_sales_menu())
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error saving audit to database: {str(e)}")
    finally:
        context.user_data.pop("starting_pot", None)
        context.user_data.pop("today_cash_sales", None)
        context.user_data.pop("expected_cash", None)
        context.user_data.pop("actual_cash", None)
        context.user_data.pop("discrepancy", None)


async def cancel_daily_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text("❌ Audit cancelled.", reply_markup=get_sales_menu())
    return ConversationHandler.END

# ==========================================
# 1. THE MANUAL ADD WIZARD
# ==========================================
async def add_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Let's manage your stock!\n\nFirst, what Category does this item belong to?",
        reply_markup=ReplyKeyboardMarkup(_category_keyboard(update.message.from_user.id), resize_keyboard=True)
    )
    return CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END
    
    context.user_data['category'] = _normalize_category(text, update.message.from_user.id)
    await update.message.reply_text("Great! What is the Name of the item?", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
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
            reply_msg = f"🔍 We found this in your stock!\nYou currently have {current_qty} pcs of {existing_item['item_name']}.\n\nHow many NEW pieces are you adding?"
        else:
            context.user_data['existing_item'] = None
            reply_msg = f"Got it: {text}.\n\nHow many Pieces are you adding? (Please type a number)"

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
        reply_msg = f"Got it. Your current wholesale cost is ₱{old_price}.\n\nKeep this price, or type a new one?"
        keyboard = [[f"Keep ₱{old_price}"], ["❌ Cancel"]]
    else:
        reply_msg = "Awesome. Finally, what is the Wholesale Cost per piece? (e.g., 60 or 15.50)"
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
    retail_price = _retail_price_from_wholesale(wholesale_price, user_id)

    try:
        if existing_item:
            final_qty = existing_item['quantity'] + added_qty
            supabase.table("inventory").update({
                "quantity": final_qty, "wholesale_price": wholesale_price, "retail_price": retail_price
            }).eq("id", existing_item['id']).execute()
            success_msg = f"✅ Restock Successful!\nAdded {added_qty} more to {item_name}.\nYou now have {final_qty} pcs.\nSelling price: ₱{retail_price:.2f}."
        else:
            supabase.table("inventory").insert({
                "telegram_id": user_id, "category": category, "item_name": item_name,
                "quantity": added_qty, "wholesale_price": wholesale_price, "retail_price": retail_price
            }).execute()
            success_msg = f"✅ New Item Added!\nAdded {added_qty}x {item_name} to {category}.\nSelling price set to ₱{retail_price:.2f}."

        await update.message.reply_text(success_msg, reply_markup=get_inventory_menu())
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error: Could not save item.", reply_markup=get_inventory_menu())
    
    context.user_data.clear() 
    return ConversationHandler.END

# ==========================================
# 2. THE SALES CHECKOUT WIZARD
# ==========================================
async def record_sale_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛒 Checkout Counter\n\nWhat item did you sell? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
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
        reply_msg = f"🛒 Selling: {sold_item['item_name']}\n💰 Price: ₱{sold_item['retail_price']}\n📦 Current Stock: {sold_item['quantity']} pcs\n\nHow many pieces did you sell?"
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
        success_msg = f"✅ Sale Recorded Successfully!\n\nSold: {qty_sold}x {sold_item['item_name']}\nTotal Earned: ₱{total_price:.2f}\nRemaining Stock: {new_stock} pcs."
        await update.message.reply_text(success_msg, reply_markup=get_sales_menu())
        await _send_low_stock_alert(update, user_id, sold_item['item_name'], new_stock)
    except Exception as e:
        await update.message.reply_text("⚠️ Server Error while saving sale.", reply_markup=get_sales_menu())

    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 3. THE EDIT ITEM WIZARD
# ==========================================
async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ Edit Item\n\nWhich item do you need to fix? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
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
        keyboard = [["📦 Fix Quantity", "💰 Fix Wholesale Price"], ["🏷️ Fix Category"], ["❌ Cancel"]]
        reply_msg = (
            f"✏️ Editing: {edit_item['item_name']}\n"
            f"Current Category: {edit_item.get('category', '📦 Others')}\n"
            f"Current Quantity: {edit_item['quantity']}\n"
            f"Current Cost: ₱{edit_item['wholesale_price']}\n\n"
            "What would you like to change?"
        )
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
    if text == "🏷️ Fix Category":
        await update.message.reply_text(
            "Choose the new category:",
            reply_markup=ReplyKeyboardMarkup(_category_keyboard(update.message.from_user.id), resize_keyboard=True),
        )
    else:
        await update.message.reply_text(f"Got it. What is the NEW value for {text.replace(' Fix ', '')}? (Type a number)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
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
            msg = f"✅ Success! {edit_item['item_name']} quantity is now {new_value} pcs."
            
        elif edit_field == "💰 Fix Wholesale Price":
            new_value = float(text)
            new_retail = _retail_price_from_wholesale(new_value, update.message.from_user.id)
            supabase.table("inventory").update({"wholesale_price": new_value, "retail_price": new_retail}).eq("id", edit_item['id']).execute()
            msg = f"✅ Success! {edit_item['item_name']} cost is now ₱{new_value}.\nSelling price updated to ₱{new_retail:.2f}."

        elif edit_field == "🏷️ Fix Category":
            new_category = _normalize_category(text, update.message.from_user.id)
            supabase.table("inventory").update({"category": new_category}).eq("id", edit_item['id']).execute()
            msg = f"✅ Success! {edit_item['item_name']} moved to {new_category}."
            
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
    await update.message.reply_text("🗑️ Delete Item\n\nWhich item do you want to permanently remove? (Type the name)", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))
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
        reply_msg = f"🗑️ WARNING!\nAre you sure you want to completely delete {delete_item['item_name']} from your database?"
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
            await update.message.reply_text(f"✅ Deleted! {delete_item['item_name']} has been removed.", reply_markup=get_inventory_menu())
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
        "🏷️ Rename Your Store\n\nWhat would you like to call your store?",
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
        await update.message.reply_text(f"✅ Success!\nYour store is now named: {text}", reply_markup=get_main_menu())
    except Exception as e:
        print(f"Rename Error: {e}")
        await update.message.reply_text("⚠️ Server Error while renaming.", reply_markup=get_main_menu())
        
    return ConversationHandler.END


async def edit_debt_limit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        store = supabase.table("stores").select("debt_grace_period_days").eq("telegram_id", user_id).limit(1).execute()
        current_days = 30
        if store.data:
            current_days = int(store.data[0].get("debt_grace_period_days") or 30)

        await update.message.reply_text(
            f"⏱️ Edit Debt Limit\n\nCurrent grace limit: {current_days} day(s).\nEnter new limit in days (1-365):",
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
        )
        return EDIT_DEBT_LIMIT
    except Exception:
        await update.message.reply_text("⚠️ Server Error while loading settings.", reply_markup=get_settings_menu())
        return ConversationHandler.END


async def receive_debt_limit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_settings_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text("⚠️ Please enter a whole number between 1 and 365.")
        return EDIT_DEBT_LIMIT

    days = int(text)
    if days < 1 or days > 365:
        await update.message.reply_text("⚠️ Limit must be between 1 and 365 days.")
        return EDIT_DEBT_LIMIT

    user_id = update.message.from_user.id
    try:
        supabase.table("stores").update({"debt_grace_period_days": days}).eq("telegram_id", user_id).execute()
        await update.message.reply_text(
            f"✅ Debt grace limit updated to {days} day(s).",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"Debt limit update error: {e}")
        await update.message.reply_text("⚠️ Failed to update debt limit.", reply_markup=get_settings_menu())
        return ConversationHandler.END


async def edit_stock_limit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    current_limit = _store_low_stock_limit(user_id)

    await update.message.reply_text(
        f"🚨 Edit Stock Alert Limit\n\nCurrent alert limit: {current_limit} pcs.\n"
        "The bot will send an automatic alert when an item drops to this number or below.\n\n"
        "Enter new limit in pieces (1-999):",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
    )
    return EDIT_STOCK_LIMIT


async def receive_stock_limit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_settings_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text("⚠️ Please enter a whole number between 1 and 999.")
        return EDIT_STOCK_LIMIT

    limit = int(text)
    if limit < 1 or limit > 999:
        await update.message.reply_text("⚠️ Limit must be between 1 and 999 pieces.")
        return EDIT_STOCK_LIMIT

    user_id = update.message.from_user.id
    try:
        supabase.table("stores").update({"low_stock_limit": limit}).eq("telegram_id", user_id).execute()
        await update.message.reply_text(
            f"✅ Low-stock alert limit updated to {limit} pcs.",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"Stock limit update error: {e}")
        await update.message.reply_text(
            "⚠️ Failed to update stock alert limit. Please make sure the stores.low_stock_limit column exists in Supabase.",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END


async def edit_markup_percent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    current_percent = _store_retail_markup_percent(user_id)

    await update.message.reply_text(
        f"💸 Edit Selling Price Percentage\n\nCurrent markup: {current_percent:g}% above wholesale cost.\n"
        "Example: if wholesale is ₱10 and markup is 20%, selling price becomes ₱12.\n\n"
        "Enter new percentage (0-500):",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
    )
    return EDIT_MARKUP_PERCENT


async def receive_markup_percent_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_settings_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    try:
        markup_percent = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid percentage, like 20 or 12.5.")
        return EDIT_MARKUP_PERCENT

    if markup_percent < 0 or markup_percent > 500:
        await update.message.reply_text("⚠️ Percentage must be between 0 and 500.")
        return EDIT_MARKUP_PERCENT

    user_id = update.message.from_user.id
    try:
        supabase.table("stores").update({"retail_markup_percent": markup_percent}).eq("telegram_id", user_id).execute()

        items = supabase.table("inventory").select("id, wholesale_price").eq("telegram_id", user_id).execute()
        updated_count = 0
        for item in items.data or []:
            wholesale = float(item.get("wholesale_price") or 0)
            new_retail = wholesale * (1 + (markup_percent / 100))
            supabase.table("inventory").update({"retail_price": new_retail}).eq("id", item["id"]).eq("telegram_id", user_id).execute()
            updated_count += 1

        await update.message.reply_text(
            f"✅ Selling price markup updated to {markup_percent:g}%.\n"
            f"Updated selling prices for {updated_count} inventory item(s).",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"Selling price percentage update error: {e}")
        await update.message.reply_text(
            "⚠️ Failed to update selling price percentage. Please make sure the stores.retail_markup_percent column exists in Supabase.",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END


def _category_management_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["👀 View Categories", "➕ Add Category"],
            ["✏️ Rename Category", "🗑️ Delete Category"],
            ["🔙 Back to Settings"],
        ],
        resize_keyboard=True,
    )


async def manage_categories_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗂️ Category Manager\n\nChoose what you want to do:",
        reply_markup=_category_management_keyboard(),
    )
    return CATEGORY_ACTION


async def process_category_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.message.from_user.id

    if text == "🔙 Back to Settings":
        await update.message.reply_text("⚙️ Settings", reply_markup=get_settings_menu())
        return ConversationHandler.END

    if text == "👀 View Categories":
        categories = _store_categories(user_id)
        lines = ["🗂️ Your Inventory Categories", "─────────────────────────"]
        lines.extend([f"{idx}. {category}" for idx, category in enumerate(categories, start=1)])
        await update.message.reply_text("\n".join(lines), reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION

    if text == "➕ Add Category":
        await update.message.reply_text(
            "➕ Add Category\n\nType the new category name:",
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True),
        )
        return CATEGORY_ADD_NAME

    if text == "✏️ Rename Category":
        await update.message.reply_text(
            "✏️ Rename Category\n\nChoose the category to rename:",
            reply_markup=ReplyKeyboardMarkup(_category_keyboard(user_id), resize_keyboard=True),
        )
        return CATEGORY_RENAME_TARGET

    if text == "🗑️ Delete Category":
        await update.message.reply_text(
            "🗑️ Delete Category\n\nChoose the category to delete. Items in that category will move to 📦 Others.",
            reply_markup=ReplyKeyboardMarkup(_category_keyboard(user_id), resize_keyboard=True),
        )
        return CATEGORY_DELETE_TARGET

    await update.message.reply_text("⚠️ Please choose an option from the Category Manager.", reply_markup=_category_management_keyboard())
    return CATEGORY_ACTION


async def receive_category_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("🗂️ Category Manager", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION

    if not text:
        await update.message.reply_text("⚠️ Category name cannot be blank.")
        return CATEGORY_ADD_NAME

    user_id = update.message.from_user.id
    categories = _store_categories(user_id)
    if any(category.lower() == text.lower() for category in categories):
        await update.message.reply_text("⚠️ That category already exists. Type a different name.")
        return CATEGORY_ADD_NAME

    try:
        _save_store_categories(user_id, categories + [text])
        await update.message.reply_text(f"✅ Added category: {text}", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION
    except Exception as e:
        print(f"Add category error: {e}")
        await update.message.reply_text(
            "⚠️ Failed to save category. Please make sure the stores.inventory_categories column exists in Supabase.",
            reply_markup=get_settings_menu(),
        )
        return ConversationHandler.END


async def receive_category_rename_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("🗂️ Category Manager", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION

    user_id = update.message.from_user.id
    category = _normalize_category(text, user_id)
    if category == "📦 Others" and text != "📦 Others":
        await update.message.reply_text("⚠️ Please choose an existing category.", reply_markup=ReplyKeyboardMarkup(_category_keyboard(user_id), resize_keyboard=True))
        return CATEGORY_RENAME_TARGET

    context.user_data["category_rename_target"] = category
    await update.message.reply_text(
        f"Renaming: {category}\n\nType the new category name:",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True),
    )
    return CATEGORY_RENAME_VALUE


async def receive_category_rename_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        context.user_data.pop("category_rename_target", None)
        await update.message.reply_text("🗂️ Category Manager", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION

    if not text:
        await update.message.reply_text("⚠️ Category name cannot be blank.")
        return CATEGORY_RENAME_VALUE

    user_id = update.message.from_user.id
    old_category = context.user_data.get("category_rename_target")
    categories = _store_categories(user_id)
    if any(category.lower() == text.lower() for category in categories if category != old_category):
        await update.message.reply_text("⚠️ That category already exists. Type a different name.")
        return CATEGORY_RENAME_VALUE

    try:
        renamed = [text if category == old_category else category for category in categories]
        _save_store_categories(user_id, renamed)
        supabase.table("inventory").update({"category": text}).eq("telegram_id", user_id).eq("category", old_category).execute()
        context.user_data.pop("category_rename_target", None)
        await update.message.reply_text(f"✅ Renamed {old_category} to {text}.", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION
    except Exception as e:
        print(f"Rename category error: {e}")
        await update.message.reply_text("⚠️ Failed to rename category.", reply_markup=get_settings_menu())
        return ConversationHandler.END


async def receive_category_delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("🗂️ Category Manager", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION

    user_id = update.message.from_user.id
    category = _normalize_category(text, user_id)
    categories = _store_categories(user_id)

    if category == "📦 Others":
        await update.message.reply_text("⚠️ 📦 Others is required and cannot be deleted.", reply_markup=_category_management_keyboard())
        return CATEGORY_ACTION
    if category not in categories:
        await update.message.reply_text("⚠️ Please choose an existing category.", reply_markup=ReplyKeyboardMarkup(_category_keyboard(user_id), resize_keyboard=True))
        return CATEGORY_DELETE_TARGET

    try:
        _save_store_categories(user_id, [existing for existing in categories if existing != category])
        supabase.table("inventory").update({"category": "📦 Others"}).eq("telegram_id", user_id).eq("category", category).execute()
        await update.message.reply_text(
            f"✅ Deleted category: {category}\nItems that used it were moved to 📦 Others.",
            reply_markup=_category_management_keyboard(),
        )
        return CATEGORY_ACTION
    except Exception as e:
        print(f"Delete category error: {e}")
        await update.message.reply_text("⚠️ Failed to delete category.", reply_markup=get_settings_menu())
        return ConversationHandler.END


# ==========================================
# 6. DELETE STORE WIZARD
# ==========================================
async def delete_store_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧾 Delete Store (Permanent)\n\nThis will permanently delete your store and all its inventory and sales data.\nType YES to confirm or click ❌ Cancel.",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)
    )
    return DELETE_STORE


async def receive_delete_store_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_main_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    if text.strip().upper() == "YES":
        try:
            supabase.table("sales_log").delete().eq("telegram_id", user_id).execute()
            supabase.table("inventory").delete().eq("telegram_id", user_id).execute()
            supabase.table("stores").delete().eq("telegram_id", user_id).execute()
            await update.message.reply_text(
                "✅ Store Deleted. All data removed.\n\nPlease send /start again to register a new store.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            print(f"Delete Store Error: {e}")
            await update.message.reply_text("⚠️ Server Error while deleting store.", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("❌ Confirmation not recognized. Cancelled.", reply_markup=get_main_menu())

    return ConversationHandler.END

# ==========================================
# 7. THE GEMINI AI SCANNER WIZARD
# ==========================================
async def ai_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 AI Receipt Scanner\n\nPlease send a clear photo of your receipt or invoice.",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)
    )
    return AI_PHOTO

async def receive_ai_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send a photo, or click Cancel.")
        return AI_PHOTO

    processing_msg = await update.message.reply_text("⏳ Gemini AI is analyzing your receipt... Please wait.")
    file_path = f"temp_receipt_{update.message.from_user.id}.jpg"

    try:
        # 1. Download the photo
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(file_path)

        # 2. Analyze with Gemini
        scanned_items = analyze_receipt(file_path, _store_categories(update.message.from_user.id))

        if not scanned_items:
            await processing_msg.edit_text("⚠️ Sorry, I couldn't extract any items from that image. Please try a clearer photo or add manually.")
            return ConversationHandler.END

        # 3. Save data to memory and ask user to confirm
        context.user_data['scanned_items'] = scanned_items
        
        reply_text = "✨ Gemini found these items:\n\n"
        for item in scanned_items:
            category = _normalize_category(item.get("category"), update.message.from_user.id)
            item["category"] = category
            reply_text += f"▪️ {item.get('quantity', 1)}x {item.get('item_name', 'Unknown')} - {category} (₱{item.get('wholesale_price', 0)})\n"
        reply_text += "\nDo you want to add all these to your inventory?"
        
        keyboard = [["✅ Yes, Add All"], ["❌ Cancel"]]
        await processing_msg.delete()
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return AI_CONFIRM

    except Exception as e:
        # If ANYTHING goes wrong, we catch it here so the bot doesn't freeze!
        print(f"Error during AI processing: {e}")
        await processing_msg.edit_text("⚠️ An error occurred while reading the receipt. Please try again or type /start.")
        return ConversationHandler.END

    finally:
        # This block runs no matter what, guaranteeing the file is cleaned up.
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                print(f"Could not delete temp file: {cleanup_error}")

async def confirm_ai_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_inventory_menu())
        return ConversationHandler.END

    if text == "✅ Yes, Add All":
        scanned_items = context.user_data.get('scanned_items', [])
        user_id = update.message.from_user.id
        
        success_count = 0
        for item in scanned_items:
            try:
                qty = int(item.get('quantity', 1))
                wholesale = float(item.get('wholesale_price', 0))
                retail = _retail_price_from_wholesale(wholesale, user_id)
                name = item.get('item_name', 'Unknown Item')
                category = _normalize_category(item.get("category"), user_id)
                
                supabase.table("inventory").insert({
                    "telegram_id": user_id,
                    "category": category,
                    "item_name": name,
                    "quantity": qty,
                    "wholesale_price": wholesale,
                    "retail_price": retail
                }).execute()
                success_count += 1
            except Exception as e:
                print(f"Error saving AI item: {e}")

        await update.message.reply_text(f"✅ Success! Added {success_count} items to your inventory.", reply_markup=get_inventory_menu())
    
    context.user_data.clear()
    return ConversationHandler.END


# ==========================================
# 8. THE CREDIT / UTANG SUBSYSTEM
# ==========================================
async def add_utang_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_credit_context(context)
    context.user_data["utang_cart"] = []
    await update.message.reply_text(
        "👤 [Add New Utang] Please enter the customer's full name:",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
    )
    return UTANG_CUSTOMER


async def receive_utang_customer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END
    if not text:
        await update.message.reply_text("⚠️ Please enter a valid customer name.")
        return UTANG_CUSTOMER

    user_id = update.message.from_user.id
    context.user_data["utang_customer_name"] = text

    try:
        response = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", user_id).ilike("customer_name", text).execute()
        matches = response.data or []

        account = None
        if matches:
            exact = next((row for row in matches if str(row.get("customer_name", "")).lower() == text.lower()), None)
            account = exact or matches[0]

        if account:
            context.user_data["utang_account"] = account
            pre_balance = float(account.get("outstanding_balance") or 0)
            context.user_data["utang_pre_balance"] = pre_balance
            context.user_data["utang_customer_name"] = account.get("customer_name") or text
            context.user_data["utang_contact_info"] = account.get("contact_info") or "Not Provided"

            note_lines = [
                f"✅ Existing customer selected: {context.user_data['utang_customer_name']}",
                f"Current balance: {_format_currency(pre_balance)}",
            ]

            oldest = _parse_iso_datetime(account.get("oldest_unpaid_credit_date"))
            if oldest and pre_balance > 0:
                days_unpaid = max(0, (datetime.now(timezone.utc) - oldest).days)
                note_lines.append(f"Aging status: {days_unpaid} day(s) unpaid")

            note_lines.append("\n🛒 Enter item name from your inventory:")
            await update.message.reply_text("\n".join(note_lines), reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True))
            return UTANG_ITEM

        await update.message.reply_text(
            f"📝 New customer profile detected for '{text}'.\n\nPlease enter 11-digit mobile (09XXXXXXXXX or +639XXXXXXXXX):",
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
        )
        return UTANG_CONTACT

    except Exception:
        _clear_credit_context(context)
        await update.message.reply_text("⚠️ Server Error while loading customer profile.", reply_markup=get_utang_menu())
        return ConversationHandler.END


async def receive_utang_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    if not re.match(r"^(09\d{9}|\+639\d{9})$", text):
        await update.message.reply_text("⚠️ Invalid format. Use 09XXXXXXXXX or +639XXXXXXXXX.")
        return UTANG_CONTACT
    context.user_data["utang_contact_info"] = text

    await update.message.reply_text("🛒 Enter item name from your inventory:", reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True))
    return UTANG_ITEM


async def receive_utang_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    user_id = update.message.from_user.id
    try:
        response = supabase.table("inventory").select("*").eq("telegram_id", user_id).ilike("item_name", f"%{text}%").execute()
        items = response.data or []
        if not items:
            await update.message.reply_text("⚠️ Item not found. Please type the item name again.")
            return UTANG_ITEM

        selected = None
        exact = next((row for row in items if str(row.get("item_name", "")).lower() == text.lower()), None)
        if exact:
            selected = exact
        elif len(items) == 1:
            selected = items[0]
        else:
            keyboard = [[row["item_name"]] for row in items[:8]]
            keyboard.append(["❌ Cancel", "🔙 Back to Main Menu"])
            await update.message.reply_text("🔍 Multiple items found. Please tap the exact one:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return UTANG_ITEM

        context.user_data["utang_selected_item"] = selected
        await update.message.reply_text(
            f"📦 Product: {selected['item_name']}\nAvailable Stock: {selected['quantity']}\nRetail Price: {_format_currency(selected['retail_price'])}\n\nEnter quantity:",
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
        )
        return UTANG_QTY
    except Exception:
        _clear_credit_context(context)
        await update.message.reply_text("⚠️ Server Error while reading inventory.", reply_markup=get_utang_menu())
        return ConversationHandler.END


async def receive_utang_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("⚠️ Quantity must be a positive whole number.")
        return UTANG_QTY

    qty = int(text)
    selected = context.user_data.get("utang_selected_item")
    if not selected:
        await update.message.reply_text("⚠️ Session expired. Please start Add New Utang again.", reply_markup=get_utang_menu())
        return ConversationHandler.END

    available_stock = int(selected.get("quantity") or 0)
    if qty > available_stock:
        await update.message.reply_text(f"⚠️ Not enough stock. Available only: {available_stock}")
        return UTANG_QTY

    unit_price = float(selected.get("retail_price") or 0)
    line_total = qty * unit_price
    cart = context.user_data.setdefault("utang_cart", [])
    cart.append({
        "inventory_id": selected["id"],
        "item_name": selected["item_name"],
        "qty": qty,
        "unit_price": unit_price,
        "line_total": line_total,
        "current_stock": available_stock,
    })
    context.user_data.pop("utang_selected_item", None)

    running_total = sum(float(row["line_total"]) for row in cart)
    lines = ["🛒 Current Basket Summary:"]
    for idx, row in enumerate(cart, start=1):
        lines.append(f"{idx}. {row['qty']}x {row['item_name']} — {_format_currency(row['line_total'])}")
    lines.append(f"\nRunning Total: {_format_currency(running_total)}")
    lines.append("\nChoose: ➕ Add Another Item or 🧾 Complete Checkout")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=ReplyKeyboardMarkup(
            [["➕ Add Another Item", "🧾 Complete Checkout"], ["❌ Cancel", "🔙 Back to Main Menu"]],
            resize_keyboard=True,
        ),
    )
    return UTANG_CART_ACTION


async def handle_utang_cart_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    if text == "➕ Add Another Item":
        await update.message.reply_text("🛒 Enter next item name:", reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True))
        return UTANG_ITEM

    if text == "🧾 Complete Checkout":
        cart = context.user_data.get("utang_cart", [])
        if not cart:
            await update.message.reply_text("⚠️ Cart is empty. Add an item first.")
            return UTANG_ITEM
        await update.message.reply_text(
            "📝 Add notes/remarks for this utang transaction:",
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
        )
        return UTANG_NOTES

    await update.message.reply_text("Please choose: ➕ Add Another Item or 🧾 Complete Checkout")
    return UTANG_CART_ACTION


async def receive_utang_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    note_text = text
    user_id = update.message.from_user.id
    cart = context.user_data.get("utang_cart", [])
    customer_name = context.user_data.get("utang_customer_name")
    contact_info = context.user_data.get("utang_contact_info", "Not Provided")
    account = context.user_data.get("utang_account")
    pre_balance = float(context.user_data.get("utang_pre_balance") or 0)

    if not cart or not customer_name:
        _clear_credit_context(context)
        await update.message.reply_text("⚠️ Missing session data. Please start Add New Utang again.", reply_markup=get_utang_menu())
        return ConversationHandler.END

    cart_total = sum(float(row["line_total"]) for row in cart)

    try:
        if not account:
            inserted = supabase.table("customer_credit_accounts").insert({
                "telegram_id": user_id,
                "customer_name": customer_name,
                "contact_info": contact_info,
            }).execute()
            inserted_rows = inserted.data or []
            if inserted_rows:
                account = inserted_rows[0]
            else:
                lookup = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", user_id).eq("customer_name", customer_name).execute()
                account = (lookup.data or [None])[0]

        if not account:
            raise RuntimeError("Unable to load or create customer account")

        account_id = account["id"]
        now_iso = datetime.now(timezone.utc).isoformat()

        if pre_balance == 0:
            supabase.table("customer_credit_accounts").update({"oldest_unpaid_credit_date": now_iso}).eq("id", account_id).execute()

        rpc_ok = True
        try:
            supabase.rpc("increment_debt", {"account_id_input": account_id, "amount_input": cart_total}).execute()
        except Exception:
            rpc_ok = False

        if not rpc_ok:
            supabase.table("customer_credit_accounts").update({"outstanding_balance": pre_balance + cart_total}).eq("id", account_id).execute()

        stock_alerts = []
        for row in cart:
            new_stock = int(row["current_stock"]) - int(row["qty"])
            supabase.table("inventory").update({"quantity": new_stock}).eq("id", row["inventory_id"]).eq("telegram_id", user_id).execute()
            supabase.table("sales_log").insert({
                "telegram_id": user_id,
                "item_name": row["item_name"],
                "quantity_sold": row["qty"],
                "total_amount": row["line_total"],
                "payment_type": "Credit",
            }).execute()
            stock_alerts.append((row["item_name"], new_stock))

        item_summary = ", ".join([f"{row['qty']}x {row['item_name']}" for row in cart])
        reference_notes = f"Borrowed: {item_summary}"
        if note_text:
            reference_notes += f" | Remarks: {note_text}"

        supabase.table("credit_transaction_ledger").insert({
            "account_id": account_id,
            "transaction_type": "CREDIT_ISSUED",
            "amount": cart_total,
            "reference_notes": reference_notes,
        }).execute()

        new_balance = pre_balance + cart_total
        success_lines = [
            "✅ Credit Transaction Successfully Processed!",
            f"Debtor: {customer_name}",
            f"Basket Subtotal: {_format_currency(cart_total)}",
            f"Updated Balance: {_format_currency(new_balance)}",
        ]
        if note_text:
            success_lines.append(f"Saved Note: {note_text}")
        success_lines.append("Inventory and ledger records have been synced.")

        await update.message.reply_text("\n".join(success_lines), reply_markup=get_utang_menu())
        for item_name, new_stock in stock_alerts:
            await _send_low_stock_alert(update, user_id, item_name, new_stock)
    except Exception as e:
        print(f"Utang checkout error: {e}")
        await update.message.reply_text("⚠️ Failed to process credit checkout. Please try again.", reply_markup=get_utang_menu())

    _clear_credit_context(context)
    return ConversationHandler.END


async def record_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_credit_context(context)
    user_id = update.message.from_user.id
    try:
        response = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", user_id).gt("outstanding_balance", 0).order("outstanding_balance", desc=True).execute()
        accounts = response.data or []
        if not accounts:
            await update.message.reply_text("✅ No active debts found for your store.", reply_markup=get_utang_menu())
            return ConversationHandler.END

        context.user_data["payment_candidates"] = accounts
        lines = ["💳 [Record Payment] Type the exact customer name:"]
        for row in accounts[:12]:
            lines.append(f"• {row['customer_name']} — Owed: {_format_currency(row['outstanding_balance'])}")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
        )
        return PAYMENT_CUSTOMER
    except Exception:
        await update.message.reply_text("⚠️ Server Error while fetching debtors.", reply_markup=get_utang_menu())
        return ConversationHandler.END


async def receive_payment_customer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    candidates = context.user_data.get("payment_candidates", [])
    matched = [row for row in candidates if str(row.get("customer_name", "")).lower() == text.lower()]

    if not matched:
        partial = [row for row in candidates if text.lower() in str(row.get("customer_name", "")).lower()]
        if len(partial) == 1:
            matched = partial
        elif len(partial) > 1:
            keyboard = [[row["customer_name"]] for row in partial[:8]]
            keyboard.append(["❌ Cancel", "🔙 Back to Main Menu"])
            await update.message.reply_text("🔍 Multiple matches found. Select exact customer:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return PAYMENT_CUSTOMER

    if not matched:
        await update.message.reply_text("⚠️ Customer not found in active debtors list. Type again.")
        return PAYMENT_CUSTOMER

    account = matched[0]
    context.user_data["payment_target_account"] = account
    await update.message.reply_text(
        f"Selected: {account['customer_name']}\nOutstanding Balance: {_format_currency(account['outstanding_balance'])}\n\nEnter cash amount received:",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
    )
    return PAYMENT_AMOUNT


async def receive_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        _clear_credit_context(context)
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END

    account = context.user_data.get("payment_target_account")
    if not account:
        await update.message.reply_text("⚠️ Payment session expired. Please start again.", reply_markup=get_utang_menu())
        return ConversationHandler.END

    try:
        payment_amount = float(text)
        if payment_amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid positive payment amount.")
        return PAYMENT_AMOUNT

    current_balance = float(account.get("outstanding_balance") or 0)
    if payment_amount > current_balance:
        await update.message.reply_text(
            f"⚠️ Payment exceeds outstanding balance ({_format_currency(current_balance)}). Enter a smaller amount."
        )
        return PAYMENT_AMOUNT

    new_balance = current_balance - payment_amount
    now_iso = datetime.now(timezone.utc).isoformat()
    update_payload = {
        "outstanding_balance": new_balance,
        "last_payment_date": now_iso,
    }
    if new_balance == 0:
        update_payload["oldest_unpaid_credit_date"] = None

    try:
        supabase.table("customer_credit_accounts").update(update_payload).eq("id", account["id"]).execute()
        supabase.table("credit_transaction_ledger").insert({
            "account_id": account["id"],
            "transaction_type": "PAYMENT_RECEIVED",
            "amount": payment_amount,
            "reference_notes": f"Cash payment received. Remaining balance: {_format_currency(new_balance)}",
        }).execute()

        if new_balance == 0:
            extra = "Debt is fully settled. Aging clock reset."
        else:
            extra = "Partial payment logged. Original debt aging clock remains active."

        await update.message.reply_text(
            "\n".join([
                "✅ Payment Logged Successfully!",
                f"Collected: {_format_currency(payment_amount)}",
                f"Remaining Balance: {_format_currency(new_balance)}",
                extra,
            ]),
            reply_markup=get_utang_menu(),
        )
    except Exception as e:
        print(f"Payment processing error: {e}")
        await update.message.reply_text("⚠️ Failed to record payment. Please try again.", reply_markup=get_utang_menu())

    _clear_credit_context(context)
    return ConversationHandler.END


async def search_customer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 [Search Customer] Type customer name or keyword:",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel", "🔙 Back to Main Menu"]], resize_keyboard=True),
    )
    return SEARCH_CUSTOMER_QUERY


async def receive_search_customer_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_utang_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END
    if not text:
        await update.message.reply_text("⚠️ Please type a customer name or keyword.")
        return SEARCH_CUSTOMER_QUERY

    user_id = update.message.from_user.id
    try:
        response = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", user_id).ilike("customer_name", f"%{text}%").execute()
        accounts = response.data or []
        if not accounts:
            await update.message.reply_text("No matching customer found. Try another keyword.")
            return SEARCH_CUSTOMER_QUERY

        selected = next((row for row in accounts if str(row.get("customer_name", "")).lower() == text.lower()), accounts[0])

        ledger_resp = supabase.table("credit_transaction_ledger").select("*").eq("account_id", selected["id"]).order("logged_at", desc=True).limit(5).execute()
        ledger_rows = ledger_resp.data or []

        header = (
            f"🔍 Statement Ledger: {selected['customer_name']}\n"
            f"Contact: {selected.get('contact_info') or 'Not Provided'}\n"
            f"Current Balance: {_format_currency(selected.get('outstanding_balance') or 0)}\n\n"
        )

        if not ledger_rows:
            body = "\nNo transactions yet."
        else:
            entries = []
            for row in ledger_rows:
                ts = _parse_iso_datetime(row.get("logged_at"))
                ts_text = ts.strftime("%Y-%m-%d %H:%M") if ts else str(row.get("logged_at"))
                txn_type = (row.get("transaction_type") or "UNKNOWN").upper()
                amount = float(row.get("amount") or 0)
                if txn_type == "PAYMENT_RECEIVED":
                    sign = "-"
                else:
                    sign = "+"

                entries.append(f"{ts_text}  |  {txn_type}  |  {sign}{_format_currency(amount)}")
                note = row.get("reference_notes")
                if note:
                    # If the stored note contains a Remarks section, split it onto its own line for clarity.
                    if "Remarks:" in note:
                        main_part, remark_part = note.split("Remarks:", 1)
                        main_part = main_part.strip().strip("| ")
                        remark_part = remark_part.strip()
                        if main_part:
                            entries.append(f"{main_part}")
                        entries.append(f"Remarks: {remark_part}\n")
                    else:
                        entries.append(f"Note: {note}\n")
                else:
                    entries.append("Note: N/A\n")

            body = "\n".join(entries)

        await update.message.reply_text(header + body, reply_markup=get_utang_menu())
        return ConversationHandler.END
    except Exception as e:
        print(f"Customer search error: {e}")
        await update.message.reply_text("⚠️ Server Error while searching customer.", reply_markup=get_utang_menu())
        return ConversationHandler.END


async def view_active_debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        accounts_resp = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", user_id).gt("outstanding_balance", 0).order("outstanding_balance", desc=True).execute()
        accounts = accounts_resp.data or []
        if not accounts:
            await update.message.reply_text("📋 No active debts found.", reply_markup=get_utang_menu())
            return

        store_resp = supabase.table("stores").select("debt_grace_period_days").eq("telegram_id", user_id).limit(1).execute()
        grace_days = 30
        if store_resp.data:
            grace_days = int(store_resp.data[0].get("debt_grace_period_days") or 30)

        now = datetime.now(timezone.utc)
        lines = ["📋 Active Credit Ledger Summary", "───────────────────"]
        for row in accounts:
            oldest = _parse_iso_datetime(row.get("oldest_unpaid_credit_date"))
            days_unpaid = max(0, (now - oldest).days) if oldest else 0
            status = "⚠️ Overdue" if days_unpaid >= grace_days else "🟢 Nominal"
            since = oldest.strftime("%B %d, %Y") if oldest else "N/A"
            lines.extend([
                f"{row['customer_name']}",
                f"Owed: {_format_currency(row['outstanding_balance'])}",
                f"Status: {status} ({days_unpaid} day(s) unpaid - Since {since})",
                "",
            ])

        lines.append("Use 🔍 Search Customer for detailed timeline.")
        await update.message.reply_text("\n".join(lines), reply_markup=get_utang_menu())
    except Exception as e:
        print(f"View active debts error: {e}")
        await update.message.reply_text("⚠️ Server Error while loading active debts.", reply_markup=get_utang_menu())


# ==========================================
# 8A. SALES REPORTING & DAILY AUDIT HANDLERS
# ==========================================
async def handle_view_sales_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Sales Reporting Portal\n\nSelect the type of report summary you would like to run:",
        reply_markup=get_sales_report_menu(),
    )


async def process_report_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    today = _now_pht().date()

    if user_text == "☀️ Today's Drawer Summary":
        await update.message.reply_text(_sales_report_message(user_id, today), reply_markup=get_sales_report_menu())

    elif user_text == "📅 Lookup a Day":
        context.user_data["awaiting_sales_report_date"] = True
        await update.message.reply_text(
            "📅 Type the day you want to look up in `YYYY-MM-DD` format.\n\nExample: 2026-05-27\n\nSend ❌ Cancel to stop.",
            reply_markup=ReplyKeyboardMarkup([ ["❌ Cancel", "🔙 Back to Sales Menu"] ], resize_keyboard=True),
        )

    elif user_text == "📊 View Dashboard":
        base_url = "https://inventorylink-dashboard.streamlit.app"
        magic_link = f"{base_url}/?store_id={user_id}"
        reply_msg = (
            "📊 Your Personal Dashboard is ready!\n\n"
            "Click the secure link below to view your real-time store analytics:\n"
            f"👉 {magic_link}\n\n"
            "(Do not share this link with anyone!)"
        )
        await update.message.reply_text(reply_msg, reply_markup=get_sales_report_menu())

    elif user_text == "🚨 Critical Out-Of-Stock":
        inventory_rows = _inventory_rows_for_store(user_id)
        out_of_stock = [row for row in inventory_rows if int(row.get("quantity") or 0) <= 0]
        if not out_of_stock:
            text = "🚨 Critical Out-Of-Stock\n\nAll stock levels are healthy. No items are out of stock right now."
        else:
            lines = ["🚨 CRITICAL OUT-OF-STOCK", "─────────────────────────", "These items need replenishment:"]
            for idx, item in enumerate(out_of_stock, start=1):
                lines.append(f"{idx}. {item['item_name']} (0 pcs remaining)")
            text = "\n".join(lines)
        await update.message.reply_text(text, reply_markup=get_sales_report_menu())

    elif user_text == "🔙 Back to Sales Menu":
        context.user_data.pop("awaiting_sales_report_date", None)
        await update.message.reply_text("🏠 Returning to Sales Menu...", reply_markup=get_sales_menu())

    else:
        await update.message.reply_text("⚠️ Unknown report request.", reply_markup=get_sales_report_menu())


async def process_custom_sales_report_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "❌ Cancel":
        context.user_data.pop("awaiting_sales_report_date", None)
        await update.message.reply_text("❌ Report lookup cancelled.", reply_markup=get_sales_report_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Main Menu":
        context.user_data.pop("awaiting_sales_report_date", None)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
        return ConversationHandler.END
    if text == "🔙 Back to Sales Menu":
        context.user_data.pop("awaiting_sales_report_date", None)
        await update.message.reply_text("🏠 Returning to Sales Menu...", reply_markup=get_sales_menu())
        return ConversationHandler.END

    try:
        report_date = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid date in YYYY-MM-DD format, for example 2026-05-27.")
        return ConversationHandler.END

    context.user_data.pop("awaiting_sales_report_date", None)
    await update.message.reply_text(_sales_report_message(update.effective_user.id, report_date), reply_markup=get_sales_report_menu())
    return ConversationHandler.END


async def start_daily_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id
    today_cash_rows = _sales_rows_for_date(user_id, _now_pht().date(), payment_type="Cash")
    today_cash_sales = sum(float(row.get("total_amount") or 0) for row in today_cash_rows)
    context.user_data["today_cash_sales"] = today_cash_sales

    keyboard = ReplyKeyboardMarkup(
        [["💵 Use Default ₱500"], ["❌ Cancel Audit"]],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "🔒 [Daily Cash Drawer Audit]\nLet's reconcile today's cash ledger.\n\n"
        "Please enter your Starting Change Pot (base barya pot for the day, e.g., 500.00):",
        reply_markup=keyboard,
    )
    return GET_STARTING_POT


async def process_starting_pot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = (update.message.text or "").strip()
    if input_text == "💵 Use Default ₱500":
        context.user_data["starting_pot"] = 500.0
        await _send_audit_actual_cash_prompt(update, context)
        return GET_ACTUAL_CASH
    if input_text == "❌ Cancel Audit":
        context.user_data.clear()
        await update.message.reply_text("❌ Audit cancelled.", reply_markup=get_sales_menu())
        return ConversationHandler.END

    try:
        starting_pot = float(input_text)
        if starting_pot < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid positive starting change pot amount (e.g., 500):")
        return GET_STARTING_POT

    context.user_data["starting_pot"] = starting_pot
    await _send_audit_actual_cash_prompt(update, context)
    return GET_ACTUAL_CASH


async def process_actual_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = (update.message.text or "").strip()
    if input_text == "❌ Cancel Audit":
        context.user_data.clear()
        await update.message.reply_text("❌ Audit cancelled.", reply_markup=get_sales_menu())
        return ConversationHandler.END

    try:
        actual_cash = float(input_text)
        if actual_cash < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid positive counted cash amount:")
        return GET_ACTUAL_CASH

    context.user_data["actual_cash"] = actual_cash
    expected_cash = context.user_data["starting_pot"] + context.user_data["today_cash_sales"]
    context.user_data["expected_cash"] = expected_cash
    discrepancy = actual_cash - expected_cash
    context.user_data["discrepancy"] = discrepancy

    keyboard = ReplyKeyboardMarkup(
        [["⏩ Skip Notes", "❌ Cancel Audit"]],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"Calculated Discrepancy: {_format_currency(discrepancy)}\n\n"
        "📝 Add Audit Notes / Remarks:\n"
        "Enter any notes (e.g., 'Ate 2 eggs for lunch', 'Gave 50 pesos to pamangkin for school project'):",
        reply_markup=keyboard,
    )
    return GET_AUDIT_NOTES


async def process_audit_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes_input = (update.message.text or "").strip()
    if notes_input == "⏩ Skip Notes":
        await _save_daily_audit(update, context, None)
        return ConversationHandler.END
    if notes_input == "❌ Cancel Audit":
        context.user_data.clear()
        await update.message.reply_text("❌ Audit cancelled.", reply_markup=get_sales_menu())
        return ConversationHandler.END

    await _save_daily_audit(update, context, notes_input or None)
    return ConversationHandler.END

# ==========================================
# 9. THE NORMAL MENU BUTTONS
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

    if context.user_data.get("awaiting_sales_report_date"):
        await process_custom_sales_report_date(update, context)
        return

    if user_text == "📦 Inventory":
        await update.message.reply_text("📦 Inventory Dashboard", reply_markup=get_inventory_menu())
    elif user_text == "⚙️ Settings":
        await update.message.reply_text("⚙️ Settings", reply_markup=get_settings_menu())
    elif user_text == "💰 Sales":
        await update.message.reply_text("💰 Sales Dashboard", reply_markup=get_sales_menu())
    elif user_text == "📝 Utang (Credit)":
        await update.message.reply_text("📝 Utang Dashboard", reply_markup=get_utang_menu())
    elif user_text == "❓ Help / About":
        about_text = (
            "🤖 InventoryLink User Manual\n\n"
            "InventoryLink helps sari-sari store owners manage inventory, sales, utang, low-stock alerts, and daily cash drawer audits directly from Telegram.\n\n"
            "📦 Inventory\n"
            "• View Current Stock: See all items grouped by category.\n"
            "• Add Manual: Add new stock or restock an existing item.\n"
            "• Add via AI: Send a clear receipt photo; Gemini extracts items, quantities, wholesale prices, and categories.\n"
            "• Edit Item: Change quantity, wholesale price, or category.\n"
            "• Delete Item: Remove an item from your store inventory.\n\n"
            "💰 Sales\n"
            "• Record a Sale: Deduct stock and log cash sales.\n"
            "• View Sales Report: Check daily sales, top items, and out-of-stock counts.\n"
            "• Close & Audit: Compare expected cash against the actual drawer count.\n\n"
            "📝 Utang\n"
            "• Add New Utang: Record credit purchases and deduct stock.\n"
            "• Record Payment: Log customer payments.\n"
            "• View/Search Debts: Monitor active balances and aging status.\n\n"
            "⚙️ Settings\n"
            "• Rename Store: Update your display name.\n"
            "• Edit Debt Limit: Set how many days before debt alerts trigger.\n"
            "• Edit Stock Alert Limit: Set the quantity where low-stock Telegram alerts trigger.\n"
            "• Edit Selling Price %: Set the markup used to calculate selling price from wholesale cost.\n"
            "• Manage Categories: View, add, rename, or delete inventory categories. Deleted categories move items to 📦 Others.\n\n"
            "🚨 Alerts\n"
            "Low-stock alerts are sent automatically after cash sales or utang checkouts when remaining stock is at or below your alert limit.\n\n"
            "📊 Dashboard\n"
            "Use View Web Dashboard to open your personal analytics dashboard."
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
                
                inventory_text = "📊 Your Current Stock:\n\n"
                for cat, cat_items in grouped_items.items():
                    inventory_text += f"{cat}\n"
                    for item in cat_items:
                        inventory_text += f"   ▪️ {item['item_name']}: {item['quantity']} pcs (₱{item['retail_price']})\n"
                    inventory_text += "\n"
                await update.message.reply_text(inventory_text, reply_markup=get_inventory_menu())
        except Exception as e:
            await update.message.reply_text("⚠️ Server Error.", reply_markup=get_inventory_menu())

    elif user_text == "📊 View Web Dashboard":
        base_url = "https://inventorylink-dashboard.streamlit.app" 
        magic_link = f"{base_url}/?store_id={user_id}"
        reply_msg = (
            "📊 Your Personal Dashboard is ready!\n\n"
            "Click the secure link below to view your real-time store analytics:\n"
            f"👉 {magic_link}\n\n"
            "(Do not share this link with anyone!)"
        )
        await update.message.reply_text(reply_msg, reply_markup=get_main_menu())

    elif user_text == "📈 View Sales Report":
        await handle_view_sales_report(update, context)
    elif user_text == "🔒 Close & Audit":
        await start_daily_audit(update, context)
    elif user_text in {"☀️ Today's Drawer Summary", "📅 Lookup a Day", "📊 View Dashboard", "🚨 Critical Out-Of-Stock", "🔙 Back to Sales Menu"}:
        await process_report_selection(update, context)
    elif user_text == "📋 View Active Debts":
        await view_active_debts(update, context)
        
    elif user_text == "🔙 Back to Main Menu":
        _clear_credit_context(context)
        await update.message.reply_text("🏠 Returning to Main Menu...", reply_markup=get_main_menu())
    else:
        pass # Ignore other text inputs
