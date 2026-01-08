import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("Purchase Order Status & Lead Time")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
po, gr, inv, cons = load_data()

# --------------------------------------------------
# PO STATUS DISTRIBUTION
# --------------------------------------------------
po_status = (
    po.groupby("po_status")
    .size()
    .reset_index(name="count")
)

fig = px.bar(
    po_status,
    x="po_status",
    y="count",
    title="PO Status Distribution"
)

st.plotly_chart(fig, use_container_width=True)
