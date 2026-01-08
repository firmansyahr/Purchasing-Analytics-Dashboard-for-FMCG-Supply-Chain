import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import load_data

st.set_page_config(layout="wide")
st.title("🏭 Supplier Performance & Risk Analysis")

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
    default=po["supplier_name"].unique()
)

po_f = po[po["supplier_name"].isin(supplier_filter)]

# --------------------------------------------------
# JOIN PO + GR
# --------------------------------------------------
po_gr = po_f.merge(gr, on="po_number", how="left")

po_gr["lead_time"] = (
    po_gr["gr_date"] - po_gr["po_date"]
).dt.days

# --------------------------------------------------
# DERIVED SUPPLIER METRICS
# --------------------------------------------------
supplier_df = (
    po_gr.groupby("supplier_name")
    .agg(
        total_po=("po_number", "nunique"),
        total_spend=("ordered_qty", lambda x: (x * po_gr.loc[x.index, "unit_price"]).sum()),
        avg_lead_time=("lead_time", "mean"),
        late_delivery_rate=(
            "po_number",
            lambda x: (
                po_gr.loc[x.index, "gr_date"] >
                po_gr.loc[x.index, "expected_delivery_date"]
            ).mean()
        ),
        rejection_rate=(
            "rejected_qty",
            lambda x: x.sum() / po_gr.loc[x.index, "received_qty"].sum()
            if po_gr.loc[x.index, "received_qty"].sum() > 0 else 0
        )
    )
    .reset_index()
)

# Dependency (% spend)
supplier_df["dependency"] = supplier_df["total_spend"] / supplier_df["total_spend"].sum()

# Composite risk score (realistic & explainable)
supplier_df["risk_score"] = (
    supplier_df["late_delivery_rate"] * 0.5 +
    supplier_df["rejection_rate"] * 0.3 +
    (supplier_df["avg_lead_time"] / supplier_df["avg_lead_time"].max()) * 0.2
)

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
st.subheader("Supplier Performance KPIs")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Avg Lead Time", f"{supplier_df['avg_lead_time'].mean():.1f} days")
c2.metric("Avg Late Delivery Rate", f"{supplier_df['late_delivery_rate'].mean():.1%}")
c3.metric("Avg Rejection Rate", f"{supplier_df['rejection_rate'].mean():.1%}")
c4.metric("Total Spend", f"Rp {supplier_df['total_spend'].sum():,.0f}")

# --------------------------------------------------
# SUPPLIER SEGMENTATION
# --------------------------------------------------
st.subheader("Supplier Segmentation (Dependency vs Risk)")

def classify_supplier(row):
    if row["dependency"] > 0.15 and row["risk_score"] < 0.2:
        return "Strategic"
    elif row["dependency"] > 0.15 and row["risk_score"] >= 0.2:
        return "Bottleneck"
    elif row["dependency"] <= 0.15 and row["risk_score"] < 0.2:
        return "Leverage"
    else:
        return "Routine"

supplier_df["segment"] = supplier_df.apply(classify_supplier, axis=1)

fig_seg = px.scatter(
    supplier_df,
    x="dependency",
    y="risk_score",
    size="total_spend",
    color="segment",
    hover_data=["supplier_name"],
    title="Supplier Segmentation Matrix"
)

st.plotly_chart(fig_seg, use_container_width=True)

# --------------------------------------------------
# SUPPLIER RISK RANKING
# --------------------------------------------------
st.subheader("Top Supplier Risk Ranking")

risk_table = supplier_df.sort_values("risk_score", ascending=False)[
    [
        "supplier_name",
        "segment",
        "risk_score",
        "avg_lead_time",
        "late_delivery_rate",
        "rejection_rate",
        "dependency"
    ]
]

st.dataframe(risk_table.head(10))

# --------------------------------------------------
# AUTOMATED INSIGHTS
# --------------------------------------------------
st.subheader("📌 Key Insights")

insights = []

high_risk = supplier_df[supplier_df["risk_score"] > 0.4]
if not high_risk.empty:
    insights.append(
        f"🚨 {len(high_risk)} supplier memiliki risiko tinggi terhadap kontinuitas supply."
    )

bottleneck = supplier_df[supplier_df["segment"] == "Bottleneck"]
if not bottleneck.empty:
    insights.append(
        f"⚠️ Supplier bottleneck utama adalah "
        f"**{bottleneck.iloc[0]['supplier_name']}**."
    )

slowest = supplier_df.sort_values("avg_lead_time", ascending=False).iloc[0]
insights.append(
    f"⏳ Supplier dengan lead time terlama adalah "
    f"**{slowest['supplier_name']}**."
)

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# --------------------------------------------------
st.subheader("✅ Recommended Supplier Actions")

actions = []

for _, r in supplier_df.iterrows():
    if r["segment"] == "Bottleneck":
        actions.append({
            "Supplier": r["supplier_name"],
            "Risk Level": "High",
            "Recommended Action": "Develop alternative supplier / renegotiate SLA"
        })
    elif r["segment"] == "Strategic":
        actions.append({
            "Supplier": r["supplier_name"],
            "Risk Level": "Low",
            "Recommended Action": "Long-term partnership & volume commitment"
        })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.success("Tidak ada rekomendasi aksi kritikal pada periode ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Analisis supplier berbasis performa aktual PO dan Goods Receipt "
    "untuk mendukung keputusan strategis procurement."
)
