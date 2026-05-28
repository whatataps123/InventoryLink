import streamlit as st
import pandas as pd
import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

# 1. PAGE SETUP
st.set_page_config(page_title="InventoryLink Dashboard", page_icon="📦", layout="wide")

# 2. UNLOCK SECRETS & CONNECT TO DATABASE
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. DASHBOARD HEADER
if "store_id" not in st.query_params:
    st.error("🔒 Access Denied.")
    st.write("Please open your dashboard directly from the InventoryLink Telegram Bot using the '📊 View Dashboard' button.")
    st.stop() # This completely stops the rest of the website from loading!

# 2. Grab the ID from the URL
current_store_id = st.query_params["store_id"]

# Optional: Fetch the store's name to make the dashboard personalized!
store_info = supabase.table("stores").select("store_name").eq("telegram_id", current_store_id).execute()
store_name = store_info.data[0]['store_name'] if store_info.data else "Your Store"

st.title(f"📦 {store_name} Dashboard")
st.write("Real-time insights for your business.")

# ==========================================
# 📊 NEW: FILTERED DATA FETCHING
# ==========================================
# We now pass the user_id into the database fetch so it ONLY grabs their items!

@st.cache_data(ttl=60) 
def load_inventory_data(user_id):
    response = supabase.table("inventory").select("*").eq("telegram_id", user_id).execute()
    return response.data

@st.cache_data(ttl=60)
def load_sales_data(user_id):
    response = supabase.table("sales_log").select("*").eq("telegram_id", user_id).execute()
    return response.data

# Fetch the data specifically for the ID in the URL
inv_data = load_inventory_data(current_store_id)
sales_data = load_sales_data(current_store_id)

# 5. BUILD THE VISUALS
if not inv_data:
    st.warning("Your inventory is currently empty. Open Telegram and add some items!")
else:
    df_inv = pd.DataFrame(inv_data)
    
    # Calculate Inventory Metrics
    total_items = df_inv['quantity'].sum()
    total_value = (df_inv['quantity'] * df_inv['retail_price']).sum()
    
    # Calculate Sales Metrics
    total_sales = 0
    if sales_data:
        df_sales = pd.DataFrame(sales_data)
        total_sales = df_sales['total_amount'].sum()

    # --- TOP ROW: BIG METRICS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Items in Stock", f"{total_items:,} pcs")
    with col2:
        st.metric("Total Retail Value", f"₱{total_value:,.2f}")
    with col3:
        st.metric("Total Sales Revenue", f"₱{total_sales:,.2f}")

    st.divider()

    # --- MIDDLE ROW: INVENTORY ---
    col4, col5 = st.columns(2)

    with col4:
        st.subheader("📋 Current Stock List")
        display_df = df_inv[['category', 'item_name', 'quantity', 'retail_price']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with col5:
        st.subheader("📊 Stock by Category")
        category_df = df_inv.groupby('category')['quantity'].sum().reset_index()
        fig = px.pie(category_df, values='quantity', names='category', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        
    st.divider()
    
    # --- BOTTOM ROW: SALES HISTORY ---
    if sales_data:
        st.subheader("💰 Recent Sales & Top Items")
        
        # Clean up the date format so it's easy to read
        df_sales['sale_date'] = pd.to_datetime(df_sales['sale_date']).dt.strftime('%Y-%m-%d %H:%M')
        display_sales = df_sales[['sale_date', 'item_name', 'quantity_sold', 'total_amount']]
        
        col6, col7 = st.columns(2)
        with col6:
            # Show the newest sales at the top
            st.dataframe(display_sales.sort_values(by='sale_date', ascending=False), use_container_width=True, hide_index=True)
        
        with col7:
            # Create a bar chart of the best-selling items
            sales_by_item = df_sales.groupby('item_name')['quantity_sold'].sum().reset_index()
            fig_sales = px.bar(sales_by_item, x='item_name', y='quantity_sold', title="Most Popular Items", labels={'item_name': 'Item', 'quantity_sold': 'Pieces Sold'})
            st.plotly_chart(fig_sales, use_container_width=True)


st.divider()
st.header("💼 Credit (Utang) Analytics")

# Always query fresh credit rows to keep debt status synchronized with bot actions.
credit_accounts_res = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", current_store_id).execute()
store_grace_res = supabase.table("stores").select("debt_grace_period_days").eq("telegram_id", current_store_id).limit(1).execute()

credit_accounts = credit_accounts_res.data or []
grace_days = 30
if store_grace_res.data:
    grace_days = int(store_grace_res.data[0].get("debt_grace_period_days") or 30)

if not credit_accounts:
    st.info("No credit accounts found yet. Use the Telegram utang menu to add credit transactions.")
else:
    df_credit = pd.DataFrame(credit_accounts)
    now = datetime.datetime.now(datetime.timezone.utc)

    def compute_days_unpaid(raw_date):
        if pd.isna(raw_date) or not raw_date:
            return 0
        date_text = str(raw_date)
        if date_text.endswith("Z"):
            date_text = date_text.replace("Z", "+00:00")
        try:
            parsed = datetime.datetime.fromisoformat(date_text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return max(0, (now - parsed).days)
        except ValueError:
            return 0

    df_credit["outstanding_balance"] = pd.to_numeric(df_credit["outstanding_balance"], errors="coerce").fillna(0)
    df_credit["days_unpaid"] = df_credit["oldest_unpaid_credit_date"].apply(compute_days_unpaid)

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("Total Outstanding Receivables", f"₱{df_credit['outstanding_balance'].sum():,.2f}")
    with kpi2:
        active_accounts = len(df_credit[df_credit["outstanding_balance"] > 0])
        st.metric("Active Debtor Accounts", f"{active_accounts}")
    with kpi3:
        overdue_accounts = len(df_credit[(df_credit["outstanding_balance"] > 0) & (df_credit["days_unpaid"] >= grace_days)])
        st.metric("Breached Grace Period", f"{overdue_accounts}", delta=f"{grace_days}-day limit", delta_color="inverse")

    def aging_bucket(days):
        if days == 0:
            return "0: Cleared"
        if days <= 14:
            return "1: Current (1-14 Days)"
        if days <= 30:
            return "2: Warning (15-30 Days)"
        return "3: Overdue (31+ Days)"

    df_credit["aging_bucket"] = df_credit["days_unpaid"].apply(aging_bucket)
    bucket_df = (
        df_credit[df_credit["outstanding_balance"] > 0]
        .groupby("aging_bucket", as_index=False)["outstanding_balance"]
        .sum()
    )

    st.subheader("Outstanding Balance by Aging Bucket")
    if bucket_df.empty:
        st.caption("No outstanding balances to visualize.")
    else:
        st.bar_chart(bucket_df, x="aging_bucket", y="outstanding_balance", use_container_width=True)

    st.subheader("Customer Credit Registry")

    def risk_status(row):
        if row["outstanding_balance"] <= 0:
            return "✅ Settled"
        if row["days_unpaid"] >= grace_days:
            return "🚨 Critical"
        return "🟢 Active"

    df_credit["status"] = df_credit.apply(risk_status, axis=1)
    st.dataframe(
        df_credit[["customer_name", "contact_info", "outstanding_balance", "days_unpaid", "status"]],
        column_config={
            "customer_name": "Customer Name",
            "contact_info": "Contact",
            "outstanding_balance": "Balance Owed",
            "days_unpaid": "Days Unpaid",
            "status": "Status",
        },
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Export Credit Report")
    csv_payload = df_credit.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Credit Ledger (.CSV)",
        data=csv_payload,
        file_name=f"credit_ledger_report_{datetime.date.today().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        key="download-credit-ledger",
    )