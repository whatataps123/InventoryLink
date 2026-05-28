import streamlit as st
import pandas as pd
import os
import datetime
import base64
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

MANILA_TZ = datetime.timezone(datetime.timedelta(hours=8))
PLOT_COLORS = ["#7c3aed", "#a855f7", "#2563eb", "#0f766e", "#d97706", "#dc2626", "#4b5563"]
LOGO_PATH = Path(__file__).parent / "assets" / "inventorylink-logo.svg"


# 1. PAGE SETUP
st.set_page_config(page_title="InventoryLink Dashboard", page_icon="📦", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=block');
    :root {
        --ink: #17202a;
        --muted: #687385;
        --line: #d8dee8;
        --panel: #ffffff;
        --soft: #f6f8fb;
        --accent: #7c3aed;
        --accent-strong: #5b21b6;
        --accent-soft: #f3e8ff;
        --accent-line: #c4b5fd;
    }
    html, body, .stApp, button, input, textarea, select, p, span, div, label {
        font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }
    .material-icons,
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-symbols-sharp,
    [class*="material"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    }
    html, body, .stApp, [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
        scrollbar-width: none;
        -ms-overflow-style: none;
    }
    html::-webkit-scrollbar,
    body::-webkit-scrollbar,
    .stApp::-webkit-scrollbar,
    [data-testid="stSidebar"]::-webkit-scrollbar,
    [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar {
        width: 0;
        height: 0;
        display: none;
    }
    [data-testid="stSidebar"] {
        overflow-x: hidden;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    .stApp {
        background: #f6f8fb;
        color: var(--ink);
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        max-width: 1440px;
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding: 22px 22px 24px 22px;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.85rem;
    }
    [data-testid="stSidebar"] img {
        filter: drop-shadow(0 8px 14px rgba(124, 58, 237, 0.16));
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 11px;
        padding: 0 0 18px 0;
        border-bottom: 1px solid var(--line);
        margin-bottom: 4px;
    }
    .sidebar-brand img {
        width: 44px;
        height: 44px;
        object-fit: contain;
    }
    .sidebar-brand h2 {
        margin: 0;
        font-size: 1.05rem;
        font-weight: 800;
        color: var(--accent-strong);
        letter-spacing: 0;
        line-height: 1.15;
    }
    .sidebar-brand p {
        margin: 4px 0 0 0;
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 500;
        line-height: 1.25;
    }
    .sidebar-panel {
        background: transparent;
        border: 0;
        border-radius: 0;
        padding: 8px 0 2px 0;
        box-shadow: none;
        margin-top: 0;
    }
    .sidebar-panel h3 {
        margin: 0 0 6px 0;
        font-size: 0.94rem;
        color: var(--ink);
        font-weight: 800;
        letter-spacing: 0;
    }
    .sidebar-panel p {
        margin: 0;
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.45;
    }
    .sidebar-footer {
        border-top: 1px solid var(--line);
        padding-top: 14px;
        margin-top: 18px;
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.55;
    }
    .sidebar-footer strong {
        color: var(--ink);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    [data-testid="stSidebar"] label p {
        font-size: 0.78rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 4px;
    }
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #ffffff;
        border-radius: 8px;
        border-color: #dfe5ee;
        min-height: 42px;
        box-shadow: none;
    }
    [data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
    [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.10) !important;
    }
    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-top: 3px solid var(--accent);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        min-height: 104px;
    }
    div[data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-size: 0.82rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.55rem;
        color: var(--ink);
    }
    .hero {
        background: #ffffff;
        border: 1px solid var(--accent-line);
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 22px 26px;
        margin-bottom: 16px;
    }
    .hero h1 {
        font-size: 1.8rem;
        margin: 0 0 4px 0;
        letter-spacing: 0;
        color: var(--accent-strong);
    }
    .hero p {
        color: var(--muted);
        margin: 0;
    }
    .section-title {
        font-size: 1.12rem;
        font-weight: 700;
        margin: 8px 0 10px 0;
        color: var(--ink);
        border-left: 4px solid var(--accent);
        padding-left: 10px;
    }
    .empty-state {
        background: #ffffff;
        border: 1px dashed #b9c3d3;
        border-radius: 8px;
        padding: 18px;
        color: var(--muted);
    }
    .status-line {
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    button[kind="primary"], .stDownloadButton button {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #ffffff !important;
    }
    button:hover, .stDownloadButton button:hover {
        border-color: var(--accent-strong) !important;
        color: var(--accent-strong) !important;
    }
    .stDownloadButton button:hover {
        color: #ffffff !important;
        background: var(--accent-strong) !important;
    }
    [data-baseweb="tab-list"] {
        gap: 24px;
    }
    [data-baseweb="tab"] {
        color: var(--muted);
        font-weight: 600;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent-strong) !important;
    }
    [data-baseweb="tab-highlight"] {
        background-color: var(--accent) !important;
    }
    input:focus, textarea:focus, [data-baseweb="select"] div:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }
    @media (max-width: 640px) {
        .hero h1 {
            font-size: 1.35rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. UNLOCK SECRETS & CONNECT TO DATABASE
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. DASHBOARD HEADER
if "store_id" not in st.query_params:
    st.error("🔒 Access Denied.")
    st.write("Please open your dashboard directly from the InventoryLink Telegram Bot using the '📊 View Dashboard' button.")
    st.stop()

current_store_id = st.query_params["store_id"]
store_info = supabase.table("stores").select("store_name").eq("telegram_id", current_store_id).execute()
store_name = store_info.data[0]["store_name"] if store_info.data else "Your Store"


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


def peso(value):
    return f"₱{float(value or 0):,.2f}"


def clean_number(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def empty_state(message):
    st.markdown(f'<div class="empty-state">{message}</div>', unsafe_allow_html=True)


def logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def style_fig(fig, height=360):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=35, b=10),
        font=dict(family="Inter, system-ui, sans-serif", color="#17202a", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e8edf4")
    return fig


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


def prepare_inventory(df):
    if df.empty:
        return df
    df = df.copy()
    for column in ["quantity", "retail_price", "wholesale_price"]:
        if column in df.columns:
            df[column] = clean_number(df[column])
    if "quantity" not in df.columns:
        df["quantity"] = 0
    if "retail_price" not in df.columns:
        df["retail_price"] = 0
    if "wholesale_price" not in df.columns:
        df["wholesale_price"] = 0
    if "category" not in df.columns:
        df["category"] = "📦 Others"
    if "item_name" not in df.columns:
        df["item_name"] = "Unknown Item"
    df["stock_value"] = df["quantity"] * df["retail_price"]
    df["category"] = df["category"].fillna("📦 Others")
    df["item_name"] = df["item_name"].fillna("Unknown Item")
    return df


def prepare_sales(df):
    if df.empty:
        return df
    if "sale_date" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce", utc=True).dt.tz_convert(MANILA_TZ)
    if "quantity_sold" not in df.columns:
        df["quantity_sold"] = 0
    if "total_amount" not in df.columns:
        df["total_amount"] = 0
    df["quantity_sold"] = clean_number(df["quantity_sold"])
    df["total_amount"] = clean_number(df["total_amount"])
    if "payment_type" not in df.columns:
        df["payment_type"] = "Cash"
    if "item_name" not in df.columns:
        df["item_name"] = "Unknown Item"
    df["payment_type"] = df["payment_type"].fillna("Cash")
    df["item_name"] = df["item_name"].fillna("Unknown Item")
    return df.dropna(subset=["sale_date"])


def apply_sales_profit(df_sales, df_inv):
    if df_sales.empty:
        return df_sales
    sales = df_sales.copy()
    wholesale_map = {}
    if not df_inv.empty and {"item_name", "wholesale_price"}.issubset(df_inv.columns):
        wholesale_map = df_inv.set_index("item_name")["wholesale_price"].to_dict()
    sales["cogs"] = sales.apply(lambda row: float(wholesale_map.get(row["item_name"], 0)) * float(row["quantity_sold"]), axis=1)
    sales["estimated_profit"] = sales["total_amount"] - sales["cogs"]
    return sales


def sales_summary_frame(df_sales, df_inv, target_date):
    empty_result = {
        "cash": 0.0,
        "credit": 0.0,
        "revenue": 0.0,
        "profit": 0.0,
        "count": 0,
        "top_items": pd.DataFrame(columns=["item_name", "quantity_sold", "total_amount"]),
    }
    if df_sales.empty:
        return empty_result

    sales = apply_sales_profit(df_sales, df_inv)
    sales = sales[sales["sale_date"].dt.date == target_date].copy()
    if sales.empty:
        return empty_result

    cash = sales.loc[sales["payment_type"].str.lower() == "cash", "total_amount"].sum()
    credit = sales.loc[sales["payment_type"].str.lower() == "credit", "total_amount"].sum()
    top_items = (
        sales.groupby("item_name", as_index=False)
        .agg({"quantity_sold": "sum", "total_amount": "sum"})
        .sort_values(["quantity_sold", "total_amount"], ascending=False)
    )
    return {
        "cash": float(cash),
        "credit": float(credit),
        "revenue": float(sales["total_amount"].sum()),
        "profit": float(sales["estimated_profit"].sum()),
        "count": int(len(sales)),
        "top_items": top_items,
    }


# 4. LOAD AND PREPARE DATA
inv_data = load_inventory_data(current_store_id)
sales_data = load_sales_data(current_store_id)
audit_data = load_audit_data(current_store_id)

df_inv = prepare_inventory(pd.DataFrame(inv_data) if inv_data else pd.DataFrame())
df_sales = prepare_sales(pd.DataFrame(sales_data) if sales_data else pd.DataFrame())
df_sales = apply_sales_profit(df_sales, df_inv)
df_audits = pd.DataFrame(audit_data) if audit_data else pd.DataFrame()

today = datetime.datetime.now(MANILA_TZ).date()
default_start = today - datetime.timedelta(days=30)
logo_uri = logo_data_uri()

with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
            {'<img src="' + logo_uri + '" alt="InventoryLink logo" />' if logo_uri else ''}
            <div>
                <h2>InventoryLink</h2>
                <p>Store operations dashboard</p>
            </div>
        </div>
        <div class="sidebar-panel">
            <h3>Dashboard Controls</h3>
            <p>Refine reports by date, category, and item.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_range = st.date_input(
        "Sales date range",
        value=(default_start, today),
        max_value=today,
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = default_start
        end_date = today

    category_options = ["All Categories"]
    if not df_inv.empty:
        category_options.extend(sorted(df_inv["category"].dropna().unique().tolist()))
    selected_category = st.selectbox("Inventory category", category_options)

    item_options = ["All Items"]
    if not df_inv.empty:
        item_options.extend(sorted(df_inv["item_name"].dropna().unique().tolist()))
    selected_item = st.selectbox("Item", item_options)

    st.markdown(
        f"""
        <div class="sidebar-footer">
            <div><strong>Store ID</strong><br>{current_store_id}</div>
            <div style="margin-top: 10px;"><strong>Data Refresh</strong><br>Every 60 seconds</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

filtered_inv = df_inv.copy()
if not filtered_inv.empty and selected_category != "All Categories":
    filtered_inv = filtered_inv[filtered_inv["category"] == selected_category]
if not filtered_inv.empty and selected_item != "All Items":
    filtered_inv = filtered_inv[filtered_inv["item_name"] == selected_item]

filtered_sales = df_sales.copy()
if not filtered_sales.empty:
    filtered_sales = filtered_sales[
        (filtered_sales["sale_date"].dt.date >= start_date)
        & (filtered_sales["sale_date"].dt.date <= end_date)
    ]
    if selected_item != "All Items":
        filtered_sales = filtered_sales[filtered_sales["item_name"] == selected_item]

st.markdown(
    f"""
    <div class="hero">
        <h1>{store_name} Dashboard</h1>
        <p>Inventory, sales, credit, and cash drawer health for {today.strftime('%B %d, %Y')}.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

overview_tab, inventory_tab, sales_tab, credit_tab, audit_tab = st.tabs(
    ["Overview", "Inventory", "Sales", "Credit", "Audit"]
)

with overview_tab:
    total_items = filtered_inv["quantity"].sum() if not filtered_inv.empty else 0
    total_value = filtered_inv["stock_value"].sum() if not filtered_inv.empty else 0
    total_sales = filtered_sales["total_amount"].sum() if not filtered_sales.empty else 0
    total_profit = filtered_sales["estimated_profit"].sum() if not filtered_sales.empty else 0
    out_of_stock = len(filtered_inv[filtered_inv["quantity"] <= 0]) if not filtered_inv.empty else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Items in Stock", f"{int(total_items):,} pcs")
    kpi2.metric("Retail Inventory Value", peso(total_value))
    kpi3.metric("Sales in Filter", peso(total_sales))
    kpi4.metric("Estimated Profit", peso(total_profit), delta=f"{out_of_stock} out of stock", delta_color="inverse")

    chart_col, table_col = st.columns([1.2, 1])
    with chart_col:
        section_title("Category Mix")
        if filtered_inv.empty:
            empty_state("No inventory matches the selected filters.")
        else:
            category_df = filtered_inv.groupby("category", as_index=False)["quantity"].sum().sort_values("quantity", ascending=False)
            fig = px.bar(
                category_df,
                x="quantity",
                y="category",
                orientation="h",
                labels={"quantity": "Pieces", "category": "Category"},
                color_discrete_sequence=[PLOT_COLORS[0]],
            )
            st.plotly_chart(style_fig(fig, 360), use_container_width=True)

    with table_col:
        section_title("Attention List")
        if filtered_inv.empty:
            empty_state("No inventory data available yet.")
        else:
            attention_df = filtered_inv[filtered_inv["quantity"] <= 5].sort_values("quantity")
            if attention_df.empty:
                st.success("No low-stock items in this view.")
            else:
                st.dataframe(
                    attention_df[["item_name", "category", "quantity"]],
                    column_config={
                        "item_name": "Item",
                        "category": "Category",
                        "quantity": st.column_config.NumberColumn("Stock", format="%d pcs"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

    section_title("Recent Sales")
    if filtered_sales.empty:
        empty_state("No sales found for the selected date range.")
    else:
        recent_sales = filtered_sales.sort_values("sale_date", ascending=False).head(12).copy()
        recent_sales["sale_date"] = recent_sales["sale_date"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(
            recent_sales[["sale_date", "item_name", "quantity_sold", "payment_type", "total_amount"]],
            column_config={
                "sale_date": "Date",
                "item_name": "Item",
                "quantity_sold": st.column_config.NumberColumn("Qty", format="%d"),
                "payment_type": "Payment",
                "total_amount": st.column_config.NumberColumn("Amount", format="₱%.2f"),
            },
            hide_index=True,
            use_container_width=True,
        )

with inventory_tab:
    section_title("Inventory Register")
    if filtered_inv.empty:
        empty_state("Your inventory is currently empty or no item matches the selected filters.")
    else:
        inv_left, inv_right = st.columns([1.35, 1])
        with inv_left:
            st.dataframe(
                filtered_inv[["category", "item_name", "quantity", "wholesale_price", "retail_price", "stock_value"]]
                .sort_values(["category", "item_name"]),
                column_config={
                    "category": "Category",
                    "item_name": "Item",
                    "quantity": st.column_config.NumberColumn("Qty", format="%d pcs"),
                    "wholesale_price": st.column_config.NumberColumn("Wholesale", format="₱%.2f"),
                    "retail_price": st.column_config.NumberColumn("Retail", format="₱%.2f"),
                    "stock_value": st.column_config.NumberColumn("Stock Value", format="₱%.2f"),
                },
                hide_index=True,
                use_container_width=True,
            )
        with inv_right:
            category_value = filtered_inv.groupby("category", as_index=False)["stock_value"].sum().sort_values("stock_value", ascending=False)
            fig = px.pie(
                category_value,
                values="stock_value",
                names="category",
                hole=0.58,
                color_discrete_sequence=PLOT_COLORS,
            )
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)

        low_stock = filtered_inv[filtered_inv["quantity"] <= 5].sort_values("quantity")
        section_title("Low and Out-of-Stock")
        if low_stock.empty:
            st.success("All filtered items have more than 5 pieces in stock.")
        else:
            st.dataframe(
                low_stock[["item_name", "category", "quantity", "retail_price"]],
                column_config={
                    "item_name": "Item",
                    "category": "Category",
                    "quantity": st.column_config.NumberColumn("Qty", format="%d pcs"),
                    "retail_price": st.column_config.NumberColumn("Retail", format="₱%.2f"),
                },
                hide_index=True,
                use_container_width=True,
            )

with sales_tab:
    if df_sales.empty:
        empty_state("No sales logs found yet. Start recording sales in Telegram to unlock sales dashboards.")
    else:
        today_summary = sales_summary_frame(df_sales, df_inv, today)
        yesterday_summary = sales_summary_frame(df_sales, df_inv, today - datetime.timedelta(days=1))
        dod = None
        if yesterday_summary["revenue"] > 0:
            dod = ((today_summary["revenue"] - yesterday_summary["revenue"]) / yesterday_summary["revenue"]) * 100

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Today's Gross Revenue", peso(today_summary["revenue"]))
        col_b.metric("Today's Estimated Profit", peso(today_summary["profit"]))
        col_c.metric("Yesterday's Revenue", peso(yesterday_summary["revenue"]))
        col_d.metric("DoD Performance", "N/A" if dod is None else f"{dod:.2f}%")

        if filtered_sales.empty:
            empty_state("No sales match the selected date range or item filter.")
        else:
            sales_left, sales_right = st.columns([1.4, 1])
            with sales_left:
                section_title("Revenue vs. Profit")
                trend = filtered_sales.copy()
                grain = st.radio(
                    "Trend grouping",
                    options=["Daily", "Weekly", "Monthly"],
                    index=0,
                    horizontal=True,
                    label_visibility="collapsed",
                )
                if grain == "Weekly":
                    trend["time_group"] = trend["sale_date"].dt.to_period("W").dt.start_time
                    x_label = "Week"
                elif grain == "Monthly":
                    trend["time_group"] = trend["sale_date"].dt.to_period("M").dt.to_timestamp()
                    x_label = "Month"
                else:
                    trend["time_group"] = trend["sale_date"].dt.date
                    x_label = "Date"
                trend_grouped = trend.groupby("time_group", as_index=False)[["total_amount", "estimated_profit"]].sum()
                trend_grouped.rename(columns={"total_amount": "Gross Sales", "estimated_profit": "Estimated Profit"}, inplace=True)
                fig = px.line(
                    trend_grouped,
                    x="time_group",
                    y=["Gross Sales", "Estimated Profit"],
                    markers=True,
                    labels={"value": "Amount", "time_group": x_label},
                    color_discrete_sequence=PLOT_COLORS,
                )
                st.plotly_chart(style_fig(fig, 390), use_container_width=True)

            with sales_right:
                section_title("Payment Split")
                split = filtered_sales.groupby("payment_type", as_index=False)["total_amount"].sum()
                fig = px.bar(
                    split,
                    x="payment_type",
                    y="total_amount",
                    labels={"payment_type": "Payment", "total_amount": "Amount"},
                    color="payment_type",
                    color_discrete_sequence=PLOT_COLORS,
                )
                st.plotly_chart(style_fig(fig, 390), use_container_width=True)

            sales_bottom_left, sales_bottom_right = st.columns(2)
            with sales_bottom_left:
                section_title("Peak Sales Times")
                hourly = filtered_sales.copy()
                hourly["hour"] = hourly["sale_date"].dt.hour
                hourly_grouped = hourly.groupby("hour", as_index=False)["total_amount"].sum()
                fig = px.bar(
                    hourly_grouped,
                    x="hour",
                    y="total_amount",
                    labels={"hour": "Hour", "total_amount": "Sales"},
                    color_discrete_sequence=[PLOT_COLORS[1]],
                )
                st.plotly_chart(style_fig(fig, 320), use_container_width=True)

            with sales_bottom_right:
                section_title("Best Sellers")
                top_items = (
                    filtered_sales.groupby("item_name", as_index=False)
                    .agg({"quantity_sold": "sum", "total_amount": "sum"})
                    .sort_values(["quantity_sold", "total_amount"], ascending=False)
                    .head(10)
                )
                st.dataframe(
                    top_items,
                    column_config={
                        "item_name": "Item",
                        "quantity_sold": st.column_config.NumberColumn("Pieces Sold", format="%d"),
                        "total_amount": st.column_config.NumberColumn("Gross Sales", format="₱%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

with credit_tab:
    st.markdown('<div class="status-line">Credit rows are queried fresh so account status stays synchronized with Telegram actions.</div>', unsafe_allow_html=True)
    credit_accounts_res = supabase.table("customer_credit_accounts").select("*").eq("telegram_id", current_store_id).execute()
    store_grace_res = supabase.table("stores").select("debt_grace_period_days").eq("telegram_id", current_store_id).limit(1).execute()

    credit_accounts = credit_accounts_res.data or []
    grace_days = 30
    if store_grace_res.data:
        grace_days = int(store_grace_res.data[0].get("debt_grace_period_days") or 30)

    if not credit_accounts:
        empty_state("No credit accounts found yet. Use the Telegram utang menu to add credit transactions.")
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

        df_credit["outstanding_balance"] = clean_number(df_credit["outstanding_balance"])
        df_credit["days_unpaid"] = df_credit["oldest_unpaid_credit_date"].apply(compute_days_unpaid)
        active_accounts = len(df_credit[df_credit["outstanding_balance"] > 0])
        overdue_accounts = len(df_credit[(df_credit["outstanding_balance"] > 0) & (df_credit["days_unpaid"] >= grace_days)])

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Outstanding Receivables", peso(df_credit["outstanding_balance"].sum()))
        kpi2.metric("Active Debtor Accounts", f"{active_accounts}")
        kpi3.metric("Breached Grace Period", f"{overdue_accounts}", delta=f"{grace_days}-day limit", delta_color="inverse")

        def aging_bucket(days):
            if days == 0:
                return "0: Cleared"
            if days <= 14:
                return "1: Current"
            if days <= 30:
                return "2: Warning"
            return "3: Overdue"

        def risk_status(row):
            if row["outstanding_balance"] <= 0:
                return "✅ Settled"
            if row["days_unpaid"] >= grace_days:
                return "🚨 Critical"
            return "🟢 Active"

        df_credit["aging_bucket"] = df_credit["days_unpaid"].apply(aging_bucket)
        df_credit["status"] = df_credit.apply(risk_status, axis=1)

        credit_left, credit_right = st.columns([1, 1.4])
        with credit_left:
            section_title("Aging Buckets")
            bucket_df = (
                df_credit[df_credit["outstanding_balance"] > 0]
                .groupby("aging_bucket", as_index=False)["outstanding_balance"]
                .sum()
            )
            if bucket_df.empty:
                empty_state("No outstanding balances to visualize.")
            else:
                fig = px.bar(
                    bucket_df,
                    x="aging_bucket",
                    y="outstanding_balance",
                    labels={"aging_bucket": "Bucket", "outstanding_balance": "Balance"},
                    color_discrete_sequence=[PLOT_COLORS[2]],
                )
                st.plotly_chart(style_fig(fig, 350), use_container_width=True)

        with credit_right:
            section_title("Customer Credit Registry")
            st.dataframe(
                df_credit[["customer_name", "contact_info", "outstanding_balance", "days_unpaid", "status"]]
                .sort_values(["outstanding_balance", "days_unpaid"], ascending=False),
                column_config={
                    "customer_name": "Customer",
                    "contact_info": "Contact",
                    "outstanding_balance": st.column_config.NumberColumn("Balance Owed", format="₱%.2f"),
                    "days_unpaid": st.column_config.NumberColumn("Days Unpaid", format="%d"),
                    "status": "Status",
                },
                use_container_width=True,
                hide_index=True,
            )

        csv_payload = df_credit.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Credit Ledger (.CSV)",
            data=csv_payload,
            file_name=f"credit_ledger_report_{datetime.date.today().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            key="download-credit-ledger",
        )

with audit_tab:
    if df_audits.empty:
        empty_state("No daily audits recorded yet. Use Close & Audit in Telegram to begin tracking drawer discrepancies.")
    else:
        audits_plot = df_audits.copy()
        audits_plot["audit_date"] = pd.to_datetime(audits_plot["audit_date"], errors="coerce", utc=True).dt.tz_convert(MANILA_TZ)
        audits_plot["discrepancy"] = clean_number(audits_plot["discrepancy"])
        audits_plot["expected_cash"] = clean_number(audits_plot["expected_cash"])
        audits_plot["actual_cash_counted"] = clean_number(audits_plot["actual_cash_counted"])
        audits_plot["starting_drawer_pot"] = clean_number(audits_plot["starting_drawer_pot"])

        col_e, col_f, col_g = st.columns(3)
        col_e.metric("Total Days Audited", f"{len(audits_plot)} days")
        net_leakage = audits_plot["discrepancy"].sum()
        status_text = "Balanced or over" if net_leakage >= 0 else "Shortage detected"
        col_f.metric("Aggregate Net Variance", peso(net_leakage), status_text, delta_color="inverse")
        col_g.metric("Average Daily Variance", peso(audits_plot["discrepancy"].mean()))

        section_title("Drawer Variance Over Time")
        fig = px.line(
            audits_plot.sort_values("audit_date"),
            x="audit_date",
            y="discrepancy",
            labels={"discrepancy": "Variance", "audit_date": "Audit Date"},
            markers=True,
            color_discrete_sequence=["#dc2626"],
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#0f766e", annotation_text="Expected cash target")
        st.plotly_chart(style_fig(fig, 360), use_container_width=True)

        section_title("Audit History")
        audit_display = audits_plot.sort_values("audit_date", ascending=False).copy()
        audit_display["audit_date"] = audit_display["audit_date"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(
            audit_display[["audit_date", "starting_drawer_pot", "expected_cash", "actual_cash_counted", "discrepancy", "audit_notes"]],
            column_config={
                "audit_date": "Audit Date",
                "starting_drawer_pot": st.column_config.NumberColumn("Starting Pot", format="₱%.2f"),
                "expected_cash": st.column_config.NumberColumn("Expected Cash", format="₱%.2f"),
                "actual_cash_counted": st.column_config.NumberColumn("Actual Cash", format="₱%.2f"),
                "discrepancy": st.column_config.NumberColumn("Variance", format="₱%.2f"),
                "audit_notes": "Notes",
            },
            use_container_width=True,
            hide_index=True,
        )
