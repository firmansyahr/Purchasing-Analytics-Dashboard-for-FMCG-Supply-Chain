import streamlit as st
import pandas as pd
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
po, gr, inv, cons = load_data()

# --------------------------------------------------
# GLOBAL FILTER (SIDEBAR)
# --------------------------------------------------
st.sidebar.header("Global Filters")

date_min = po["po_date"].min()
date_max = po["po_date"].max()

date_range = st.sidebar.date_input(
    "PO Date Range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max
)

supplier_filter = st.sidebar.multiselect(
    "Supplier",
    options=po["supplier_name"].unique(),
    default=po["supplier_name"].unique()
)

material_filter = st.sidebar.multiselect(
    "Material",
    options=po["material_name"].unique(),
    default=po["material_name"].unique()
)

# --------------------------------------------------
# APPLY FILTER
# --------------------------------------------------
po_f = po[
    (po["po_date"] >= pd.to_datetime(date_range[0])) &
    (po["po_date"] <= pd.to_datetime(date_range[1])) &
    (po["supplier_name"].isin(supplier_filter)) &
    (po["material_name"].isin(material_filter))
]

inv_f = inv[inv["material_name"].isin(material_filter)]

# --------------------------------------------------
# DERIVED METRICS (PO + GR)
# --------------------------------------------------
po_gr = po_f.merge(gr, on="po_number", how="left")

po_gr["actual_lead_time"] = (
    po_gr["gr_date"] - po_gr["po_date"]
).dt.days

on_time_po = po_gr[
    po_gr["gr_date"].notna() &
