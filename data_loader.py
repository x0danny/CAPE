import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load_erpsim():
    sales = pd.read_excel(DATA_DIR / "Sales.xlsx", sheet_name="Sales")
    carbon = pd.read_excel(DATA_DIR / "Carbon Emissions.xlsx", sheet_name="Carbon_Emissions")
    po = pd.read_excel(DATA_DIR / "Purchase Orders.xlsx", sheet_name="Purchase_Orders")
    inventory = pd.read_excel(DATA_DIR / "Inventory.xlsx", sheet_name="Inventory")
    financial = pd.read_excel(DATA_DIR / "Fianancial Postings.xlsx", sheet_name="Financial_Postings")
    return sales, carbon, po, inventory, financial


@st.cache_data
def load_lax_aggregate():
    lax = pd.read_csv(DATA_DIR / "lax_cargo.csv")
    lax['AirCargoTons'] = lax['AirCargoTons'].str.replace(',', '').astype(float)
    lax['date'] = pd.to_datetime(lax['ReportPeriod'], format='%b %Y')
    lax['year'] = lax['date'].dt.year
    lax['month'] = lax['date'].dt.month
    return lax


@st.cache_data
def load_lax_shipments():
    sales = pd.read_excel(DATA_DIR / "LAX_Sales.xlsx")
    carbon = pd.read_excel(DATA_DIR / "LAX_Carbon_Emissions.xlsx", sheet_name="Carbon_Emissions")
    return sales, carbon
