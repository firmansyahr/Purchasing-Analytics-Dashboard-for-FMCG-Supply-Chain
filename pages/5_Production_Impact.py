import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.title("🏗️ Production Impact")

_, _, inv, cons, _ = load_data()

impact = cons.merge(inv, on="material_id", how="left")
impact["stockout_flag"] = impact["stock_on_hand"] < impact["consumed_qty"]

summary = impact.groupby("material_id")["stockout_flag"].mean().reset_index()

fig = px.bar(
    summary,
    x="material_id",
    y="stockout_flag",
    title="Production Risk Due to Material Shortage"
)

st.plotly_chart(fig, use_container_width=True)
