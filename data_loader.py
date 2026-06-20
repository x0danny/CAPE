import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


@st.cache_data
def load_erpsim():
    sales = pd.read_excel(DATA_DIR / "Sales.xlsx", sheet_name="Sales")
    carbon = pd.read_excel(DATA_DIR / "Carbon Emissions.xlsx", sheet_name="Carbon_Emissions")
    po = pd.read_excel(DATA_DIR / "Purchase Orders.xlsx", sheet_name="Purchase_Orders")
    inventory = pd.read_excel(DATA_DIR / "Inventory.xlsx", sheet_name="Inventory")
    financial = pd.read_excel(DATA_DIR / "Fianancial Postings.xlsx", sheet_name="Financial_Postings")
    return sales, carbon, po, inventory, financial


def period_label(sim_round, sim_step, all_periods):
    """Convert R-S notation to 'Week N' for non-technical display."""
    key = (sim_round, sim_step)
    if key in all_periods:
        return f"Week {all_periods[key]}"
    return f"R{sim_round}-S{sim_step}"


def build_period_map(sales_df):
    """Build a mapping from (SIM_ROUND, SIM_STEP) → sequential period number."""
    periods = sorted(set(zip(sales_df['SIM_ROUND'], sales_df['SIM_STEP'])))
    return {key: i + 1 for i, key in enumerate(periods)}


def add_period_labels(df, period_map):
    """Add a 'period' column with readable 'Period N' labels."""
    df = df.copy()
    df['period'] = [period_label(r, s, period_map)
                    for r, s in zip(df['SIM_ROUND'], df['SIM_STEP'])]
    return df


ROUND_NAMES = {1: "Phase 1 (Startup)", 2: "Phase 2 (Growth)",
               3: "Phase 3 (Stress)", 4: "Phase 4 (Recovery)"}


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
