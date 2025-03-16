import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="SuperStore KPI Dashboard", layout="wide")

# Load data
@st.cache_data
def load_data():
    df = pd.read_excel("Sample - Superstore.xlsx", engine="openpyxl")
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    return df

df_original = load_data()

# Sidebar filters
st.sidebar.title("🔍 Filters")

def filter_options(df, column, prev_selection):
    options = sorted(df[column].dropna().unique())
    return ["All"] + options if prev_selection == "All" else ["All"] + sorted(df[df[prev_selection] == selected_filters[prev_selection]][column].dropna().unique())

selected_filters = {}

filter_columns = ["Region", "State", "City", "Category", "Sub-Category"]
for col in filter_columns:
    prev_col = filter_columns[filter_columns.index(col) - 1] if filter_columns.index(col) > 0 else "All"
    selected_filters[col] = st.sidebar.selectbox(f"Select {col}", options=filter_options(df_original, col, prev_col))

# Date range filter
min_date, max_date = df_original["Order Date"].min(), df_original["Order Date"].max()
from_date, to_date = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

if from_date > to_date:
    st.sidebar.error("From Date must be earlier than To Date.")

# Apply filters
def filter_data(df, filters, from_date, to_date):
    for key, value in filters.items():
        if value != "All":
            df = df[df[key] == value]
    return df[(df["Order Date"] >= pd.to_datetime(from_date)) & (df["Order Date"] <= pd.to_datetime(to_date))]

df = filter_data(df_original, selected_filters, from_date, to_date)

# Page title
st.title("SuperStore KPI Dashboard")

# Empty data handling
if df.empty:
    st.warning("⚠ No data available. Please adjust your filters.")
    st.stop()

# KPI calculation
kpi_metrics = {
    "Sales": df["Sales"].sum(),
    "Quantity Sold": df["Quantity"].sum(),
    "Profit": df["Profit"].sum(),
    "Margin Rate": (df["Profit"].sum() / df["Sales"].sum() * 100) if df["Sales"].sum() != 0 else 0
}

# KPI display with tooltips
kpi_cols = st.columns(4)
for col, (title, value) in zip(kpi_cols, kpi_metrics.items()):
    if "Rate" in title:
        col.metric(label=title, value=f"{value:.2f}%", help=f"{title} is calculated as (Profit/Sales)*100")
    else:
        col.metric(label=title, value=f"${value:,.2f}", help=f"{title} is the total {title.lower()} within the selected period")

# KPI selection for visualization
st.subheader("Visualize KPI Trends & Top Products")
selected_kpi = st.selectbox("Select KPI to display:", options=list(kpi_metrics.keys()))

time_aggregation = st.selectbox("Group Data By:", ["Daily", "Monthly"])

df["Year-Month"] = df["Order Date"].dt.to_period("M").astype(str)

time_grouped = df.groupby("Year-Month" if time_aggregation == "Monthly" else "Order Date").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
time_grouped["Margin Rate"] = (time_grouped["Profit"] / time_grouped["Sales"]).fillna(0)
x_column = "Year-Month" if time_aggregation == "Monthly" else "Order Date"

# Top 10 Products
selected_kpi_col = "Margin Rate" if selected_kpi == "Margin Rate" else selected_kpi

top_products = df.groupby("Product Name").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
top_products["Margin Rate"] = (top_products["Profit"] / top_products["Sales"]).fillna(0)
top_products = top_products.nlargest(10, selected_kpi_col)

# Side-by-side charts
col_left, col_right = st.columns(2)

with col_left:
    fig_time = px.line(time_grouped, x=x_column, y=selected_kpi_col, markers=True,
                       title=f"{selected_kpi} Over Time", labels={x_column: "Date", selected_kpi_col: selected_kpi},
                       template="plotly_white")
    fig_time.update_layout(height=400)
    st.plotly_chart(fig_time, use_container_width=True)

with col_right:
    fig_bar = px.bar(top_products, x=selected_kpi_col, y="Product Name", orientation="h",
                     title=f"Top 10 Products by {selected_kpi}", color=selected_kpi_col, color_continuous_scale="Blues",
                     template="plotly_white")
    fig_bar.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_bar, use_container_width=True)

# Additional insights
st.subheader("Additional Insights")
if st.checkbox("Show Detailed Data"):
    st.write(df)

# Download data option
if st.button("Download Filtered Data"):
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(df)
    st.download_button("Download CSV", csv, "filtered_data.csv", "text/csv", key='download-csv')
