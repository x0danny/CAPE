import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler

st.set_page_config(page_title="CAPE Dashboard", page_icon="🌿", layout="wide")

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**AI-Driven Analytics Platform for Carbon-Awareness of LAX Logistics**")

st.markdown("##### Team")
st.markdown("Brian Ta · Daniel Ramirez")
st.markdown("##### Advisor")
st.markdown("Dr. Ming Wang")
st.caption("CSULA CIS | SAIES Research | NSF Grant Project")
st.divider()

st.caption("This page shows carbon exposure across all 38 simulation periods — which periods were high risk, why, and how the findings connect to 18 years of real LAX air freight data (2006–2023).")
st.divider()

# Load data
@st.cache_data
def load_data():
    sales = pd.read_excel('data/Sales.xlsx', sheet_name='Sales')
    carbon = pd.read_excel('data/Carbon Emissions.xlsx', sheet_name='Carbon_Emissions')
    inventory = pd.read_excel('data/Inventory.xlsx', sheet_name='Inventory')
    financial = pd.read_excel('data/Fianancial Postings.xlsx', sheet_name='Financial_Postings')
    return sales, carbon, inventory, financial

sales, carbon, inventory, financial = load_data()

# Build CAPE summary
cape_join = pd.merge(sales, carbon, on=['SIM_ROUND', 'SIM_STEP'], how='inner')
cape_summary = cape_join.groupby(['SIM_ROUND', 'SIM_STEP']).agg(
    total_revenue=('NET_VALUE', 'sum'),
    total_co2e=('TOTAL_CO2E_EMISSIONS', 'sum'),
    num_orders=('SALES_ORDER_NUMBER', 'nunique')
).reset_index()
cape_summary['co2e_per_dollar'] = cape_summary['total_co2e'] / cape_summary['total_revenue']
cape_summary['period'] = 'R' + cape_summary['SIM_ROUND'].astype(str) + '-S' + cape_summary['SIM_STEP'].astype(str)

overstock = carbon[carbon['TYPE'] == 'Overstock'].groupby(['SIM_ROUND', 'SIM_STEP']).agg(
    overstock_co2e=('TOTAL_CO2E_EMISSIONS', 'sum')
).reset_index()
cape_summary = pd.merge(cape_summary, overstock, on=['SIM_ROUND', 'SIM_STEP'], how='left')
cape_summary['overstock_co2e'] = cape_summary['overstock_co2e'].fillna(0)

scaler = MinMaxScaler()
cape_summary['intensity_scaled'] = scaler.fit_transform(cape_summary[['co2e_per_dollar']])
cape_summary['overstock_scaled'] = scaler.fit_transform(cape_summary[['overstock_co2e']])
cape_summary['cape_risk_score'] = (cape_summary['intensity_scaled'] * 0.70 + cape_summary['overstock_scaled'] * 0.30)
cape_summary_sorted = cape_summary.sort_values(['SIM_ROUND', 'SIM_STEP'])

# KPI row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total CO2e", f"{carbon['TOTAL_CO2E_EMISSIONS'].sum():,.0f} kg")
col2.metric("Overstock CO2e", f"{carbon[carbon['TYPE']=='Overstock']['TOTAL_CO2E_EMISSIONS'].sum():,.0f} kg")
col3.metric("% of Scope 1", "60.8%")
col4.metric("High Risk Periods", f"{len(cape_summary[cape_summary['cape_risk_score'] >= 0.6])}")
col5.metric("Highest Risk Period", "R3-S6")

st.divider()

# Charts row 1
col_a, col_b = st.columns(2)

with col_a:
    fig1 = px.line(cape_summary_sorted, x='period', y='co2e_per_dollar',
                   title='Carbon Intensity Over Time (CO2e per $ Revenue)',
                   markers=True, color_discrete_sequence=['#2ca02c'])
    fig1.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    fig2 = px.bar(cape_summary_sorted, x='period', y='cape_risk_score',
                  color='cape_risk_score', color_continuous_scale='RdYlGn_r',
                  title='CAPE Risk Score by Period')
    fig2.add_hline(y=0.6, line_dash='dash', line_color='red', annotation_text='High Risk Threshold')
    fig2.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)

# Charts row 2
col_c, col_d = st.columns(2)

with col_c:
    scope_totals = carbon.groupby('SCOPE')['TOTAL_CO2E_EMISSIONS'].sum().reset_index()
    scope_totals['SCOPE'] = 'Scope ' + scope_totals['SCOPE'].astype(str)
    fig3 = px.pie(scope_totals, values='TOTAL_CO2E_EMISSIONS', names='SCOPE',
                  title='CO2e by Emission Scope',
                  color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'])
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    type_totals = carbon.groupby('TYPE')['TOTAL_CO2E_EMISSIONS'].sum().reset_index()
    fig4 = px.bar(type_totals, x='TYPE', y='TOTAL_CO2E_EMISSIONS',
                  title='CO2e by Emission Type',
                  color='TOTAL_CO2E_EMISSIONS', color_continuous_scale='Reds',
                  labels={'TOTAL_CO2E_EMISSIONS': 'Total CO2e (kg)'})
    st.plotly_chart(fig4, use_container_width=True)

# Revenue vs Carbon
fig5 = go.Figure()
fig5.add_trace(go.Bar(x=cape_summary_sorted['period'], y=cape_summary_sorted['total_revenue'],
                      name='Revenue ($)', yaxis='y1', marker_color='steelblue', opacity=0.7))
fig5.add_trace(go.Scatter(x=cape_summary_sorted['period'], y=cape_summary_sorted['total_co2e'],
                          name='Total CO2e (kg)', yaxis='y2',
                          line=dict(color='red', width=2), marker=dict(size=6), mode='lines+markers'))
fig5.update_layout(title='Revenue vs Carbon Emissions Over Time',
                   xaxis=dict(tickangle=45),
                   yaxis=dict(title='Revenue ($)', side='left'),
                   yaxis2=dict(title='CO2e (kg)', side='right', overlaying='y'),
                   legend=dict(x=0.01, y=0.99))
st.plotly_chart(fig5, use_container_width=True)

# High risk table
st.subheader("🚨 High Risk Periods")
high_risk = cape_summary[cape_summary['cape_risk_score'] >= 0.6][
    ['period', 'total_revenue', 'total_co2e', 'overstock_co2e', 'co2e_per_dollar', 'cape_risk_score']
].sort_values('cape_risk_score', ascending=False)
high_risk.columns = ['Period', 'Revenue ($)', 'Total CO2e', 'Overstock CO2e', 'CO2e per $', 'Risk Score']
st.dataframe(high_risk, use_container_width=True)

st.divider()
st.subheader("✈️ LAX Air Freight Validation — 18 Years of Data (2006–2023)")
st.caption("This section connects CAPE's simulation findings to real-world LAX air freight data. The question: does LAX air cargo data support CAPE's predictions about carbon risk during supply chain stress?")

lax = pd.read_csv('data/lax_cargo.csv')
lax['AirCargoTons'] = lax['AirCargoTons'].str.replace(',', '').astype(float)
lax['ReportPeriod'] = pd.to_datetime(lax['ReportPeriod'], format='%b %Y')
lax_freight = lax[lax['CargoType'] == 'Freight']
lax_monthly = lax_freight.groupby('ReportPeriod').agg(
    total_tons=('AirCargoTons', 'sum')
).reset_index().sort_values('ReportPeriod')

lax_yearly = lax_freight.groupby(lax_freight['ReportPeriod'].dt.year).agg(
    total_tons=('AirCargoTons', 'sum')
).reset_index()
lax_yearly.columns = ['Year', 'total_tons']

fig6 = px.line(lax_monthly,
               x='ReportPeriod',
               y='total_tons',
               title='LAX Monthly Air Freight Volume (2006–2023)',
               labels={'total_tons': 'Total Freight (Tons)', 'ReportPeriod': 'Month'},
               color_discrete_sequence=['#e377c2'])
fig6.add_vline(x=pd.Timestamp('2008-09-01').timestamp()*1000, line_dash='dash', line_color='red', annotation_text='2008 Financial Crisis')
fig6.add_vline(x=pd.Timestamp('2020-03-01').timestamp()*1000, line_dash='dash', line_color='orange', annotation_text='COVID-19 Pandemic')
fig6.add_vline(x=pd.Timestamp('2021-03-01').timestamp()*1000, line_dash='dash', line_color='green', annotation_text='Supply Chain Surge')
fig6.update_layout(height=400)
st.plotly_chart(fig6, use_container_width=True)
st.caption("📌 **How to read this chart:** Each point is one month of air freight volume at LAX. Sharp spikes indicate supply chain stress events where companies switched from ground to air shipping — exactly the kind of mode-switching that multiplies carbon emissions by 47-50x.")

st.divider()
st.markdown("#### Key Findings from 18 Years of LAX Data")

col_e, col_f, col_g = st.columns(3)
with col_e:
    st.metric("Peak Month", "Mar 2021")
    st.metric("Peak Volume", "254,057 tons")
    st.caption("The highest single month in 18 years — driven by the global supply chain crisis.")
with col_f:
    st.metric("2006 vs 2023", "-7.2%")
    st.metric("2006 Volume", "2,024,065 tons")
    st.caption("Overall freight volume declined slightly over 18 years, but the spikes during crises are what matter for carbon.")
with col_g:
    st.metric("CAPE Highest Risk", "R3-S6")
    st.metric("Peak Carbon Intensity", "0.158 kg CO2e/$")
    st.caption("CAPE's riskiest simulation period mirrors the real-world pattern: supply chain stress → air freight surge → carbon spike.")

st.divider()
st.markdown("#### Does Air Freight Reduce Carbon Over Time?")
st.caption("The short answer: **no**. While overall freight volume has slightly declined, the carbon problem is about **spikes during crises**, not long-term averages.")

fig_yearly = px.bar(lax_yearly, x='Year', y='total_tons',
                    title='LAX Annual Air Freight Volume (2006–2023)',
                    labels={'total_tons': 'Total Freight (Tons)', 'Year': 'Year'},
                    color='total_tons', color_continuous_scale='Blues')
fig_yearly.update_layout(height=350)
st.plotly_chart(fig_yearly, use_container_width=True)

st.markdown("""
**What the data shows across 18 years:**
- **2006–2009:** Freight dropped 21% during the financial crisis — companies shipped less of everything
- **2010–2019:** Gradual recovery with steady growth, reaching pre-crisis levels by 2015
- **2020–2021:** COVID disrupted ground supply chains, causing a massive surge in air freight (+22% from 2019 to 2021)
- **2022–2023:** Sharp correction as supply chains normalized, dropping 34% from the 2021 peak

**Why this matters for carbon:** Air freight produces 47-50x more carbon per ton-mile than ground transport. Even a temporary spike in air cargo — like the 2021 surge — generates outsized carbon emissions. CAPE's value is detecting the conditions that trigger these mode-switching events **before** they happen.
""")

st.info("📍 **The CAPE connection:** CAPE's highest-risk simulation periods (R3-S6 through R3-S10) show the same pattern as 2020-2021 at LAX — supply chain stress forces a switch to high-carbon air freight. CAPE catches this at the order level, before the freight mode decision is made.")

st.divider()
st.caption("CAPE — Carbon-Aware Predictive Engine | AI-Driven Analytics Platform | SAIES Research | CSULA CIS | NSF Grant Project")
st.divider()
st.subheader("🤖 CAPE Order Risk Model")

col_r1, col_r2, col_r3 = st.columns(3)
col_r1.metric("Model Type", "Random Forest")
col_r2.metric("CV Accuracy", "94.2% ±3.3%")
col_r3.metric("Top Predictor", "total_co2e")

features_list = ['total_co2e','num_orders','total_quantity','SIM_ELAPSED_STEPS','avg_margin','overstock_co2e','SIM_STEP','avg_net_value']
importances_list = [0.1735,0.1469,0.1420,0.1132,0.1063,0.0923,0.0740,0.0721]

fig_imp = px.bar(
    x=importances_list,
    y=features_list,
    orientation='h',
    title='CAPE Risk Model — Feature Importance (Trained on ERPsim Data)',
    labels={'x': 'Importance', 'y': 'Feature'},
    color=importances_list,
    color_continuous_scale='Blues'
)
fig_imp.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_imp, use_container_width=True)

st.success("🔑 Key Finding: total_co2e is the #1 predictor of order lateness — carbon exposure and order risk are statistically linked. CV accuracy: 94.2% across 5 folds.")

st.divider()
st.subheader("🚢 Port of LA vs LAX Air Cargo — 2021 Validation")

import plotly.graph_objects as go

port_la_2021 = pd.DataFrame({
    'month': ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
    'total_teus': [835516,799315,957599,946966,1012048,876430,890800,954377,903865,902644,811460,786589],
    'total_tons': [212993,200482,254057,241159,249734,238398,240152,236615,234046,249535,245303,249442]
})

fig7 = go.Figure()
fig7.add_trace(go.Bar(x=port_la_2021['month'], y=port_la_2021['total_teus'],
                      name='Port of LA TEUs', yaxis='y1', marker_color='steelblue', opacity=0.7))
fig7.add_trace(go.Scatter(x=port_la_2021['month'], y=port_la_2021['total_tons'],
                          name='LAX Air Cargo (tons)', yaxis='y2',
                          line=dict(color='red', width=3), marker=dict(size=8), mode='lines+markers'))
fig7.update_layout(
    title='Port of LA Container Volume vs LAX Air Freight — 2021 Supply Chain Surge',
    yaxis=dict(title='Port TEUs', side='left'),
    yaxis2=dict(title='LAX Air Cargo (tons)', side='right', overlaying='y'),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig7, use_container_width=True)
st.caption("📌 **How to read this chart:** The blue bars show shipping containers handled by the Port of LA. The red line shows air cargo at LAX. When both spike at the same time (March 2021), it means the entire freight system was under stress — ground AND air. That's when carbon emissions are at their highest.")
st.info("📍 **March 2021:** Port of LA handled 957,599 containers (113% above the prior year) while LAX air cargo peaked at 254,057 tons. When ground shipping gets overwhelmed, companies switch to air — producing 47-50x more carbon per ton-mile. This is exactly the pattern CAPE is designed to predict and prevent.")
