"""Interactive dashboard for the cleaned UCI Online Retail data."""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB = Path("output/retail.db")
st.set_page_config(page_title="Retail Sales Analysis", layout="wide")
st.title("Retail Sales Analysis")
st.caption("Completed positive-value sales only · Revenue = Quantity × UnitPrice · Currency: GBP")
if not DB.is_file():
    st.info("First run: python src/prepare.py data/Online_Retail.xlsx")
    st.stop()

@st.cache_data

def get_data():
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query("SELECT * FROM transactions", conn, parse_dates=["InvoiceDate"])

data = get_data()
countries = sorted(data["Country"].dropna().unique().tolist())
chosen = st.multiselect("Filter countries", countries, default=countries)
filtered = data[data["Country"].isin(chosen)]
if filtered.empty:
    st.warning("No transactions match this filter.")
    st.stop()

revenue = filtered["Revenue"].sum()
orders = filtered["InvoiceNo"].nunique()
customers = filtered["CustomerID"].nunique(dropna=True)
a, b, c, d = st.columns(4)
a.metric("Sales value (GBP)", f"£{revenue:,.2f}")
b.metric("Orders", f"{orders:,}")
c.metric("Average order value", f"£{revenue / orders:,.2f}")
d.metric("Identified customers", f"{customers:,}")

monthly = filtered.assign(Month=filtered["InvoiceDate"].dt.to_period("M").astype(str)).groupby("Month", as_index=False)["Revenue"].sum()
st.subheader("Monthly sales value")
st.line_chart(monthly.set_index("Month"))
left, right = st.columns(2)
with left:
    st.subheader("Top 10 products by sales value")
    products = (filtered.groupby(["StockCode", "Description"], dropna=False)["Revenue"]
                .sum().sort_values(ascending=False).head(10).reset_index())
    products["Product"] = products["Description"].fillna(products["StockCode"])
    st.bar_chart(products.set_index("Product")["Revenue"])
with right:
    st.subheader("Top 10 countries by sales value")
    country = filtered.groupby("Country")["Revenue"].sum().sort_values(ascending=False).head(10)
    st.bar_chart(country)
st.download_button("Download filtered transactions", filtered.to_csv(index=False).encode(), "retail_filtered.csv", "text/csv")
st.caption("Customer count excludes missing customer IDs. Canceled, zero/negative quantity or price, and duplicate rows are excluded during cleaning.")
