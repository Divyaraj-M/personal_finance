import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import plotly.graph_objects as go


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

# Standardize and map 'type' column
df['type'] = df['type'].str.strip().str.lower()
df['type'] = df['type'].map({'credit': 'income', 'debit': 'expense'})

# Ensure 'amount' is numeric
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

# Convert 'date' column to datetime
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Sidebar Filters
st.sidebar.header("🔍 Filters")
min_date = df['date'].min()
max_date = df['date'].max()

start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)
category = st.sidebar.multiselect("Category", options=df['category'].dropna().unique(), default=df['category'].dropna().unique())

# Apply filters
filtered_df = df[
    (df['date'] >= pd.to_datetime(start_date)) &
    (df['date'] <= pd.to_datetime(end_date)) &
    (df['category'].isin(category))
]

# Summary Metrics
income = filtered_df[filtered_df['type'] == 'income']['amount'].sum()
expense = filtered_df[filtered_df['type'] == 'expense']['amount'].sum()
balance = income - expense

st.markdown("### 💰 Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"₹{income:,.2f}")
col2.metric("Total Expense", f"₹{expense:,.2f}")
col3.metric("Balance", f"₹{balance:,.2f}")

# Monthly Expense Chart
filtered_df['month'] = filtered_df['date'].dt.to_period('M').astype(str)
monthly_summary = filtered_df[filtered_df['type'] == 'expense'].groupby('month')['amount'].sum().reset_index()

st.markdown("### 📉 Monthly Expenses")
fig = px.bar(monthly_summary, x='month', y='amount', title='Expenses Over Time', labels={'amount': '₹'}, text='amount')
st.plotly_chart(fig, use_container_width=True)

# Display full filtered table
with st.expander("📋 View All Filtered Transactions"):
    st.dataframe(filtered_df.sort_values(by="date", ascending=False), use_container_width=True)

# Prepare data
monthly_data = filtered_df.copy()
monthly_data['month'] = monthly_data['date'].dt.to_period('M').astype(str)

# Summarize income and expenses by month
income_summary = monthly_data[monthly_data['type'].str.lower() == 'income'].groupby('month')['amount'].sum().reset_index()
expense_summary = monthly_data[monthly_data['type'].str.lower() == 'expense'].groupby('month')['amount'].sum().reset_index()

# Merge income and expenses
full_summary = pd.merge(income_summary, expense_summary, on='month', how='outer', suffixes=('_income', '_expense')).fillna(0)

# Create numeric X axis (month number)
full_summary['month_num'] = np.arange(len(full_summary))

# Model for Income
income_model = LinearRegression()
income_model.fit(full_summary[['month_num']], full_summary['amount_income'])

# Model for Expense
expense_model = LinearRegression()
expense_model.fit(full_summary[['month_num']], full_summary['amount_expense'])

# Predict next 6 months
future_months = np.arange(len(full_summary), len(full_summary) + 6).reshape(-1,1)
predicted_income = income_model.predict(future_months)
predicted_expense = expense_model.predict(future_months)

# Create future months labels
last_month = pd.to_datetime(full_summary['month'].iloc[-1])
future_month_labels = [(last_month + pd.DateOffset(months=i)).strftime('%Y-%m') for i in range(1,7)]

# Plot
fig_pred = go.Figure()

# Actuals
fig_pred.add_trace(go.Scatter(x=full_summary['month'], y=full_summary['amount_income'], mode='lines+markers', name='Actual Income'))
fig_pred.add_trace(go.Scatter(x=full_summary['month'], y=full_summary['amount_expense'], mode='lines+markers', name='Actual Expense'))

# Predictions
fig_pred.add_trace(go.Scatter(x=future_month_labels, y=predicted_income, mode='lines+markers', name='Predicted Income', line=dict(dash='dash')))
fig_pred.add_trace(go.Scatter(x=future_month_labels, y=predicted_expense, mode='lines+markers', name='Predicted Expense', line=dict(dash='dash')))

fig_pred.update_layout(title='Income & Expense Forecast (Next 6 months)', xaxis_title='Month', yaxis_title='Amount (₹)', legend_title='Legend')

st.plotly_chart(fig_pred, use_container_width=True)