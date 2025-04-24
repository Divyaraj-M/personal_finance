# In app.py, under your Streamlit app’s main loop:
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
gc = gspread.authorize(creds)
SHEET_URL = st.secrets["sheet_url"]
wb = gc.open_by_url(SHEET_URL)

def load_transactions():
    sh = wb.worksheet("bank_transactions")
    data = sh.get_all_records()
    df = pd.DataFrame(data)
    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    df["amount"] = pd.to_numeric(df["amount"])
    return df

# --- assume load_transactions() is defined above ---
# def load_transactions(): ...

def dashboard_page():
    st.title("📊 Financial Dashboard")

    # Load & filter data
    df = load_transactions()
    df['txn_timestamp'] = pd.to_datetime(df['txn_timestamp'])
    df['amount'] = pd.to_numeric(df['amount'])

    # Sidebar filters
    st.sidebar.header("Filters")
    min_date = df['txn_timestamp'].dt.date.min()
    max_date = df['txn_timestamp'].dt.date.max()
    date_range = st.sidebar.date_input("Date range", [min_date, max_date])
    categories = st.sidebar.multiselect(
        "Categories", df['category'].unique(), df['category'].unique()
    )

    df = df[
        (df['txn_timestamp'].dt.date >= date_range[0]) &
        (df['txn_timestamp'].dt.date <= date_range[1]) &
        (df['category'].isin(categories))
    ]

    # KPIs
    total = df['amount'].sum()
    avg_daily = df.groupby(df['txn_timestamp'].dt.date)['amount'].sum().mean()
    weeks = df['txn_timestamp'].dt.to_period('W').nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spent", f"₹{total:,.0f}")
    c2.metric("Avg Daily Spend", f"₹{avg_daily:,.0f}")
    c3.metric("Weeks Covered", weeks)

    # Weekly trend
    weekly = df.set_index('txn_timestamp').resample('W')['amount'].sum().reset_index()
    fig_w = px.line(weekly, x='txn_timestamp', y='amount', title="Weekly Expense Trend")
    st.plotly_chart(fig_w, use_container_width=True)

    # Monthly breakdown
    monthly = df.set_index('txn_timestamp').resample('M')['amount'].sum().reset_index()
    fig_m = px.bar(monthly, x='txn_timestamp', y='amount', title="Monthly Expenses")
    st.plotly_chart(fig_m, use_container_width=True)

    # Category distribution
    cat_sum = df.groupby('category')['amount'].sum().reset_index()
    fig_p = px.pie(cat_sum, names='category', values='amount', title="Expenses by Category")
    st.plotly_chart(fig_p, use_container_width=True)

# In your main app logic:
page = st.sidebar.selectbox("Go to", ["Home", "Dashboard", "Plan Expenses"])
if page == "Dashboard":
    dashboard_page()