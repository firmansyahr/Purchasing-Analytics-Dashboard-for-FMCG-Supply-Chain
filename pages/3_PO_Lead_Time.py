import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("PO Lead Time and Delivery Performance")

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

# --------------------------------------------------
# JOIN PO + GR
# --------------------------------------------------
po_gr = po_f.merge(gr, on="po_number", how="left")

# --------------------------------------------------
# DERIVED METRICS
# --------------------------------------------------
today = pd.Timestamp.today().normalize()

po_gr["actual_lead_time"] = (
    po_gr["gr_date"] - po_gr["po_date"]
).dt.days

po_gr["current_age"] = (
    po_gr["gr_date"].fillna(today) - po_gr["po_date"]
).dt.days

po_gr["late_flag"] = (
    po_gr["gr_date"].notna() &
    (po_gr["gr_date"] > po_gr["expected_delivery_date"])
)

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
st.subheader("PO Lead Time KPIs")

TARGET_LT = 14

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Average Lead Time",
    f"{po_gr['actual_lead_time'].mean():.1f} days"
)

c2.metric(
    "Late PO Count",
    int(po_gr["late_flag"].sum())
)

c3.metric(
    "Late PO Rate",
    f"{po_gr['late_flag'].mean():.1%}"
)

c4.metric(
    "Open PO Aging (Avg)",
    f"{po_gr[po_gr['gr_date'].isna()]['current_age'].mean():.1f} days"
)

# --------------------------------------------------
# PO AGING DISTRIBUTION
# --------------------------------------------------
st.subheader("PO Aging Distribution")

po_gr["aging_bucket"] = pd.cut(
    po_gr["current_age"],
    bins=[0,7,14,30,999],
    labels=["0–7 days","8–14 days","15–30 days",">30 days"]
)

aging_dist = (
    po_gr.groupby("aging_bucket")
    .size()
    .reset_index(name="po_count")
)

fig_aging = px.bar(
    aging_dist,
    x="aging_bucket",
    y="po_count",
    title="PO Aging Bucket"
)

st.plotly_chart(fig_aging, use_container_width=True)

# --------------------------------------------------
# SUPPLIER BOTTLENECK
# --------------------------------------------------
st.subheader("Supplier Bottleneck Analysis")

supplier_lt = (
    po_gr.groupby("supplier_name")
    .agg(
        avg_lead_time=("actual_lead_time","mean"),
        late_rate=("late_flag","mean"),
        po_count=("po_number","nunique")
    )
    .reset_index()
)

fig_supplier = px.scatter(
    supplier_lt,
    x="avg_lead_time",
    y="late_rate",
    size="po_count",
    color="supplier_name",
    title="Supplier Lead Time vs Late Rate"
)

st.plotly_chart(fig_supplier, use_container_width=True)

# --------------------------------------------------
# MATERIAL BOTTLENECK
# --------------------------------------------------
st.subheader("Material Bottleneck Analysis")

material_lt = (
    po_gr.groupby("material_name")
    .agg(
        avg_lead_time=("actual_lead_time","mean"),
        late_rate=("late_flag","mean"),
        po_count=("po_number","nunique")
    )
    .reset_index()
)

st.dataframe(
    material_lt.sort_values("late_rate", ascending=False).head(10)
)

# --------------------------------------------------
# EARLY WARNING – OPEN & OVERDUE PO
# --------------------------------------------------
st.subheader("Early Warning: Overdue Open PO")

overdue_po = po_gr[
    (po_gr["gr_date"].isna()) &
    (po_gr["current_age"] > TARGET_LT)
]

if not overdue_po.empty:
    st.warning(
        f"Terdapat {len(overdue_po)} PO open yang melebihi target lead time."
    )
    st.dataframe(
        overdue_po[
            ["po_number","supplier_name","material_name","current_age"]
        ].sort_values("current_age", ascending=False).head(10)
    )
else:
    st.success("Tidak ada PO open yang melewati target lead time.")

# --------------------------------------------------
# AUTOMATED INSIGHTS
# --------------------------------------------------
st.subheader("Key Insights")

insights = []

if po_gr["late_flag"].mean() > 0.2:
    insights.append(
        "Tingkat keterlambatan PO cukup tinggi dan berpotensi "
        "mengganggu ketersediaan material."
    )

top_late_supplier = supplier_lt.sort_values(
    "late_rate", ascending=False
).iloc[0]

insights.append(
    f"Supplier dengan performa terburuk terkait lead time adalah "
    f"{top_late_supplier['supplier_name']}."
)

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# --------------------------------------------------
st.subheader("Recommended Actions")

actions = []

if not overdue_po.empty:
    actions.append({
        "Area": "PO Control",
        "Issue": "Overdue Open PO",
        "Recommended Action": "Follow-up supplier dan percepat pengiriman"
    })

if top_late_supplier["late_rate"] > 0.3:
    actions.append({
        "Area": "Supplier Management",
        "Issue": f"High Late Rate – {top_late_supplier['supplier_name']}",
        "Recommended Action": "Review SLA dan evaluasi kapasitas supplier"
    })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.success("Tidak ada tindakan kritikal terkait PO lead time.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Analisis PO lead time ini digunakan untuk memantau keterlambatan, "
    "mengidentifikasi bottleneck supplier/material, dan mendukung "
    "kontrol operasional supply chain."
)
