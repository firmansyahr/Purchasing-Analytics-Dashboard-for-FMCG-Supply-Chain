import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    file_path = "data/FMCG_Purchasing_Dataset.xlsx"

    po = pd.read_excel(file_path, sheet_name="Purchase_Order", parse_dates=["po_date","expected_delivery_date"])
    gr = pd.read_excel(file_path, sheet_name="Goods_Receipt", parse_dates=["gr_date"])
    inv = pd.read_excel(file_path, sheet_name="Inventory", parse_dates=["date"])
    cons = pd.read_excel(file_path, sheet_name="Material_Consumption", parse_dates=["production_date"])

    return po, gr, inv, cons
