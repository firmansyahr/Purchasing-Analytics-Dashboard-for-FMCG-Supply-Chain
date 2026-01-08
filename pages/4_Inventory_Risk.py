import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.title("📦 Inventory Risk & Coverage")

_, _, inv, _, _ = load_data()

inv["days_of_inventory"] = inv["stock_on_hand"] / inv["daily_consumption"]

fig = px.histogram(
    inv,
    x="days_of_inventory",
    nbins=30,
    title="Days of Inventory Distribution"
)

st.plotly_chart(fig, use_container_width=True)

risk = inv[inv["stock_on_hand"] < inv["safety_stock"]]
st.subheader("⚠️ Material Below Safety Stock")
st.dataframe(risk.head(15))
