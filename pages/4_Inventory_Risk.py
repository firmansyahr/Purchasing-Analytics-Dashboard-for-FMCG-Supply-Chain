import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("Inventory Risk & Coverage Analysis")

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
    options=inv["material_name"].unique(),
    default=list(inv["material_name"].unique())
)

inv_f = inv[inv["material_name"].isin(material_filter)].copy()
cons_f = cons[cons["material_name"].isin(material_filter)].copy()

# --------------------------------------------------
# DERIVED METRICS
# --------------------------------------------------
# Days of Inventory
inv_f["days_of_inventory"] = inv_f["stock_on_hand"] / inv_f["daily_consumption"]

# Consumption volatility
cons_var = (
    cons_f.groupby("material_id")["consumed_qty"]
    .std()
    .reset_index(name="consumption_volatility")
)

inv_risk = inv_f.merge(cons_var, on="material_id", how="left").fillna(0)

# Normalization (safe guard)
inv_risk["doi_norm"] = inv_risk["days_of_inventory"] / inv_risk["days_of_inventory"].max()
inv_risk["vol_norm"] = (
    inv_risk["consumption_volatility"] /
    inv_risk["consumption_volatility"].max()
    if inv_risk["consumption_volatility"].max() > 0 else 0
)

# Composite inventory risk score
inv_risk["inventory_risk_score"] = (
    (1 - inv_risk["doi_norm"]) * 0.6 +
    inv_risk["vol_norm"] * 0.4
)

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
st.subheader("Inventory Risk KPIs")

TARGET_DOI = 14

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Avg Days of Inventory",
    f"{inv_risk['days_of_inventory'].mean():.1f} days"
)

c2.metric(
    "Materials Below Safety Stock",
    int((inv_risk["stock_on_hand"] < inv_risk["safety_stock"]).sum())
)

c3.metric(
    "Avg Inventory Risk Score",
    f"{inv_risk['inventory_risk_score'].mean():.2f}"
)

c4.metric(
    "High Risk Materials",
    int((inv_risk["inventory_risk_score"] > 0.6).sum())
)

# --------------------------------------------------
# INVENTORY HEALTH MATRIX
# --------------------------------------------------
st.subheader("Inventory Health Matrix")

fig_matrix = px.scatter(
    inv_risk,
    x="days_of_inventory",
    y="consumption_volatility",
    size="stock_on_hand",
    color="inventory_risk_score",
    hover_data=["material_name"],
    title="Inventory Health Matrix (Coverage vs Volatility)"
)

st.plotly_chart(fig_matrix, use_container_width=True)

# --------------------------------------------------
# EARLY WARNING – DAYS TO STOCKOUT
# --------------------------------------------------
st.subheader("Early Warning: Days to Stockout")

inv_risk["days_to_stockout"] = (
    inv_risk["stock_on_hand"] / inv_risk["daily_consumption"]
)

early_warning = inv_risk[inv_risk["days_to_stockout"] < TARGET_DOI]

if not early_warning.empty:
    st.warning(
        f"{len(early_warning)} material diperkirakan stockout dalam < {TARGET_DOI} hari."
    )
    st.dataframe(
        early_warning.sort_values("days_to_stockout")[
            ["material_name","days_to_stockout","stock_on_hand","daily_consumption"]
        ].head(10)
    )
else:
    st.success("Tidak ada material dengan risiko stockout dalam waktu dekat.")

# --------------------------------------------------
# RISK RANKING
# --------------------------------------------------
st.subheader("Top Inventory Risk Ranking")

risk_table = inv_risk.sort_values(
    "inventory_risk_score", ascending=False
)[
    ["material_name","days_of_inventory","consumption_volatility","inventory_risk_score"]
]

st.dataframe(risk_table.head(10))

# --------------------------------------------------
# AUTOMATED INSIGHTS
# --------------------------------------------------
st.subheader("Key Insights")

insights = []

high_risk_count = (inv_risk["inventory_risk_score"] > 0.6).sum()
if high_risk_count > 0:
    insights.append(
        f"{high_risk_count} material memiliki risiko inventory tinggi."
    )

low_doi = inv_risk[inv_risk["days_of_inventory"] < TARGET_DOI]
if not low_doi.empty:
    insights.append(
        f"{len(low_doi)} material memiliki Days of Inventory di bawah target {TARGET_DOI} hari."
    )

high_vol = inv_risk[
    inv_risk["consumption_volatility"] >
    inv_risk["consumption_volatility"].quantile(0.75)
]
if not high_vol.empty:
    insights.append(
        f"{len(high_vol)} material menunjukkan volatilitas konsumsi tinggi."
    )

for i in insights:
    st.markdown(f"- {i}")

# --------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# --------------------------------------------------
st.subheader("Recommended Inventory Actions")

actions = []

for _, r in inv_risk.iterrows():
    if r["inventory_risk_score"] > 0.6:
        actions.append({
            "Material": r["material_name"],
            "Risk Level": "High",
            "Recommended Action": "Increase safety stock or expedite PO"
        })
    elif r["days_of_inventory"] < TARGET_DOI:
        actions.append({
            "Material": r["material_name"],
            "Risk Level": "Medium",
            "Recommended Action": "Review reorder point"
        })

if actions:
    st.dataframe(pd.DataFrame(actions))
else:
    st.info("Tidak ada rekomendasi aksi inventory kritikal saat ini.")

# --------------------------------------------------
# FOOTNOTE
# --------------------------------------------------
st.caption(
    "Inventory risk dihitung dari Days of Inventory dan volatilitas konsumsi "
    "untuk mendukung pencegahan stockout."
)
