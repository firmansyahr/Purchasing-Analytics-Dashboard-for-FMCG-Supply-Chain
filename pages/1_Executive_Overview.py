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

po_f = po[
    (po["supplier_name"].isin(supplier_filter)) &
    (po["material_name"].isin(material_filter))
].copy()

inv_f = inv[inv["material_name"].isin(material_filter)].copy()

# --------------------------------------------------
# KPI CALCULATION
# --------------------------------------------------
total_spend = (po_f["ordered_qty"] * po_f["unit_price"]).sum()

open_po = po_f[po_f["po_status"] == "Open"].shape[0]

materials_below_ss = (
    inv_f["stock_on_hand"] < inv_f["safety_stock"]
).sum()

# On-time delivery (PO + GR)
po_gr = po_f.merge(gr, on="po_number", how="left")

on_time_po = po_gr[
    po_gr["gr_date"].notna() &
    (po_gr["gr_date"] <= po_gr["expected_delivery_date"])
]

otd_rate = (
    len(on_time_po) / po_gr["po_number"].nunique()
    if po_gr["po_number"].nunique() > 0 else 0
)

# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------
st.subheader("Key Performance Indicators")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Spend", f"Rp {total_spend:,.0f}")
c2.metric("Open PO", int(open_po))
c3.metric("On-Time Delivery Rate", f"{otd_rate:.1%}")
c4.metric("Materials Below Safety Stock", int(materials_below_ss))

# --------------------------------------------------
# SPEND TREND
# --------------------------------------------------
st.subheader("Purchasing Spend Trend")

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
# EXECUTIVE INSIGHTS
# --------------------------------------------------
st.subheader("Executive Insights")

insights = []

late_po = po_gr[
    po_gr["gr_date"].notna() &
    (po_gr["gr_date"] > po_gr["expected_delivery_date"])
]

if not late_po.empty:
    top_late_supplier = (
        late_po["supplier_name"]
        .value_counts()
        .idxmax()
    )
    insights.append(
        f"Supplier dengan keterlambatan pengiriman tertinggi adalah "
        f"{top_late_supplier}."
    )

if materials_below_ss > 0:
    insights.append(
        f"Terdapat {materials_below_ss} material dengan stok di bawah safety stock."
    )

top_spend_supplier = (
    po_f.assign(spend=lambda x: x["ordered_qty"] * x["unit_price"])
    .groupby("supplier_name")["spend"]
    .sum()
    .idxmax()
)

insights.append(
    f"Nilai pembelian terbesar berasal dari {top_spend_supplier}."
)

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# ACTION SUMMARY
# --------------------------------------------------
st.subheader("Priority Actions")

actions = []

if materials_below_ss > 0:
    actions.append({
        "Area": "Inventory",
        "Issue": "Below Safety Stock",
        "Recommended Action": "Expedite PO or review safety stock level"
    })

if not late_po.empty:
    actions.append({
        "Area": "Supplier Performance",
        "Issue": "Frequent Delivery Delay",
        "Recommended Action": "Conduct supplier review and SLA discussion"
    })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.success("Tidak ada isu kritikal pada periode ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Executive overview ini menyajikan ringkasan kinerja purchasing, "
    "risiko supply, dan area prioritas tindakan untuk manajemen."
)
