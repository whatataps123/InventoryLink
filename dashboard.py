import streamlit as st
import pandas as pd
import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

MANILA_TZ = datetime.timezone(datetime.timedelta(hours=8))

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


@st.cache_data(ttl=60)
def load_audit_data(user_id):
    try:
        response = supabase.table("daily_drawer_audits").select("*").eq("telegram_id", user_id).order("audit_date", desc=True).execute()
        return response.data
    except Exception:
        return []


def to_manila_datetime(raw_value):
    if not raw_value:
        return None
    text = str(raw_value)
    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(MANILA_TZ)
    except ValueError:
        return None


def sales_summary_frame(df_sales, df_inv, target_date):
    if df_sales.empty:
        return {
            "cash": 0.0,
            "credit": 0.0,
            "revenue": 0.0,
            "profit": 0.0,
            "count": 0,
            "top_items": pd.DataFrame(columns=["item_name", "quantity_sold", "total_amount"]),
        }

    sales = df_sales.copy()
    sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce", utc=True).dt.tz_convert(MANILA_TZ)
    sales = sales[sales["sale_date"].dt.date == target_date].copy()

    if sales.empty:
        return {
            "cash": 0.0,
            "credit": 0.0,
            "revenue": 0.0,
            "profit": 0.0,
            "count": 0,
            "top_items": pd.DataFrame(columns=["item_name", "quantity_sold", "total_amount"]),
        }

    sales["quantity_sold"] = pd.to_numeric(sales["quantity_sold"], errors="coerce").fillna(0)
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce").fillna(0)
    sales["payment_type"] = sales["payment_type"].fillna("Cash")

    wholesale_map = {}
    if not df_inv.empty:
        inv = df_inv.copy()
        inv["wholesale_price"] = pd.to_numeric(inv["wholesale_price"], errors="coerce").fillna(0)
        wholesale_map = inv.set_index("item_name")["wholesale_price"].to_dict()

    sales["cogs"] = sales.apply(lambda row: float(wholesale_map.get(row["item_name"], 0)) * float(row["quantity_sold"]), axis=1)
    sales["estimated_profit"] = sales["total_amount"] - sales["cogs"]

    cash = sales.loc[sales["payment_type"].str.lower() == "cash", "total_amount"].sum()
    credit = sales.loc[sales["payment_type"].str.lower() == "credit", "total_amount"].sum()
    revenue = sales["total_amount"].sum()
    profit = sales["estimated_profit"].sum()
    count = len(sales)
    top_items = sales.groupby("item_name", as_index=False).agg({"quantity_sold": "sum", "total_amount": "sum"}).sort_values(["quantity_sold", "total_amount"], ascending=False)

    return {
        "cash": float(cash),
        "credit": float(credit),
        "revenue": float(revenue),
        "profit": float(profit),
        "count": int(count),
        "top_items": top_items,
    }

# Fetch the data specifically for the ID in the URL
inv_data = load_inventory_data(current_store_id)
sales_data = load_sales_data(current_store_id)

# 5. BUILD THE VISUALS
df_inv = pd.DataFrame(inv_data) if inv_data else pd.DataFrame()
df_sales = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()
df_audits = pd.DataFrame(load_audit_data(current_store_id)) if current_store_id else pd.DataFrame()

if df_inv.empty:
    st.warning("Your inventory is currently empty. Open Telegram and add some items!")
else:
    total_items = df_inv['quantity'].sum()
    total_value = (df_inv['quantity'] * df_inv['retail_price']).sum()
    total_sales = df_sales['total_amount'].sum() if not df_sales.empty else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Items in Stock", f"{total_items:,} pcs")
    with col2:
        st.metric("Total Retail Value", f"₱{total_value:,.2f}")
    with col3:
        st.metric("Total Sales Revenue", f"₱{total_sales:,.2f}")

    st.divider()

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

    if not df_sales.empty:
        st.subheader("💰 Recent Sales & Top Items")
        df_sales_display = df_sales.copy()
        df_sales_display['sale_date'] = pd.to_datetime(df_sales_display['sale_date'], errors='coerce', utc=True).dt.tz_convert(MANILA_TZ).dt.strftime('%Y-%m-%d %H:%M')
        display_sales = df_sales_display[['sale_date', 'item_name', 'quantity_sold', 'total_amount']]

        col6, col7 = st.columns(2)
        with col6:
            st.dataframe(display_sales.sort_values(by='sale_date', ascending=False), use_container_width=True, hide_index=True)

        with col7:
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

st.divider()
st.header("📈 Sales Reporting & Daily Audit")

if df_sales.empty:
    st.info("No sales logs found yet. Start recording sales in Telegram to unlock reporting dashboards.")
else:
    sales_plot = df_sales.copy()
    sales_plot['sale_date'] = pd.to_datetime(sales_plot['sale_date'], errors='coerce', utc=True).dt.tz_convert(MANILA_TZ)
    sales_plot['quantity_sold'] = pd.to_numeric(sales_plot['quantity_sold'], errors='coerce').fillna(0)
    sales_plot['total_amount'] = pd.to_numeric(sales_plot['total_amount'], errors='coerce').fillna(0)

    wholesale_map = {}
    if not df_inv.empty:
        inv_costs = df_inv.copy()
        inv_costs['wholesale_price'] = pd.to_numeric(inv_costs['wholesale_price'], errors='coerce').fillna(0)
        wholesale_map = inv_costs.set_index('item_name')['wholesale_price'].to_dict()

    sales_plot['cogs'] = sales_plot.apply(lambda row: float(wholesale_map.get(row['item_name'], 0)) * float(row['quantity_sold']), axis=1)
    sales_plot['estimated_profit'] = sales_plot['total_amount'] - sales_plot['cogs']

    today = datetime.datetime.now(MANILA_TZ).date()
    today_summary = sales_summary_frame(df_sales, df_inv, today)
    yesterday_summary = sales_summary_frame(df_sales, df_inv, today - datetime.timedelta(days=1))

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Today's Gross Revenue", f"₱{today_summary['revenue']:,.2f}")
    with col_b:
        st.metric("Today's Estimated Profit", f"₱{today_summary['profit']:,.2f}")
    with col_c:
        st.metric("Yesterday's Revenue", f"₱{yesterday_summary['revenue']:,.2f}")
    with col_d:
        if yesterday_summary['revenue'] > 0:
            dod = ((today_summary['revenue'] - yesterday_summary['revenue']) / yesterday_summary['revenue']) * 100
            st.metric("DoD Performance", f"{dod:.2f}%")
        else:
            st.metric("DoD Performance", "N/A")

    st.subheader("Today's Drawer Split")
    split_df = pd.DataFrame([
        {"Category": "Cash Sales", "Amount": today_summary['cash']},
        {"Category": "Credit Sales", "Amount": today_summary['credit']},
    ])
    if split_df['Amount'].sum() > 0:
        st.bar_chart(split_df, x="Category", y="Amount", use_container_width=True)
    else:
        st.caption("No sales recorded today yet.")

    st.subheader("Revenue vs. Real Profit (Tubo) Over Time")
    time_grain = st.selectbox(
        "Analyze trends by:",
        options=["Daily", "Weekly", "Monthly"],
        index=0,
        help="Group sales and profit data dynamically to evaluate business growth cycles.",
        key="sales-time-grain",
    )

    if time_grain == "Daily":
        sales_plot['time_group'] = sales_plot['sale_date'].dt.date
        x_label = "Date"
    elif time_grain == "Weekly":
        sales_plot['time_group'] = sales_plot['sale_date'].dt.to_period('W').dt.start_time
        x_label = "Week Commencing"
    else:
        sales_plot['time_group'] = sales_plot['sale_date'].dt.to_period('M').dt.to_timestamp()
        x_label = "Month"

    time_grouped = sales_plot.groupby('time_group', as_index=False)[['total_amount', 'estimated_profit']].sum()
    time_grouped.rename(columns={'total_amount': 'Gross Sales', 'estimated_profit': 'Net Profit (Tubo)'}, inplace=True)

    fig_trends = px.line(
        time_grouped,
        x='time_group',
        y=['Gross Sales', 'Net Profit (Tubo)'],
        labels={'value': 'Pesos (₱)', 'time_group': x_label},
        markers=True,
    )
    st.plotly_chart(fig_trends, use_container_width=True)

    st.subheader("⏰ Peak Sales Times (Hourly Cashier Staffing Guide)")
    sales_plot['hour'] = sales_plot['sale_date'].dt.hour
    hourly_grouped = sales_plot.groupby('hour', as_index=False)['total_amount'].sum()
    fig_hourly = px.bar(
        hourly_grouped,
        x='hour',
        y='total_amount',
        labels={'total_amount': 'Sales Volume (₱)', 'hour': 'Hour of the Day (24h)'},
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    st.subheader("🏆 Top 5 Best Sellers")
    top_items = today_summary['top_items'].head(5)
    if top_items.empty:
        st.caption("No sales yet for today's ranking.")
    else:
        st.dataframe(
            top_items,
            column_config={
                "item_name": "Item",
                "quantity_sold": "Pieces Sold",
                "total_amount": "Gross Sales",
            },
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("🚨 Critical Out-Of-Stock")
    if df_inv.empty:
        st.caption("Inventory data is unavailable.")
    else:
        out_of_stock_df = df_inv[df_inv['quantity'] <= 0][['item_name', 'category', 'quantity']]
        if out_of_stock_df.empty:
            st.success("All items are in stock.")
        else:
            st.dataframe(out_of_stock_df, hide_index=True, use_container_width=True)

    st.subheader("🔒 Daily Drawer Reconciliation & Leakage Audit History")
    if df_audits.empty:
        st.info("No daily audits recorded yet. Use Close & Audit in Telegram to begin tracking drawer discrepancies.")
    else:
        audits_plot = df_audits.copy()
        audits_plot['audit_date'] = pd.to_datetime(audits_plot['audit_date'], errors='coerce', utc=True).dt.tz_convert(MANILA_TZ)
        audits_plot['discrepancy'] = pd.to_numeric(audits_plot['discrepancy'], errors='coerce').fillna(0)
        audits_plot['expected_cash'] = pd.to_numeric(audits_plot['expected_cash'], errors='coerce').fillna(0)
        audits_plot['actual_cash_counted'] = pd.to_numeric(audits_plot['actual_cash_counted'], errors='coerce').fillna(0)

        col_e, col_f, col_g = st.columns(3)
        with col_e:
            st.metric("Total Days Audited", f"{len(audits_plot)} Days")
        with col_f:
            net_leakage = audits_plot['discrepancy'].sum()
            status_text = "🟢 Safe" if net_leakage >= 0 else "🚨 Leakage Alert"
            st.metric("Aggregate Net Leakage", f"₱{net_leakage:,.2f}", status_text, delta_color="inverse")
        with col_g:
            avg_discrepancy = audits_plot['discrepancy'].mean()
            st.metric("Average Daily Variance", f"₱{avg_discrepancy:,.2f}")

        fig_leakage = px.line(
            audits_plot,
            x='audit_date',
            y='discrepancy',
            labels={'discrepancy': 'Discrepancy (₱)', 'audit_date': 'Audit Closing Date'},
            markers=True,
            color_discrete_sequence=['#E11D48']
        )
        fig_leakage.add_hline(y=0, line_dash="dash", line_color="#10B981", annotation_text="Expected Cash Target")
        st.plotly_chart(fig_leakage, use_container_width=True)

        st.dataframe(
            audits_plot[['audit_date', 'starting_drawer_pot', 'expected_cash', 'actual_cash_counted', 'discrepancy', 'audit_notes']],
            column_config={
                "audit_date": "Audit Date",
                "starting_drawer_pot": "Starting Pot",
                "expected_cash": "Theoretical Drawer Expected",
                "actual_cash_counted": "Physical Cash Counted",
                "discrepancy": "Discrepancy (₱)",
                "audit_notes": "Audit Notes & Explanation",
            },
            use_container_width=True,
            hide_index=True,
        )