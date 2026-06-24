import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_erpsim, load_lax_aggregate, build_period_map, add_period_labels

st.title("✈️ LAX Case Study")
st.markdown("##### How do CAPE's simulation findings compare to 18 years of real LAX air freight data?")
st.caption(
    "This page connects CAPE's ERPsim-based carbon risk predictions to real-world LAX air freight data "
    "published by LAWA (Los Angeles World Airports). LAX — Los Angeles International Airport — is one of "
    "the busiest cargo airports in the United States and a critical hub for the Los Angeles community and economy. "
    "Understanding carbon emissions at LAX matters because air freight produces roughly 49 times more carbon "
    "per ton-mile than ground transport."
)
st.divider()

lax = load_lax_aggregate()
lax['ReportPeriod'] = lax['date']
lax_freight = lax[lax['CargoType'] == 'Freight']
lax_monthly = lax_freight.groupby('ReportPeriod').agg(
    total_tons=('AirCargoTons', 'sum')
).reset_index().sort_values('ReportPeriod')

lax_yearly = lax_freight.groupby(lax_freight['ReportPeriod'].dt.year).agg(
    total_tons=('AirCargoTons', 'sum')
).reset_index()
lax_yearly.columns = ['Year', 'total_tons']

# ── Monthly freight volume ───────────────────────────────────────────────────
st.subheader("Figure 1: LAX Monthly Air Freight Volume (2006–2023)")

fig1 = px.line(lax_monthly,
               x='ReportPeriod',
               y='total_tons',
               labels={'total_tons': 'Total Freight (Tons)', 'ReportPeriod': 'Month'},
               color_discrete_sequence=['#e377c2'])
fig1.add_vline(x=pd.Timestamp('2008-09-01').timestamp()*1000, line_dash='dash', line_color='red',
               annotation_text='2008 Financial Crisis')
fig1.add_vline(x=pd.Timestamp('2020-03-01').timestamp()*1000, line_dash='dash', line_color='orange',
               annotation_text='COVID-19 Pandemic')
fig1.add_vline(x=pd.Timestamp('2021-03-01').timestamp()*1000, line_dash='dash', line_color='green',
               annotation_text='Supply Chain Surge')
fig1.update_layout(height=400)
st.plotly_chart(fig1, use_container_width=True)
st.caption(
    "Each point is one month of air freight volume at LAX. The **2008 financial crisis** caused a sharp drop "
    "as global trade slowed. Volumes gradually recovered through the 2010s. The **COVID-19 pandemic** (March 2020) "
    "initially disrupted all shipping, but then ground supply chains became severely backed up — forcing companies "
    "to shift cargo to air freight. This caused the **March 2021 surge** to 254,057 tons, the highest single month "
    "in 18 years. After 2021, volumes dropped sharply as supply chains normalized."
)

st.divider()

# ── Key metrics ──────────────────────────────────────────────────────────────
st.markdown("#### Key Findings from 18 Years of LAX Data")

col_e, col_f = st.columns(2)
with col_e:
    st.metric("Peak Month of Carbon Emissions", "Mar 2021")
    st.metric("Peak Volume (March 2021)", "254,057 tons")
    st.caption("The highest single month in 18 years — driven by the global supply chain crisis.")
with col_f:
    total_18yr_tons = lax_yearly['total_tons'].sum()
    max_yearly = lax_yearly['total_tons'].max()
    min_yearly = lax_yearly['total_tons'].min()
    avg_diff_pct = (max_yearly / min_yearly - 1) * 100
    st.metric("Total 18-Year Volume", f"{total_18yr_tons:,.0f} tons")
    st.metric("Avg. High-to-Low Difference", f"{avg_diff_pct:+.1f}%")
    st.caption(
        "Averaged across 18 years, the difference between the highest and lowest annual volumes "
        "shows the overall volatility in LAX air freight."
    )

st.divider()

# ── Port of LA comparison ────────────────────────────────────────────────────
st.subheader("Figure 2: Port of LA vs LAX Air Cargo — 2021 Supply Chain Surge")

port_la_2021 = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    'total_teus': [835516, 799315, 957599, 946966, 1012048, 876430, 890800, 954377, 903865, 902644, 811460, 786589],
    'total_tons': [212993, 200482, 254057, 241159, 249734, 238398, 240152, 236615, 234046, 249535, 245303, 249442]
})

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=port_la_2021['month'], y=port_la_2021['total_teus'],
                      name='Port of LA Containers (TEUs)', yaxis='y1', marker_color='steelblue', opacity=0.7))
fig2.add_trace(go.Scatter(x=port_la_2021['month'], y=port_la_2021['total_tons'],
                          name='LAX Air Cargo (tons)', yaxis='y2',
                          line=dict(color='red', width=3), marker=dict(size=8), mode='lines+markers'))
fig2.update_layout(
    yaxis=dict(title='Shipping Containers (TEUs)', side='left'),
    yaxis2=dict(title='LAX Air Cargo (tons)', side='right', overlaying='y'),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig2, use_container_width=True)
st.caption(
    "The blue bars show shipping containers handled by the Port of LA (measured in TEUs — twenty-foot equivalent units, "
    "the standard measure for container volume). The red line shows air cargo at LAX. In **March 2021**, the Port of LA "
    "handled 957,599 TEUs while LAX air cargo peaked at 254,057 tons. When ground shipping gets overwhelmed, "
    "companies switch to air — producing roughly 49x more carbon per ton-mile."
)
st.caption(
    "Port of LA data source: [Port of Los Angeles Container Statistics]"
    "(https://www.portoflosangeles.org/business/statistics/container-statistics). "
    "LAX data source: LAWA Open Data Portal."
)

st.divider()

# ── Summary ──────────────────────────────────────────────────────────────────
st.markdown("#### Summary")
st.markdown("""
**What the data shows across 18 years:**
- **2006–2009:** Freight dropped 21% during the 2008 financial crisis — companies shipped less of everything
- **2010–2019:** Gradual recovery with steady growth, reaching pre-crisis levels by 2015
- **2020–2021:** COVID disrupted ground supply chains, causing a massive surge in air freight (+31% from 2019 to 2021)
- **2022–2023:** Sharp correction as supply chains normalized, dropping 34% from the 2021 peak
""")

# ── CAPE connection ──────────────────────────────────────────────────────────
sales, carbon, _po, _inv, _fin = load_erpsim()
_period_map = build_period_map(sales)

cape_join = pd.merge(sales, carbon, on=['SIM_ROUND', 'SIM_STEP'], how='inner')
cape_summary = cape_join.groupby(['SIM_ROUND', 'SIM_STEP']).agg(
    total_co2e=('TOTAL_CO2E_EMISSIONS', 'sum'),
).reset_index()
cape_summary = add_period_labels(cape_summary, _period_map)

st.divider()
st.info(
    "📍 **Why CAPE matters to LAX:** CAPE's highest-risk time points (periods 24–28, during Phase 3 of the simulation) "
    "show the same pattern as 2020–2021 at LAX — supply chain stress forces a switch to high-carbon air freight. "
    "CAPE catches this at the order level, before the freight mode decision is made. "
    "This means CAPE could help airports like LAX and logistics operators anticipate carbon spikes "
    "and intervene before they happen."
)
st.caption("CAPE — Carbon-Aware Predictive Engine | AI-Driven Analytics Application | SAIES Research | Cal State LA · CIS | NSF Grant Project")
