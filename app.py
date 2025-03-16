import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import base64  # For custom CSS injection

# Set Streamlit page configuration with a wide layout and custom title
st.set_page_config(page_title="SuperStore KPI Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inject custom CSS for better styling and responsiveness
def local_css():
    st.markdown("""
    <style>
        /* Improve spacing and font consistency */
        .stMetric { font-size: 1.2em; margin-bottom: 10px; }
        .block-container { padding: 1rem; }
        /* Responsive design for smaller screens */
        @media (max-width: 768px) {
            .stColumn { width: 100% !important; margin-bottom: 1rem; }
            .stSidebar { width: 200px !important; }
        }
        /* Reduce clutter in charts */
        .plotly-chart { margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# Load data with caching for performance
@st.cache_data
def load_data():
    df = pd.read_excel("Sample - Superstore.xlsx", engine="openpyxl")
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    return df

df_original = load_data()

# Sidebar filters with improved usability
st.sidebar.title("🔍 Filters")
st.sidebar.markdown("Use the filters below to explore the data.")

# Dynamic filter options with dependency handling
def filter_options(df, column, prev_col, prev_selection):
    options = sorted(df[column].dropna().unique())
    if prev_selection == "All" or prev_col == "All":
        return ["All"] + options
    return ["All"] + sorted(df[df[prev_col] == prev_selection][column].dropna().unique())

selected_filters = {}
filter_columns = ["Region", "State", "City", "Category", "Sub-Category"]
for i, col in enumerate(filter_columns):
    prev_col = filter_columns[i - 1] if i > 0 else "All"
    prev_selection = selected_filters.get(prev_col, "All")
    selected_filters[col] = st.sidebar.selectbox(f"Select {col}", filter_options(df_original, col, prev_col, prev_selection))

# Date range slider for better UX
min_date, max_date = df_original["Order Date"].min().date(), df_original["Order Date"].max().date()
default_date = (min_date, max_date)
date_range = st.sidebar.slider(
    "Date Range",
    min_value=min_date,
    max_value=max_date,
    value=default_date,
    format="MM/DD/YYYY"
)
from_date, to_date = date_range

# Apply filters efficiently
@st.cache_data
def filter_data(df, filters, from_date, to_date):
    df_filtered = df.copy()
    for key, value in filters.items():
        if value != "All":
            df_filtered = df_filtered[df_filtered[key] == value]
    return df_filtered[
        (df_filtered["Order Date"] >= pd.to_datetime(from_date)) &
        (df_filtered["Order Date"] <= pd.to_datetime(to_date))
    ]

df = filter_data(df_original, selected_filters, from_date, to_date)

# Main page with a cleaner title and intro
st.title("SuperStore KPI Dashboard")
st.markdown("Analyze sales, profit, and product performance with interactive filters and visualizations.")

# Handle empty data gracefully
if df.empty:
    st.warning("⚠ No data matches your filters. Please adjust your selections.")
    st.stop()

# KPI calculations with improved readability
kpi_metrics = {
    "Total Sales": df["Sales"].sum(),
    "Units Sold": df["Quantity"].sum(),
    "Total Profit": df["Profit"].sum(),
    "Profit Margin": (df["Profit"].sum() / df["Sales"].sum() * 100) if df["Sales"].sum() != 0 else 0
}

# Display KPIs in a responsive grid
st.subheader("Key Performance Indicators")
kpi_cols = st.columns(4)
for col, (title, value) in zip(kpi_cols, kpi_metrics.items()):
    help_text = f"{title} reflects the total {'percentage' if 'Margin' in title else 'value'} for the filtered data."
    col.metric(
        label=title,
        value=f"{value:.2f}%" if "Margin" in title else f"${value:,.2f}" if "Units" not in title else f"{value:,.0f}",
        help=help_text
    )

# Visualization section with tabs for clarity
st.subheader("Explore Trends and Insights")
tab1, tab2 = st.tabs(["KPI Trends", "Top Products"])

# KPI selection and time aggregation
selected_kpi = st.selectbox("Select KPI to Visualize", options=list(kpi_metrics.keys()), key="kpi_select")
time_aggregation = st.selectbox("Group Data By", ["Daily", "Weekly", "Monthly"], key="time_agg")

# Prepare data for trends
df["Year-Month"] = df["Order Date"].dt.to_period("M").astype(str)
df["Year-Week"] = df["Order Date"].dt.to_period("W").astype(str)
time_col = {"Daily": "Order Date", "Weekly": "Year-Week", "Monthly": "Year-Month"}[time_aggregation]
time_grouped = df.groupby(time_col).agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
time_grouped["Profit Margin"] = (time_grouped["Profit"] / time_grouped["Sales"] * 100).fillna(0)

kpi_mapping = {"Total Sales": "Sales", "Units Sold": "Quantity", "Total Profit": "Profit", "Profit Margin": "Profit Margin"}
selected_kpi_col = kpi_mapping[selected_kpi]

# Trends chart in Tab 1
with tab1:
    fig_time = px.line(
        time_grouped, x=time_col, y=selected_kpi_col, markers=True,
        title=f"{selected_kpi} Over Time",
        labels={time_col: "Date", selected_kpi_col: selected_kpi},
        template="plotly_white"
    )
    fig_time.update_layout(height=450, showlegend=False, hovermode="x unified")
    fig_time.update_traces(line=dict(width=2.5), marker=dict(size=8))
    st.plotly_chart(fig_time, use_container_width=True)

# Top products in Tab 2
with tab2:
    top_products = df.groupby("Product Name").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    top_products["Profit Margin"] = (top_products["Profit"] / top_products["Sales"] * 100).fillna(0)
    top_products = top_products.nlargest(10, selected_kpi_col)

    fig_bar = px.bar(
        top_products, x=selected_kpi_col, y="Product Name", orientation="h",
        title=f"Top 10 Products by {selected_kpi}",
        color=selected_kpi_col, color_continuous_scale="Blues",
        template="plotly_white"
    )
    fig_bar.update_layout(height=450, yaxis={"categoryorder": "total ascending"}, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# Additional insights with expander for less clutter
with st.expander("Additional Insights", expanded=False):
    st.markdown("### Detailed Data")
    st.dataframe(df.style.format({"Sales": "${:,.2f}", "Profit": "${:,.2f}", "Order Date": "{:%Y-%m-%d}"}))
    
    # Download option
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Filtered Data as CSV",
        data=csv,
        file_name="filtered_superstore_data.csv",
        mime="text/csv"
    )

# Footer with last update info
st.markdown(f"<small>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)
