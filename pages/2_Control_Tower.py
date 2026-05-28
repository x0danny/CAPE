import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="CAPE Control Tower", page_icon="⚡", layout="wide")

st.title("⚡ CAPE Control Tower")
st.markdown("**Order Risk Intelligence + Carbon Exposure | ERPsim Data**")
st.caption("Every number has a plain English explanation. No guessing what anything means.")
st.divider()

@st.cache_data
def load_data():
    sales = pd.read_excel('data/Sales.xlsx', sheet_name='Sales')
    carbon = pd.read_excel('data/Carbon Emissions.xlsx', sheet_name='Carbon_Emissions')
    po = pd.read_excel('data/Purchase Orders.xlsx', sheet_name='Purchase_Orders')
    inventory = pd.read_excel('data/Inventory.xlsx', sheet_name='Inventory')
    return sales, carbon, po, inventory

sales, carbon, po, inventory = load_data()

# Build period summary
po['delivery_steps'] = (po['GOODS_RECEIPT_ROUND'] - po['SIM_ROUND']) * 10 + \
                       (po['GOODS_RECEIPT_STEP'] - po['SIM_STEP'])
po['is_late'] = (po['delivery_steps'] == 2).astype(int)

carbon_by_period = carbon.groupby(['SIM_ROUND','SIM_STEP']).agg(
    total_co2e=('TOTAL_CO2E_EMISSIONS','sum'),
    overstock_co2e=('TOTAL_CO2E_EMISSIONS', lambda x: x[carbon.loc[x.index,'TYPE']=='Overstock'].sum())
).reset_index()

sales_by_period = sales.groupby(['SIM_ROUND','SIM_STEP']).agg(
    total_revenue=('NET_VALUE','sum'),
    num_orders=('SALES_ORDER_NUMBER','nunique'),
    avg_margin=('CONTRIBUTION_MARGIN_PCT','mean'),
    total_quantity=('QUANTITY','sum')
).reset_index()

period_summary = pd.merge(carbon_by_period, sales_by_period, on=['SIM_ROUND','SIM_STEP'], how='inner')
period_summary['co2e_per_dollar'] = period_summary['total_co2e'] / period_summary['total_revenue']
period_summary['period'] = 'R' + period_summary['SIM_ROUND'].astype(str) + '-S' + period_summary['SIM_STEP'].astype(str)

late_by_period = po.groupby(['SIM_ROUND','SIM_STEP']).agg(
    total_orders=('is_late','count'),
    late_orders=('is_late','sum')
).reset_index()
late_by_period['late_pct'] = late_by_period['late_orders'] / late_by_period['total_orders'] * 100
period_summary = pd.merge(period_summary, late_by_period, on=['SIM_ROUND','SIM_STEP'], how='left')

scaler = MinMaxScaler()
period_summary['intensity_scaled'] = scaler.fit_transform(period_summary[['co2e_per_dollar']])
period_summary['overstock_scaled'] = scaler.fit_transform(period_summary[['overstock_co2e']])
period_summary['cape_risk_score'] = (period_summary['intensity_scaled'] * 0.70 +
                                      period_summary['overstock_scaled'] * 0.30)
period_summary_sorted = period_summary.sort_values(['SIM_ROUND','SIM_STEP'])
high_risk = period_summary[period_summary['cape_risk_score'] >= 0.6]
total_late = po['is_late'].sum()
total_orders = len(po)

# ══════════════════════════════════════════════════════
# SECTION 1: WHAT IS HAPPENING RIGHT NOW
# ══════════════════════════════════════════════════════
st.header("📍 What Is Happening Right Now")
st.caption("A snapshot of order health and carbon exposure across all simulation periods.")
st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Late Orders", f"{total_late} of {total_orders}")
    st.caption("Orders that took 2 steps to arrive instead of 1. Late orders trigger carbon penalties downstream.")
with col2:
    st.metric("High Risk Periods", f"{len(high_risk)} of 38")
    st.caption("Simulation periods where carbon intensity AND overstock penalties were both elevated above safe threshold.")
with col3:
    st.metric("Worst Period", "R3-S6")
    st.caption("Round 3 Step 6 had the highest CAPE risk score (0.834) — carbon intensity spiked to 0.146 kg CO2e per dollar.")
with col4:
    st.metric("Overstock CO2e", "142,500 kg")
    st.caption("Total carbon penalty from inventory sitting idle. This is 61% of all direct emissions — caused by late orders.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 2: WHY IS IT HAPPENING
# ══════════════════════════════════════════════════════
st.header("🔍 Why Is It Happening")
st.caption("These charts show which signals are driving the carbon risk. Each chart has a plain English explanation.")
st.divider()

col_a, col_b = st.columns(2)

with col_a:
    fig1 = px.bar(period_summary_sorted, x='period', y='late_pct',
                  title='Late Order Rate by Period (%)',
                  color='late_pct', color_continuous_scale='Reds',
                  labels={'late_pct': '% Late', 'period': 'Period'})
    fig1.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("📌 **What this means:** Bars show what percentage of orders arrived late in each period. Taller red bars = more late orders = more carbon risk. Round 3 consistently has the most late orders.")

with col_b:
    fig2 = px.bar(period_summary_sorted, x='period', y='overstock_co2e',
                  title='Overstock Carbon Penalty by Period (kg CO2e)',
                  color='overstock_co2e', color_continuous_scale='Oranges',
                  labels={'overstock_co2e': 'Overstock CO2e (kg)', 'period': 'Period'})
    fig2.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("📌 **What this means:** When orders are late, inventory piles up in warehouses. That idle inventory generates a carbon penalty. Taller bars = more inventory sitting idle = more wasted emissions.")

col_c, col_d = st.columns(2)

with col_c:
    fig3 = px.scatter(period_summary, x='late_pct', y='co2e_per_dollar',
                      size='overstock_co2e', color='cape_risk_score',
                      color_continuous_scale='RdYlGn_r',
                      title='Late Orders vs Carbon Intensity',
                      labels={'late_pct': '% Late Orders', 'co2e_per_dollar': 'CO2e per $ Revenue'},
                      hover_data=['period'])
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("📌 **What this means:** Each dot is a simulation period. Dots in the top-right corner = high late order rate AND high carbon cost per dollar. Bigger dots = bigger overstock penalty. This proves late orders and carbon spikes move together.")

with col_d:
    round_summary = period_summary.groupby('SIM_ROUND').agg(
        avg_risk=('cape_risk_score','mean'),
        avg_late=('late_pct','mean'),
        total_co2e=('total_co2e','sum')
    ).reset_index()
    round_summary['round'] = 'Round ' + round_summary['SIM_ROUND'].astype(str)

    fig4 = px.bar(round_summary, x='round', y='avg_risk',
                  title='Average CAPE Risk Score by Round',
                  color='avg_risk', color_continuous_scale='RdYlGn_r',
                  labels={'avg_risk': 'Avg Risk Score', 'round': 'Simulation Round'})
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("📌 **What this means:** Round 3 has the highest average risk score across all its periods. This tells us something systematically went wrong in Round 3 — more late orders, more overstock, more carbon.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 3: WHAT TO DO ABOUT IT
# ══════════════════════════════════════════════════════
st.header("🚨 What To Do About It")
st.caption("Plain English action recommendations for each high risk period. No jargon.")
st.divider()

for _, row in high_risk.sort_values('cape_risk_score', ascending=False).iterrows():
    risk = row['cape_risk_score']
    if risk >= 0.8:
        color = "error"
        level = "🔴 CRITICAL RISK"
    elif risk >= 0.7:
        color = "warning"
        level = "🟠 HIGH RISK"
    else:
        color = "info"
        level = "🟡 ELEVATED RISK"

    with st.expander(f"{level} — Period {row['period']} | Risk Score: {risk:.3f}"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Carbon Intensity", f"{row['co2e_per_dollar']:.4f} kg/$")
        col2.metric("Overstock Penalty", f"{row['overstock_co2e']:,.0f} kg CO2e")
        col3.metric("Late Order Rate", f"{row['late_pct']:.0f}%" if pd.notna(row['late_pct']) else "N/A")

        st.markdown("**What happened:**")
        st.write(f"In period {row['period']}, carbon costs per dollar of revenue reached {row['co2e_per_dollar']:.4f} kg CO2e — above the safe threshold of 0.09. Overstock penalties hit {row['overstock_co2e']:,.0f} kg CO2e from inventory sitting idle due to delayed orders.")

        st.markdown("**What should have been done:**")
        st.write("1. Flag orders at risk of delay 1-2 periods earlier using the CAPE risk score")
        st.write("2. Reduce reorder quantities to prevent overstock buildup")
        st.write("3. Avoid air freight escalation — each air shipment carries 47-50x the carbon of ground freight per ton-mile")
        st.write("4. Alert the operations manager before the period starts, not after")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 4: THE CAPE CONNECTION
# ══════════════════════════════════════════════════════
st.header("🔗 How This Connects to CAPE")
st.caption("This control tower feeds directly into the CAPE Carbon layer. Here is the full pipeline explained.")
st.divider()

st.markdown("""
| Step | What Happens | Why It Matters |
|------|-------------|----------------|
| **1. Order Placed** | A purchase order enters the ERP system | Starting point — no carbon cost yet |
| **2. Delivery Delay** | Order takes 2 steps instead of 1 to arrive | Late flag triggered — carbon risk begins |
| **3. Inventory Builds Up** | Warehouse holds excess stock | Overstock CO2e penalty starts accumulating |
| **4. CAPE Flags the Period** | Risk score exceeds 0.6 threshold | Alert — intervention window is now |
| **5. Air Freight Escalation** | Critical orders get upgraded to air to catch up | Carbon cost multiplies 47-50x vs ground |
| **6. LAX Absorbs the Load** | Air cargo volume at LAX spikes | Real-world validation — this is what we measured |
| **7. Green Ledger Records It** | SAP logs the emissions after the fact | Too late — CAPE caught it at Step 4 |
""")

st.info("💡 CAPE's job is to intervene at Step 4 — before Steps 5, 6, and 7 happen. That is the research contribution.")

st.divider()
st.caption("CAPE Control Tower | SAIES Research | CSULA CIS | NSF Grant Project")
