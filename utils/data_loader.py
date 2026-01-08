import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    file_path = "data/FMCG_Purchasing_Data.xlsx"
    
    po = pd.read_excel(file_path, sheet_name="Purchase_Order")
    gr = pd.read_excel(file_path, sheet_name="Goods_Receipt")
    inv = pd.read_excel(file_path, sheet_name="Inventory")
    cons = pd.read_excel(file_path, sheet_name="Material_Consumption")
    sup = pd.read_excel(file_path, sheet_name="Supplier_Performance")

    return po, gr, inv, cons, sup
