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
po, gr, inv, cons, sup = load_data()

# --------------------------------------------------
# GLOBAL FILTER
# --------------------------------------------------
st.sidebar.header("Global Filters")

supplier_filter = st.sidebar.multiselect(
    "Supplier",
    options=sup["supplier_id"].unique(),
    default=sup["supplier_id"].unique()
)

sup_f = sup[sup["supplier_id"].isin(supplier_filter)]
po_f = po[po["supplier_id"].isin(supplier_filter)]

# --------------------------------------------------
# DERIVED METRICS
# --------------------------------------------------
# Spend per supplier
supplier_spend = (
    po_f.assign(spend=lambda x: x["ordered_qty"] * x["unit_price"])
    .groupby("supplier_id")["spend"]
    .sum()
    .reset_index()
)

supplier_df = sup_f.merge(supplier_spend, on="supplier_id", how="left").fillna(0)

# Lead time variability proxy
supplier_df["lead_time_risk"] = supplier_df["avg_lead_time"] / supplier_df["avg_lead_time"].mean()

# Composite risk score (weighted)
supplier_df["risk_score"] = (
    (1 - supplier_df["on_time_delivery_rate"]) * 0.4 +
    supplier_df["rejection_rate"] * 0.3 +
    supplier_df["price_variance"].abs() * 0.2 +
    (supplier_df["avg_lead_time"] / supplier_df["avg_lead_time"].max()) * 0.1
)

# Dependency (% spend)
supplier_df["dependency"] = supplier_df["spend"] / supplier_df["spend"].sum()

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
st.subheader("Supplier Performance KPIs")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Avg On-Time Delivery", f"{supplier_df['on_time_delivery_rate'].mean():.1%}")
c2.metric("Avg Lead Time", f"{supplier_df['avg_lead_time'].mean():.1f} days")
c3.metric("Avg Rejection Rate", f"{supplier_df['rejection_rate'].mean():.1%}")
c4.metric("Total Supplier Spend", f"Rp {supplier_df['spend'].sum():,.0f}")

# --------------------------------------------------
# SUPPLIER SEGMENTATION
# --------------------------------------------------
st.subheader("Supplier Segmentation")

def classify_supplier(row):
    if row["dependency"] > 0.15 and row["risk_score"] < 0.15:
        return "Strategic"
    elif row["dependency"] > 0.15 and row["risk_score"] >= 0.15:
        return "Bottleneck"
    elif row["dependency"] <= 0.15 and row["risk_score"] < 0.15:
        return "Leverage"
    else:
        return "Routine"

supplier_df["segment"] = supplier_df.apply(classify_supplier, axis=1)

fig_seg = px.scatter(
    supplier_df,
    x="dependency",
    y="risk_score",
    size="spend",
    color="segment",
    hover_data=["supplier_id"],
    title="Supplier Segmentation Matrix (Dependency vs Risk)"
)

st.plotly_chart(fig_seg, use_container_width=True)

# --------------------------------------------------
# SUPPLIER RISK RANKING
# --------------------------------------------------
st.subheader("Top Supplier Risk Ranking")

risk_table = supplier_df.sort_values("risk_score", ascending=False)[
    ["supplier_id","segment","risk_score","on_time_delivery_rate","avg_lead_time","rejection_rate","dependency"]
]

st.dataframe(risk_table.head(10))

# --------------------------------------------------
# AUTOMATED INSIGHTS
# --------------------------------------------------
st.subheader("📌 Key Insights")

insights = []

high_risk = supplier_df[supplier_df["risk_score"] > 0.2]
if not high_risk.empty:
    insights.append(
        f"⚠️ {len(high_risk)} supplier memiliki risk score tinggi (>0.2) dan berpotensi mengganggu supply."
    )

bottleneck = supplier_df[supplier_df["segment"] == "Bottleneck"]
if not bottleneck.empty:
    insights.append(
        f"🚨 {len(bottleneck)} supplier tergolong Bottleneck (dependensi tinggi + risiko tinggi)."
    )

price_risk = supplier_df[supplier_df["price_variance"].abs() > 0.1]
if not price_risk.empty:
    insights.append(
        f"💸 {len(price_risk)} supplier menunjukkan volatilitas harga tinggi."
    )

if insights:
    for i in insights:
        st.markdown(f"- {i}")
else:
    st.success("✅ Tidak ditemukan risiko supplier signifikan pada periode ini.")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# --------------------------------------------------
st.subheader("✅ Recommended Supplier Actions")

actions = []

for _, r in supplier_df.iterrows():
    if r["segment"] == "Bottleneck":
        actions.append({
            "Supplier": r["supplier_id"],
            "Segment": r["segment"],
            "Risk Level": "High",
            "Recommended Action": "Develop alternative supplier / renegotiate SLA"
        })
    elif r["segment"] == "Strategic":
        actions.append({
            "Supplier": r["supplier_id"],
            "Segment": r["segment"],
            "Risk Level": "Low",
            "Recommended Action": "Long-term contract & collaboration"
        })
    elif r["price_variance"] > 0.1:
        actions.append({
            "Supplier": r["supplier_id"],
            "Segment": r["segment"],
            "Risk Level": "Medium",
            "Recommended Action": "Price review & cost breakdown analysis"
        })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.info("Tidak ada rekomendasi aksi kritikal saat ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Supplier risk score dihitung menggunakan pendekatan multi-metric untuk mendukung keputusan strategis procurement."
)
