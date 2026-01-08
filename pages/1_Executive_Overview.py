import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("📊 Executive Purchasing Overview")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
po, gr, inv, cons, sup = load_data()

# --------------------------------------------------
# GLOBAL FILTER (SIDEBAR)
# --------------------------------------------------
st.sidebar.header("Global Filters")

# Date filter
date_min = po["po_date"].min()
date_max = po["po_date"].max()

date_range = st.sidebar.date_input(
    "PO Date Range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max
)

# Supplier filter
supplier_filter = st.sidebar.multiselect(
    "Supplier",
    options=po["supplier_id"].unique(),
    default=po["supplier_id"].unique()
)

# Material filter
material_filter = st.sidebar.multiselect(
    "Material",
    options=po["material_id"].unique(),
    default=po["material_id"].unique()
)

# --------------------------------------------------
# APPLY FILTER
# --------------------------------------------------
po_f = po[
    (po["po_date"] >= pd.to_datetime(date_range[0])) &
    (po["po_date"] <= pd.to_datetime(date_range[1])) &
    (po["supplier_id"].isin(supplier_filter)) &
    (po["material_id"].isin(material_filter))
]

inv_f = inv[inv["material_id"].isin(material_filter)]
sup_f = sup[sup["supplier_id"].isin(supplier_filter)]

# --------------------------------------------------
# KPI CALCULATION
# --------------------------------------------------
total_spend = (po_f["ordered_qty"] * po_f["unit_price"]).sum()
avg_otd = sup_f["on_time_delivery_rate"].mean()
avg_lead_time = sup_f["avg_lead_time"].mean()
stockout_ratio = (inv_f["stock_on_hand"] < inv_f["safety_stock"]).mean()

# Target (assumption – portfolio friendly)
TARGET_OTD = 0.95
TARGET_LT = 14
TARGET_STOCKOUT = 0.05

# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------
st.subheader("Key Performance Indicators")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Spend",
    f"Rp {total_spend:,.0f}"
)

c2.metric(
    "On-Time Delivery",
    f"{avg_otd:.1%}",
    delta=f"{avg_otd - TARGET_OTD:.1%}"
)

c3.metric(
    "Avg Lead Time (days)",
    f"{avg_lead_time:.1f}",
    delta=f"{TARGET_LT - avg_lead_time:.1f}"
)

c4.metric(
    "Stockout Risk",
    f"{stockout_ratio:.1%}",
    delta=f"{TARGET_STOCKOUT - stockout_ratio:.1%}"
)

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
    markers=True,
    title="Monthly Purchasing Spend Trend"
)

st.plotly_chart(fig_trend, use_container_width=True)

# --------------------------------------------------
# INSIGHT ENGINE (RULE-BASED)
# --------------------------------------------------
st.subheader("📌 Executive Insights")

insights = []

# Insight 1: Supplier performance risk
low_otd_supplier = sup_f[sup_f["on_time_delivery_rate"] < 0.9]
if not low_otd_supplier.empty:
    insights.append(
        f"⚠️ {len(low_otd_supplier)} supplier memiliki on-time delivery < 90%."
    )

# Insight 2: Inventory risk
critical_material = inv_f[inv_f["stock_on_hand"] < inv_f["safety_stock"]]
if not critical_material.empty:
    insights.append(
        f"⚠️ {critical_material['material_id'].nunique()} material berada di bawah safety stock."
    )

# Insight 3: Lead time risk
slow_supplier = sup_f[sup_f["avg_lead_time"] > TARGET_LT]
if not slow_supplier.empty:
    insights.append(
        f"⏳ {len(slow_supplier)} supplier memiliki lead time di atas standar ({TARGET_LT} hari)."
    )

if insights:
    for i in insights:
        st.markdown(f"- {i}")
else:
    st.success("✅ Tidak ada risiko utama terdeteksi pada periode ini.")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATION TABLE
# --------------------------------------------------
st.subheader("✅ Recommended Actions")

action_table = []

for _, row in critical_material.iterrows():
    action_table.append({
        "Material": row["material_id"],
        "Issue": "Below Safety Stock",
        "Risk Level": "High",
        "Recommended Action": "Expedite PO / Increase Safety Stock"
    })

for _, row in low_otd_supplier.iterrows():
    action_table.append({
        "Supplier": row["supplier_id"],
        "Issue": "Low On-Time Delivery",
        "Risk Level": "Medium",
        "Recommended Action": "Supplier review & renegotiation"
    })

if action_table:
    st.dataframe(pd.DataFrame(action_table))
else:
    st.info("Tidak ada rekomendasi aksi kritikal pada periode ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Insight dihasilkan otomatis berdasarkan rule-based analytics untuk mendukung keputusan eksekutif."
)
