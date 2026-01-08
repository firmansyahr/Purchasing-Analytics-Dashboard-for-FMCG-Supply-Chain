import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("Production Impact Analysis")

# --------------------------------------------------
# LOAD DATA (4 OBJECTS ONLY)
# --------------------------------------------------
po, gr, inv, cons = load_data()

# --------------------------------------------------
# GLOBAL FILTER
# --------------------------------------------------
st.sidebar.header("Global Filters")

material_filter = st.sidebar.multiselect(
    "Material",
    options=cons["material_name"].unique(),
    default=list(cons["material_name"].unique())
)

product_filter = st.sidebar.multiselect(
    "Product",
    options=cons["product_name"].unique(),
    default=list(cons["product_name"].unique())
)

cons_f = cons[
    (cons["material_name"].isin(material_filter)) &
    (cons["product_name"].isin(product_filter))
].copy()

inv_f = inv[inv["material_name"].isin(material_filter)].copy()

# --------------------------------------------------
# MATERIAL → PRODUCTION EXPOSURE
# --------------------------------------------------
prod_exposure = (
    cons_f.groupby(
        ["material_id", "material_name", "product_id", "product_name"]
    )["consumed_qty"]
    .sum()
    .reset_index()
)

# Merge inventory
impact_df = prod_exposure.merge(
    inv_f[
        ["material_id", "material_name", "stock_on_hand", "daily_consumption"]
    ],
    on=["material_id", "material_name"],
    how="left"
)

# --------------------------------------------------
# DERIVED METRICS
# --------------------------------------------------
# Days to stockout (safe)
impact_df["days_to_stockout"] = np.where(
    impact_df["daily_consumption"] > 0,
    impact_df["stock_on_hand"] / impact_df["daily_consumption"],
    np.nan
)

# Production loss proxy
impact_df["production_loss_units"] = np.where(
    impact_df["days_to_stockout"] < 7,
    impact_df["consumed_qty"],
    impact_df["consumed_qty"] * 0.3
)

# Revenue loss assumption
ASSUMED_UNIT_REVENUE = 15000
impact_df["estimated_revenue_loss"] = (
    impact_df["production_loss_units"] * ASSUMED_UNIT_REVENUE
)

# Normalize safely
impact_df["loss_norm"] = (
    impact_df["production_loss_units"] /
    impact_df["production_loss_units"].max()
    if impact_df["production_loss_units"].max() > 0 else 0
)

impact_df["stockout_norm"] = np.where(
    impact_df["days_to_stockout"] > 0,
    1 / impact_df["days_to_stockout"],
    0
)

# Composite impact risk score
impact_df["impact_risk_score"] = (
    impact_df["stockout_norm"] * 0.6 +
    impact_df["loss_norm"] * 0.4
)

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
st.subheader("Production Impact KPIs")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Materials at Risk",
    int(impact_df[impact_df["days_to_stockout"] < 7]["material_name"].nunique())
)

c2.metric(
    "Estimated Production Loss (Units)",
    f"{int(impact_df['production_loss_units'].sum()):,}"
)

c3.metric(
    "Estimated Revenue Loss",
    f"Rp {impact_df['estimated_revenue_loss'].sum():,.0f}"
)

c4.metric(
    "Avg Days to Stockout",
    f"{impact_df['days_to_stockout'].mean():.1f}"
)

# --------------------------------------------------
# MATERIAL → PRODUCT IMPACT MATRIX
# --------------------------------------------------
st.subheader("Material to Product Impact Mapping")

fig_matrix = px.scatter(
    impact_df,
    x="days_to_stockout",
    y="production_loss_units",
    size="estimated_revenue_loss",
    color="material_name",
    hover_data=["product_name"],
    title="Production Exposure Matrix"
)

st.plotly_chart(fig_matrix, use_container_width=True)

# --------------------------------------------------
# TOP PRODUCTION RISK
# --------------------------------------------------
st.subheader("Top Production Risk Ranking")

risk_table = impact_df.sort_values(
    "impact_risk_score", ascending=False
)[
    [
        "material_name",
        "product_name",
        "days_to_stockout",
        "production_loss_units",
        "estimated_revenue_loss",
        "impact_risk_score"
    ]
]

st.dataframe(risk_table.head(10))

# --------------------------------------------------
# WHAT-IF SCENARIO
# --------------------------------------------------
st.subheader("What-if Scenario: Improve Inventory Coverage")

coverage_improvement = st.slider(
    "Increase Inventory Coverage (%)",
    min_value=0,
    max_value=50,
    value=20,
    step=5
)

impact_df["adjusted_stock"] = impact_df["stock_on_hand"] * (
    1 + coverage_improvement / 100
)

impact_df["adjusted_days_to_stockout"] = np.where(
    impact_df["daily_consumption"] > 0,
    impact_df["adjusted_stock"] / impact_df["daily_consumption"],
    np.nan
)

impact_df["adjusted_revenue_loss"] = np.where(
    impact_df["adjusted_days_to_stockout"] < 7,
    impact_df["estimated_revenue_loss"],
    impact_df["estimated_revenue_loss"] * 0.4
)

saving = (
    impact_df["estimated_revenue_loss"].sum() -
    impact_df["adjusted_revenue_loss"].sum()
)

st.metric(
    "Estimated Revenue Loss After Improvement",
    f"Rp {impact_df['adjusted_revenue_loss'].sum():,.0f}",
    delta=f"-Rp {saving:,.0f}"
)

# --------------------------------------------------
# AUTOMATED INSIGHTS
# --------------------------------------------------
st.subheader("Key Insights")

insights = []

high_risk = impact_df[impact_df["impact_risk_score"] > 0.6]
if not high_risk.empty:
    insights.append(
        f"{len(high_risk)} kombinasi material–produk berisiko tinggi "
        f"mengganggu produksi."
    )

top_loss = impact_df.sort_values(
    "estimated_revenue_loss", ascending=False
).iloc[0]

insights.append(
    f"Risiko kerugian terbesar berasal dari material "
    f"{top_loss['material_name']} untuk produk "
    f"{top_loss['product_name']} "
    f"dengan estimasi Rp {top_loss['estimated_revenue_loss']:,.0f}."
)

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# --------------------------------------------------
st.subheader("Recommended Actions")

actions = []

for _, r in impact_df.iterrows():
    if r["days_to_stockout"] < 7:
        actions.append({
            "Material": r["material_name"],
            "Product": r["product_name"],
            "Risk Level": "High",
            "Recommended Action": (
                "Expedite PO, increase safety stock, "
                "or activate alternative supplier"
            )
        })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.success("Tidak ada risiko produksi kritikal pada periode ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Production impact dianalisis dari eksposur konsumsi material, "
    "ketersediaan inventory, dan estimasi kerugian produksi "
    "untuk mendukung keputusan operasional dan strategis."
)
