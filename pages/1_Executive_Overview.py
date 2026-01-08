import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("Executive Purchasing Overview")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
po, gr, inv, cons = load_data()

# --------------------------------------------------
# GLOBAL FILTER
# --------------------------------------------------
st.sidebar.header("Global Filters")

date_min = po["po_date"].min()
date_max = po["po_date"].max()

date_input = st.sidebar.date_input(
    "PO Date Range",
    value=[date_min, date_max]
)

# SAFETY GUARD (WAJIB)
if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
    start_date, end_date = pd.to_datetime(date_input[0]), pd.to_datetime(date_input[1])
else:
    start_date = end_date = pd.to_datetime(date_input)

supplier_filter = st.sidebar.multiselect(
    "Supplier",
    options=po["supplier_name"].unique(),
    default=list(po["supplier_name"].unique())
)

material_filter = st.sidebar.multiselect(
    "Material",
    options=po["material_name"].unique(),
    default=list(po["material_name"].unique())
)

# --------------------------------------------------
# APPLY FILTER
# --------------------------------------------------
po_f = po[
    (po["po_date"] >= start_date) &
    (po["po_date"] <= end_date) &
    (po["supplier_name"].isin(supplier_filter)) &
    (po["material_name"].isin(material_filter))
].copy()

inv_f = inv[inv["material_name"].isin(material_filter)].copy()

# --------------------------------------------------
# JOIN PO + GR
# --------------------------------------------------
po_gr = po_f.merge(gr, on="po_number", how="left")

po_gr["actual_lead_time"] = (
    po_gr["gr_date"] - po_gr["po_date"]
).dt.days

on_time_po = po_gr[
    po_gr["gr_date"].notna() &
    (po_gr["gr_date"] <= po_gr["expected_delivery_date"])
]

# --------------------------------------------------
# KPI CALCULATION
# --------------------------------------------------
total_spend = (po_f["ordered_qty"] * po_f["unit_price"]).sum()

avg_otd = (
    len(on_time_po) / po_gr["po_number"].nunique()
    if po_gr["po_number"].nunique() > 0 else 0
)

avg_lead_time = po_gr["actual_lead_time"].mean()

stockout_ratio = (inv_f["stock_on_hand"] < inv_f["safety_stock"]).mean()

# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------
st.subheader("Key Performance Indicators")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Spend", f"Rp {total_spend:,.0f}")
c2.metric("On-Time Delivery", f"{avg_otd:.1%}")
c3.metric("Avg Lead Time (days)", f"{avg_lead_time:.1f}")
c4.metric("Stockout Risk", f"{stockout_ratio:.1%}")

# --------------------------------------------------
# TREND ANALYSIS
# --------------------------------------------------
st.subheader("Spend Trend")

po_f["month"] = po_f["po_date"].dt.to_period("M").astype(str)

spend_trend = (
    po_f.groupby("month")
    .apply(lambda x: (x["ordered_qty"] * x["unit_price"]).sum())
    .reset_index(name="total_spend")
)

fig_trend = px.line(
    spend_trend,
    x="month",
    y="total_spend",
    markers=True
)

st.plotly_chart(fig_trend, use_container_width=True)

# --------------------------------------------------
# INSIGHTS
# --------------------------------------------------
st.subheader("Executive Insights")

insights = []

late_supplier = (
    po_gr[
        po_gr["gr_date"].notna() &
        (po_gr["gr_date"] > po_gr["expected_delivery_date"])
    ]
    .groupby("supplier_name")
    .size()
    .sort_values(ascending=False)
)

if not late_supplier.empty:
    insights.append(
        f"Supplier dengan keterlambatan tertinggi adalah "
        f"{late_supplier.index[0]}."
    )

critical_material = inv_f[inv_f["stock_on_hand"] < inv_f["safety_stock"]]

if not critical_material.empty:
    insights.append(
        f"{critical_material['material_name'].nunique()} material "
        f"berada di bawah safety stock."
    )

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Executive overview ini dirancang untuk memantau risiko supply, "
    "kin
