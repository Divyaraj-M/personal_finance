import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

# SETUP Google Sheet Connection
gc_scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcred.json", gc_scope)
client = gspread.authorize(creds)

# PAGE CONFIGURATION
st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("💼 Personal Finance Dashboard")

# LOAD DATA
sheet = client.open("FINANCE TRACKER").sheet1
df = pd.DataFrame(sheet.get_all_records())

# CLEAN & PREPARE
# Normalize columns
df.columns = df.columns.str.strip().str.lower()
# Timestamp
df['txn_timestamp'] = pd.to_datetime(df.get('txn_timestamp', df.get('date')), errors='coerce')
# Map type to income/expense
df['type'] = df['type'].str.strip().str.lower().map({'credit': 'income', 'debit': 'expense'})
# Ensure numeric amount
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
# Derive date & month
df['date'] = df['txn_timestamp'].dt.date

df['month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)

# SIDEBAR FILTERS
st.sidebar.header("🔍 Filters")
min_date = df['date'].min()
max_date = df['date'].max()
start_date, end_date = st.sidebar.date_input("Date range", [min_date, max_date])
filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

# CALCULATE SUMMARY METRICS
# Total income & expense in filtered period
total_inc = filtered.loc[filtered['type']=='income', 'amount'].sum()
total_exp = filtered.loc[filtered['type']=='expense', 'amount'].sum()
balance = total_inc - total_exp

# Additional KPIs
savings_rate = (total_inc - total_exp) / total_inc if total_inc > 0 else 0
exp_ratio = total_exp / total_inc if total_inc > 0 else 0
avg_inc = filtered.loc[filtered['type']=='income', 'amount'].mean()
avg_exp = filtered.loc[filtered['type']=='expense', 'amount'].mean()

# DISPLAY KPIS
st.markdown("### 💰 Summary & KPIs")
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Income", f"₹{total_inc:,.2f}")
col2.metric("Total Expense", f"₹{total_exp:,.2f}")
col3.metric("Balance", f"₹{balance:,.2f}")
col4.metric("Savings Rate", f"{savings_rate:.1%}")
col5.metric("Expense Ratio", f"{exp_ratio:.1%}")
col6.metric("Avg Income (₹)", f"₹{avg_inc:,.0f}")
col6.metric("Avg Expense (₹)", f"₹{avg_exp:,.0f}")

# CUMULATIVE BALANCE TREND
trend = filtered.sort_values('txn_timestamp').copy()
trend['signed_amt'] = trend['amount'] * trend['type'].map({'income': 1, 'expense': -1})
trend['cum_balance'] = trend['signed_amt'].cumsum()
fig_trend = px.line(
    trend, x='txn_timestamp', y='cum_balance',
    title='Cumulative Balance Over Time',
    labels={'txn_timestamp':'Date','cum_balance':'Balance (₹)'}
)
st.plotly_chart(fig_trend, use_container_width=True)

# EXPENSE BY CATEGORY
cat_summary = (
    filtered[filtered['type']=='expense']
    .groupby('category')['amount']
    .sum()
    .reset_index()
)
fig_cat = px.pie(
    cat_summary, names='category', values='amount',
    title='Expenses by Category'
)
st.plotly_chart(fig_cat, use_container_width=True)

# TOP 5 TRANSACTIONS
top5 = (
    filtered.nlargest(5, 'amount')
    [['txn_timestamp','type','merchant','category','amount']]
)
st.subheader("Top 5 Transactions")
st.table(top5)

# MONTHLY EXPENSE BAR
monthly_exp = (
    filtered[filtered['type']=='expense']
    .groupby('month')['amount']
    .sum()
    .reset_index()
)
fig_mon = px.bar(
    monthly_exp, x='month', y='amount',
    title='Monthly Expenses', labels={'amount':'₹'}, text='amount'
)
st.plotly_chart(fig_mon, use_container_width=True)

# FORECAST (Income & Expense)
# Prepare time series
inc_ts = (
    filtered[filtered['type']=='income']
    .groupby('month')['amount']
    .sum()
    .reset_index(name='inc')
)
exp_ts = (
    filtered[filtered['type']=='expense']
    .groupby('month')['amount']
    .sum()
    .reset_index(name='exp')
)
full = pd.merge(inc_ts, exp_ts, on='month', how='outer').fillna(0)
full['x'] = np.arange(len(full))
# Fit models
model_inc = LinearRegression().fit(full[['x']], full['inc'])
model_exp = LinearRegression().fit(full[['x']], full['exp'])
# Predict next 6
fut_x = np.arange(len(full), len(full)+6).reshape(-1,1)
f_inc = model_inc.predict(fut_x)
f_exp = model_exp.predict(fut_x)
# Future labels
last_month = pd.to_datetime(full['month'].iloc[-1])
fut_labels = [
    (last_month + pd.DateOffset(months=i)).strftime('%Y-%m')
    for i in range(1,7)
]
# Plot forecast
fig_f = go.Figure()
fig_f.add_trace(go.Scatter(x=full['month'], y=full['inc'], mode='lines+markers', name='Actual Income'))
fig_f.add_trace(go.Scatter(x=full['month'], y=full['exp'], mode='lines+markers', name='Actual Expense'))
fig_f.add_trace(go.Scatter(x=fut_labels, y=f_inc, mode='lines+markers', name='Predicted Income', line=dict(dash='dash')))
fig_f.add_trace(go.Scatter(x=fut_labels, y=f_exp, mode='lines+markers', name='Predicted Expense', line=dict(dash='dash')))
fig_f.update_layout(
    title='Income & Expense Forecast (Next 6 Months)',
    xaxis_title='Month', yaxis_title='Amount (₹)'
)
st.plotly_chart(fig_f, use_container_width=True)
