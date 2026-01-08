import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.title("📑 Purchase Order & Lead Time")

po, gr, _, _, _ = load_data()

po_status = po.groupby("po_status").size().reset_index(name="count")

fig = px.bar(
    po_status,
    x="po_status",
    y="count",
    title="PO Status Distribution"
)

st.plotly_chart(fig, use_container_width=True)
