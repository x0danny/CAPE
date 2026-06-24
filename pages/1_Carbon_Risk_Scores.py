import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
from data_loader import load_erpsim, build_period_map, add_period_labels, ROUND_NAMES

EUR_TO_USD = 1.08

st.title("🌿 Carbon Emissions Risk Scores")
st.markdown("##### Which time periods had the highest carbon risk — and why?")
st.caption(
    "Our research started by analyzing ERPsim data — ERPsim is a business simulation platform developed in Germany "
    "where teams manage a virtual supply chain (purchasing, inventory, sales, and logistics) in real time. "
    "This page scores each of 38 simulation periods for carbon risk. "
    f"The original data was recorded in EUR; we show USD equivalents at €1 = ${EUR_TO_USD:.2f}."
)
st.info(
    "📌 **How to read the timeline:** The x-axis shows 38 time points from a supply chain training exercise. "
    "They are grouped into 4 phases: Phase 1 (Early) → Phase 2 (Growth) → Phase 3 (Peak Risk) → Phase 4 (Late). "
    "CAPE uses these to learn what happens to carbon emissions as conditions change — then checks the pattern against real LAX data on the LAX Case Study tab."
)
st.divider()

sales, carbon, _po, inventory, financial = load_erpsim()
_period_map = build_period_map(sales)

# Build CAPE summary
cape_join = pd.merge(sales, carbon, on=['SIM_ROUND', 'SIM_STEP'], how='inner')
cape_summary = cape_join.groupby(['SIM_ROUND', 'SIM_STEP']).agg(
    total_revenue=('NET_VALUE', 'sum'),
    total_co2e=('TOTAL_CO2E_EMISSIONS', 'sum'),
    num_orders=('SALES_ORDER_NUMBER', 'nunique')
).reset_index()
cape_summary['co2e_per_eur'] = cape_summary['total_co2e'] / cape_summary['total_revenue']
cape_summary['co2e_per_dollar'] = cape_summary['total_co2e'] / (cape_summary['total_revenue'] * EUR_TO_USD)
cape_summary = add_period_labels(cape_summary, _period_map)

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

total_co2e = carbon['TOTAL_CO2E_EMISSIONS'].sum()
overstock_co2e = carbon[carbon['TYPE']=='Overstock']['TOTAL_CO2E_EMISSIONS'].sum()
overstock_pct = overstock_co2e / total_co2e * 100
high_risk_count = len(cape_summary[cape_summary['cape_risk_score'] >= 0.6])
worst_period = cape_summary.loc[cape_summary['cape_risk_score'].idxmax(), 'period']

col1, col2, col3 = st.columns(3)
col1.metric("Total Carbon Emissions", f"{total_co2e:,.0f} kg CO₂e",
            help="CO₂e = carbon dioxide equivalent. This is the total greenhouse gas output across all simulation periods.")
col2.metric("Overstock Carbon Waste", f"{overstock_co2e:,.0f} kg CO₂e",
            help=f"Carbon wasted on inventory sitting idle in warehouses — {overstock_pct:.0f}% of all direct (Scope 1) emissions.")
col3.metric("High Risk Periods", f"{high_risk_count} of {len(cape_summary)}",
            help="Periods where the CAPE risk score exceeded 0.6 — meaning both carbon intensity and overstock were dangerously high.")

col4, col5 = st.columns(2)
col4.metric("Worst Period", worst_period,
            help="The simulation period with the highest carbon emissions risk score — carbon emissions were at their peak here.")
col5.metric("Overstock Share of Direct Emissions", f"{overstock_pct:.1f}%",
            help="Scope 1 = direct emissions from operations. This shows how much came from idle inventory vs. shipping.")

st.divider()

st.markdown("""
Understanding carbon risk starts with measuring it. The charts below show how carbon emissions
changed across 38 simulation periods in the ERPsim training exercise. Each period represents a
different set of supply chain conditions — from calm early periods to high-stress peak periods.
By tracking how carbon intensity and risk scores shift over time, CAPE identifies the conditions
that lead to the highest emissions.
""")

# Risk Score chart (full width)
st.markdown("**Figure 1: Carbon Emissions Risk Score by Period**")
fig1 = px.bar(cape_summary_sorted, x='period', y='cape_risk_score',
              color='cape_risk_score', color_continuous_scale='RdYlGn_r')
fig1.add_hline(y=0.6, line_dash='dash', line_color='red', annotation_text='High Risk Threshold')
fig1.update_layout(xaxis_tickangle=45)
st.plotly_chart(fig1, use_container_width=True)
st.caption(f"Periods above the red dashed line (0.6) are high-risk. **{high_risk_count} of {len(cape_summary)}** periods exceeded this threshold.")

col_key1, col_key2, col_key3 = st.columns(3)
with col_key1:
    st.success("🟢 **0.0 – 0.3: Low Risk**\n\nEmissions are under control. No immediate action needed.")
with col_key2:
    st.warning("🟡 **0.3 – 0.6: Moderate Risk**\n\nEmissions are elevated. Monitor closely and consider adjustments.")
with col_key3:
    st.error("🔴 **0.6 – 1.0: High Risk**\n\nEmissions are critically high. Immediate attention needed to reduce carbon exposure.")

st.divider()

# Charts row 2
col_c, col_d = st.columns(2)

with col_c:
    scope_totals = carbon.groupby('SCOPE')['TOTAL_CO2E_EMISSIONS'].sum().reset_index()
    scope_totals['SCOPE'] = 'Scope ' + scope_totals['SCOPE'].astype(str)
    st.markdown("**Figure 2: CO₂e by Emission Scope**")
    fig3 = px.pie(scope_totals, values='TOTAL_CO2E_EMISSIONS', names='SCOPE',
                  color_discrete_sequence=['#1f77b4', '#9467bd', '#2ca02c'])
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "**Scope 1** — Direct emissions from airplanes and operations the company controls "
        "(goods movement, deliveries, internal transfers, overstock storage).\n\n"
        "**Scope 2** — Indirect emissions from purchased energy, such as electricity for facilities "
        "(e.g., passenger electric charging, Wi-Fi, displays at LAX — even solar energy has production costs).\n\n"
        "**Scope 3** — Upstream and supply chain emissions the company doesn't directly control "
        "(ground maintenance, truck shipping after the airplane lands, CO₂ embedded in purchased products)."
    )

with col_d:
    type_totals = carbon.groupby('TYPE')['TOTAL_CO2E_EMISSIONS'].sum().reset_index()
    type_color_map = {'Goods Movement': '#E24B4A', 'Overstock': '#9467bd', 'Purchased Energy': '#2ca02c', 'Goods Receipt': '#1f77b4'}
    st.markdown("**Figure 3: CO₂e by Emission Type**")
    fig4 = px.bar(type_totals, x='TYPE', y='TOTAL_CO2E_EMISSIONS',
                  color='TYPE', color_discrete_map=type_color_map,
                  labels={'TOTAL_CO2E_EMISSIONS': 'Total CO2e (kg)'})
    fig4.update_layout(showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)
    top_type = type_totals.loc[type_totals['TOTAL_CO2E_EMISSIONS'].idxmax(), 'TYPE']
    st.caption(f"**{top_type}** is the largest source of carbon emissions by type.")

# Revenue vs Carbon — Scatter plot
import numpy as np
from scipy import stats

cape_summary_sorted['total_revenue_usd'] = cape_summary_sorted['total_revenue'] * EUR_TO_USD
cape_summary_sorted['phase'] = cape_summary_sorted['SIM_ROUND'].map(ROUND_NAMES)

slope, intercept, r_value, p_value, std_err = stats.linregress(
    cape_summary_sorted['total_revenue_usd'], cape_summary_sorted['total_co2e']
)

st.markdown(f"**Figure 4: Revenue vs Carbon Emissions (r = {r_value:.3f}, p = {p_value:.4f})**")
fig5 = px.scatter(
    cape_summary_sorted,
    x='total_revenue_usd',
    y='total_co2e',
    color='phase',
    hover_data={'period': True, 'total_revenue_usd': ':.0f', 'total_co2e': ':.0f', 'phase': True},
    labels={'total_revenue_usd': 'Revenue (USD)', 'total_co2e': 'Total CO₂e (kg)', 'phase': 'Phase'},
    color_discrete_sequence=['#2ca02c', '#1f77b4', '#E24B4A', '#9467bd'],
)
x_range = np.linspace(cape_summary_sorted['total_revenue_usd'].min(), cape_summary_sorted['total_revenue_usd'].max(), 100)
fig5.add_trace(go.Scatter(
    x=x_range, y=slope * x_range + intercept,
    mode='lines', name='Trend',
    line=dict(color='gray', dash='dash', width=2), showlegend=False
))
fig5.update_traces(marker=dict(size=10), selector=dict(mode='markers'))
fig5.update_layout(legend=dict(x=0.01, y=0.99))
st.plotly_chart(fig5, use_container_width=True)
st.caption(
    f"Each dot is one simulation period. Dots trending upward mean higher-revenue periods also had higher "
    f"carbon emissions (r = {r_value:.3f}, p = {p_value:.4f}). Both variables are driven by production volume, "
    f"so this correlation reflects shared supply chain conditions rather than a direct causal link. "
    f"Revenue converted from EUR at €1 = ${EUR_TO_USD:.2f}."
)

# High risk table
st.subheader("🚨 High Risk Periods")
high_risk = cape_summary[cape_summary['cape_risk_score'] >= 0.6][
    ['period', 'total_revenue', 'total_co2e', 'overstock_co2e', 'co2e_per_dollar', 'cape_risk_score']
].sort_values('cape_risk_score', ascending=False)
high_risk.columns = ['Period', 'Revenue (USD)', 'Total CO2e', 'Overstock CO2e', 'CO2e per $', 'Risk Score']
high_risk['Revenue (USD)'] = high_risk['Revenue (USD)'].apply(lambda x: f"${x * EUR_TO_USD:,.0f}")
high_risk['Total CO2e'] = high_risk['Total CO2e'].apply(lambda x: f"{x:,.0f}")
high_risk['Overstock CO2e'] = high_risk['Overstock CO2e'].apply(lambda x: f"{x:,.0f}")
high_risk['CO2e per $'] = high_risk['CO2e per $'].apply(lambda x: f"{x:.4f}")
high_risk['Risk Score'] = high_risk['Risk Score'].apply(lambda x: f"{x:.3f}")
st.dataframe(high_risk.reset_index(drop=True), use_container_width=True, hide_index=True)
st.caption(f"Revenue and carbon emissions are not strongly correlated (r = {r_value:.3f}), "
           "suggesting that high revenue periods do not necessarily produce the highest carbon emissions.")

st.divider()
st.subheader("🤖 CAPE Order Risk Model for LAX Data")

col_r1, col_r2, col_r3 = st.columns(3)
col_r1.metric("Model Type", "Random Forest",
              help="A machine learning algorithm that builds many decision trees and averages their predictions.")
col_r2.metric("Model Accuracy (CV)", "94.2% ±3.3%",
              help="CV = cross-validation. The model correctly predicts order risk 94.2% of the time, tested using 5-fold cross-validation (CV) on simulation data.")
col_r3.metric("Top Predictor", "CO₂ Emissions",
              help="Carbon emissions are the single most important signal for predicting whether an order will be late.")

st.success(
    "🔑 **Key Finding:** Carbon emissions are the strongest predictor of order lateness — "
    "when supply chain conditions produce high carbon, they also produce late deliveries. "
    "The two risks move together, which means monitoring carbon can serve as an early warning "
    "for supply chain problems. Model accuracy: 94.2% across 5 folds."
)

st.divider()
st.info("📍 **Why CAPE matters to LAX:** CAPE's highest-risk time points (24–28, during Phase 3) show the same pattern as 2020–2021 at LAX — supply chain stress forces a switch to high-carbon air freight. CAPE catches this at the order level, before the freight mode decision is made.")
st.caption("CAPE — Carbon-Aware Predictive Engine | AI-Driven Analytics Platform | SAIES Research | Cal State LA · CIS | NSF Grant Project")
