import streamlit as st
from utils.data_loader import load_data

st.title("📊 Executive Purchasing Overview")

po, gr, inv, cons, sup = load_data()

total_spend = (po["ordered_qty"] * po["unit_price"]).sum()
on_time_rate = sup["on_time_delivery_rate"].mean()
avg_lead_time = sup["avg_lead_time"].mean()
stockout_risk = (inv["stock_on_hand"] < inv["safety_stock"]).mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Spend", f"Rp {total_spend:,.0f}")
c2.metric("On-Time Delivery", f"{on_time_rate:.2%}")
c3.metric("Avg Lead Time (days)", f"{avg_lead_time:.1f}")
c4.metric("Stockout Risk", f"{stockout_risk:.1%}")
