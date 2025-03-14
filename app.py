import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="SuperStore KPI Dashboard", layout="wide")

# ---- Load Data ----
@st.cache_data
def load_data():
    df = pd.read_excel("Sample - Superstore.xlsx", engine="openpyxl")
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    return df

df_original = load_data()

# ---- Sidebar Filters ----
st.sidebar.title("Filters")

# Function to dynamically filter selections
def filter_options(df, column, prev_selection):
    options = sorted(df[column].dropna().unique())
    return ["All"] + options if prev_selection == "All" else ["All"] + sorted(df[df[prev_selection] == selected_filters[prev_selection]][column].dropna().unique())

selected_filters = {}

# Region Filter
selected_filters["Region"] = st.sidebar.selectbox("Select Region", options=filter_options(df_original, "Region", "All"))

# State Filter (depends on Region)
selected_filters["State"] = st.sidebar.selectbox("Select State", options=filter_options(df_original, "State", "Region"))

# City Filter (NEW FEATURE - depends on State)
selected_filters["City"] = st.sidebar.selectbox("Select City", options=filter_options(df_original, "City", "State"))

# Category Filter
selected_filters["Category"] = st.sidebar.selectbox("Select Category", options=filter_options(df_original, "Category", "All"))

# Sub-Category Filter
selected_filters["Sub-Category"] = st.sidebar.selectbox("Select Sub-Category", options=filter_options(df_original, "Sub-Category", "Category"))

# Date Range Filter
min_date, max_date = df_original["Order Date"].min(), df_original["Order Date"].max()
from_date = st.sidebar.date_input("From Date", value=min_date, min_value=min_date, max_value=max_date)
to_date = st.sidebar.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date)

if from_date > to_date:
    st.sidebar.error("From Date must be earlier than To Date.")

# ---- Apply Filters ----
def filter_data(df, filters, from_date, to_date):
    for key, value in filters.items():
        if value != "All":
            df = df[df[key] == value]
    df = df[(df["Order Date"] >= pd.to_datetime(from_date)) & (df["Order Date"] <= pd.to_datetime(to_date))]
    return df

df = filter_data(df_original, selected_filters, from_date, to_date)

# ---- Page Title ----
st.title("📊 SuperStore KPI Dashboard")

# ---- Empty Data Handling ----
if df.empty:
    st.warning("No data available. Please adjust your filters.")
    st.stop()

# ---- KPI Calculation ----
total_sales = df["Sales"].sum()
total_quantity = df["Quantity"].sum()
total_profit = df["Profit"].sum()
margin_rate = (total_profit / total_sales) * 100 if total_sales != 0 else 0

# ---- KPI Display ----
kpi_cols = st.columns(4)
kpis = [("Sales", f"${total_sales:,.2f}"), ("Quantity Sold", f"{total_quantity:,}"), ("Profit", f"${total_profit:,.2f}"), ("Margin Rate", f"{margin_rate:.2f}%")]
for col, (title, value) in zip(kpi_cols, kpis):
    col.metric(label=title, value=value)

# ---- KPI Selection for Visualization ----
st.subheader("📈 Visualize KPI Across Time & Top Products")
kpi_options = ["Sales", "Quantity", "Profit", "Margin Rate"]
selected_kpi = st.radio("Select KPI to display:", options=kpi_options, horizontal=True)

# ---- Data Aggregation Option ----
time_aggregation = st.selectbox("Group Data By:", ["Daily", "Monthly"])

# ---- Prepare Data for Charts ----
df["Year-Month"] = df["Order Date"].dt.to_period("M").astype(str)  # Convert to 'YYYY-MM' format

if time_aggregation == "Monthly":
    time_grouped = df.groupby("Year-Month").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    time_grouped["Margin Rate"] = (time_grouped["Profit"] / time_grouped["Sales"]).fillna(0)
    x_column = "Year-Month"
else:
    time_grouped = df.groupby("Order Date").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    time_grouped["Margin Rate"] = (time_grouped["Profit"] / time_grouped["Sales"]).fillna(0)
    x_column = "Order Date"

# Top 10 Products
top_products = df.groupby("Product Name").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
top_products["Margin Rate"] = (top_products["Profit"] / top_products["Sales"]).fillna(0)
top_products = top_products.nlargest(10, selected_kpi)

# ---- Side-by-Side Charts ----
col_left, col_right = st.columns(2)

with col_left:
    fig_time = px.line(time_grouped, x=x_column, y=selected_kpi, markers=True,
                       title=f"{selected_kpi} Over Time", labels={x_column: "Date", selected_kpi: selected_kpi},
                       template="plotly_white")
    fig_time.update_layout(height=400)
    st.plotly_chart(fig_time, use_container_width=True)

with col_right:
    fig_bar = px.bar(top_products, x=selected_kpi, y="Product Name", orientation="h",
                     title=f"Top 10 Products by {selected_kpi}", color=selected_kpi, color_continuous_scale="Blues",
                     template="plotly_white")
    fig_bar.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_bar, use_container_width=True)
