import streamlit as st
import pandas as pd
import os
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
    st.error("🔒 **Access Denied.**")
    st.write("Please open your dashboard directly from the **InventoryLink Telegram Bot** using the '📊 View Dashboard' button.")
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