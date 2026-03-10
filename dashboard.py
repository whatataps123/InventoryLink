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
st.title("📦 InventoryLink Dashboard")
st.write("Real-time insights for your Sari-Sari store.")

# 4. FETCH THE DATA
# We use st.cache_data so it doesn't constantly hammer the database every second
@st.cache_data(ttl=60) 
def load_data():
    response = supabase.table("inventory").select("*").execute()
    return response.data

data = load_data()

# 5. BUILD THE VISUALS
if not data:
    st.warning("Your inventory is currently empty. Open Telegram and add some items!")
else:
    # Turn the raw database data into a Pandas DataFrame (a super-powered Excel table)
    df = pd.DataFrame(data)

    # --- TOP ROW: BIG METRICS ---
    # Calculate totals
    total_items = df['quantity'].sum()
    total_value = (df['quantity'] * df['retail_price']).sum()

    # Create two columns for our big numbers
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Items in Stock", f"{total_items:,} pcs")
    with col2:
        st.metric("Total Retail Value", f"₱{total_value:,.2f}")

    st.divider()

    # --- BOTTOM ROW: TABLE & CHART ---
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📋 Current Stock List")
        # Show a clean version of the table
        display_df = df[['category', 'item_name', 'quantity', 'retail_price']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with col4:
        st.subheader("📊 Stock by Category")
        # Group items by category and draw a donut chart
        category_df = df.groupby('category')['quantity'].sum().reset_index()
        fig = px.pie(category_df, values='quantity', names='category', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)