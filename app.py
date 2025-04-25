import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import matplotlib.pyplot as plt

# SETUP Google Sheet Connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcred.json", scope)
client = gspread.authorize(creds)

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("💼 Personal Finance Dashboard")

sheet = client.open("FINANCE TRACKER").sheet1
df = pd.DataFrame(sheet.get_all_records())

# Clean column names (strip, lowercase)
df.columns = df.columns.str.strip().str.lower()

# Convert 'date' column to datetime
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Sidebar Filters
st.sidebar.header("🔍 Filters")
min_date = df['date'].min()
max_date = df['date'].max()

start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)
category = st.sidebar.multiselect("Category", options=df['category'].unique(), default=df['category'].unique())

# Apply filters
filtered_df = df[
    (df['date'] >= pd.to_datetime(start_date)) &
    (df['date'] <= pd.to_datetime(end_date)) &
    (df['category'].isin(category))
]

# Summary Metrics
income = filtered_df[filtered_df['type'].str.lower() == 'income']['amount'].sum()
expense = filtered_df[filtered_df['type'].str.lower() == 'expense']['amount'].sum()
balance = income - expense

st.markdown("### 💰 Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"₹{income:,.2f}")
col2.metric("Total Expense", f"₹{expense:,.2f}")
col3.metric("Balance", f"₹{balance:,.2f}")

# Monthly Expense Chart
filtered_df['month'] = filtered_df['date'].dt.to_period('M').astype(str)
monthly_summary = filtered_df[filtered_df['type'].str.lower() == 'expense'].groupby('month')['amount'].sum().reset_index()

st.markdown("### 📉 Monthly Expenses")
fig = px.bar(monthly_summary, x='month', y='amount', title='Expenses Over Time', labels={'amount': '₹'}, text='amount')
st.plotly_chart(fig, use_container_width=True)

# Display full filtered table
with st.expander("📋 View All Filtered Transactions"):
    st.dataframe(filtered_df.sort_values(by="date", ascending=False), use_container_width=True)
