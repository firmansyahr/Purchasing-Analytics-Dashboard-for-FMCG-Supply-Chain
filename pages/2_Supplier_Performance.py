import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.title("🏭 Supplier Performance")

_, _, _, _, sup = load_data()

fig = px.scatter(
    sup,
    x="price_variance",
    y="on_time_delivery_rate",
    size="service_level",
    color="supplier_id",
    hover_data=["rejection_rate"],
    title="Supplier Price vs Delivery Performance"
)

st.plotly_chart(fig, use_container_width=True)
