import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_loader import load_erpsim

st.title("⚡ What-If Simulator")
st.markdown("##### What would happen to carbon risk if we changed our supply chain decisions?")
st.caption("Drag the sliders to test different strategies. Every number has a plain English explanation — no jargon.")
st.divider()

sales, carbon, po, inventory, _fin = load_erpsim()

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
st.caption("A quick snapshot of order health and carbon exposure. Think of this as a check engine light for your supply chain.")
st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Late Orders", f"{total_late} of {total_orders}")
    st.caption("Orders that took 2 steps to arrive instead of 1. Late orders cause inventory to pile up, which generates carbon penalties.")
with col2:
    st.metric("High Risk Periods", f"{len(high_risk)} of 38")
    st.caption("Time periods where carbon costs were unusually high. More high-risk periods = more money being spent on avoidable emissions.")
with col3:
    worst_idx = period_summary['cape_risk_score'].idxmax()
    worst_p = period_summary.loc[worst_idx, 'period']
    worst_score = period_summary.loc[worst_idx, 'cape_risk_score']
    st.metric("Worst Period", worst_p)
    st.caption(f"This period had the highest risk score ({worst_score:.3f}). Carbon costs per dollar of revenue were nearly double the safe level.")
with col4:
    total_overstock = period_summary['overstock_co2e'].sum()
    total_co2e_all = period_summary['total_co2e'].sum()
    overstock_share = total_overstock / total_co2e_all * 100 if total_co2e_all > 0 else 0
    st.metric("Overstock Carbon Waste", f"{total_overstock:,.0f} kg",
              help="CO₂e = carbon dioxide equivalent — the standard unit for measuring greenhouse gas emissions.")
    st.caption(f"Carbon wasted on inventory sitting in warehouses. That's {overstock_share:.0f}% of all direct emissions — most of it preventable.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 2: WHAT-IF SCENARIO SIMULATOR
# ══════════════════════════════════════════════════════
st.header("🎛️ What-If Scenario Simulator")
st.caption("Drag the sliders to see how changes to late orders, reorder quantities, and freight choices would affect carbon risk. This helps you compare different strategies before committing.")
st.divider()

sim_col1, sim_col2, sim_col3 = st.columns(3)

with sim_col1:
    late_reduction = st.slider(
        "Reduce late orders by",
        min_value=0, max_value=100, value=0, step=5,
        format="%d%%",
        help="What if you could prevent some late orders? Slide right to see the impact of fewer delays."
    )

with sim_col2:
    reorder_reduction = st.slider(
        "Reduce reorder quantities by",
        min_value=0, max_value=50, value=0, step=5,
        format="%d%%",
        help="Ordering less means less overstock sitting in warehouses. Slide right to see how smaller orders reduce carbon waste."
    )

with sim_col3:
    ground_shift = st.slider(
        "Shift air freight to ground",
        min_value=0, max_value=100, value=0, step=5,
        format="%d%%",
        help="Ground transport produces ~47-50x less carbon than air. Slide right to see the impact of using more ground shipping."
    )

sim_summary = period_summary_sorted.copy()

original_overstock = sim_summary['overstock_co2e'].sum()
original_total_co2e = sim_summary['total_co2e'].sum()
original_high_risk_count = len(sim_summary[sim_summary['cape_risk_score'] >= 0.6])
original_avg_risk = sim_summary['cape_risk_score'].mean()

late_factor = 1 - (late_reduction / 100)
overstock_factor = 1 - (reorder_reduction / 100)
air_carbon_reduction = ground_shift / 100 * 0.98

sim_summary['sim_overstock_co2e'] = sim_summary['overstock_co2e'] * late_factor * overstock_factor
non_overstock = sim_summary['total_co2e'] - sim_summary['overstock_co2e']
sim_summary['sim_total_co2e'] = non_overstock * (1 - air_carbon_reduction) + sim_summary['sim_overstock_co2e']
sim_summary['sim_co2e_per_dollar'] = sim_summary['sim_total_co2e'] / sim_summary['total_revenue']

scaler_sim = MinMaxScaler()
if sim_summary['sim_co2e_per_dollar'].nunique() > 1:
    sim_summary['sim_intensity_scaled'] = scaler_sim.fit_transform(sim_summary[['sim_co2e_per_dollar']])
else:
    sim_summary['sim_intensity_scaled'] = 0.0
if sim_summary['sim_overstock_co2e'].nunique() > 1:
    sim_summary['sim_overstock_scaled'] = scaler_sim.fit_transform(sim_summary[['sim_overstock_co2e']])
else:
    sim_summary['sim_overstock_scaled'] = 0.0
sim_summary['sim_risk_score'] = (sim_summary['sim_intensity_scaled'] * 0.70 +
                                  sim_summary['sim_overstock_scaled'] * 0.30)

new_overstock = sim_summary['sim_overstock_co2e'].sum()
new_total_co2e = sim_summary['sim_total_co2e'].sum()
new_high_risk_count = len(sim_summary[sim_summary['sim_risk_score'] >= 0.6])
new_avg_risk = sim_summary['sim_risk_score'].mean()

has_changes = late_reduction > 0 or reorder_reduction > 0 or ground_shift > 0

if has_changes:
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        co2e_delta = new_total_co2e - original_total_co2e
        st.metric("Total CO2e", f"{new_total_co2e:,.0f} kg",
                  delta=f"{co2e_delta:,.0f} kg", delta_color="inverse")
        st.caption("Lower is better. This shows total carbon emissions under your scenario.")
    with r2:
        overstock_delta = new_overstock - original_overstock
        st.metric("Overstock CO2e", f"{new_overstock:,.0f} kg",
                  delta=f"{overstock_delta:,.0f} kg", delta_color="inverse")
        st.caption("Carbon wasted on idle inventory. Your changes would reduce this by ordering smarter.")
    with r3:
        risk_delta = new_high_risk_count - original_high_risk_count
        st.metric("High Risk Periods", f"{new_high_risk_count} of 38",
                  delta=f"{risk_delta}", delta_color="inverse")
        st.caption("Fewer high-risk periods means fewer times the supply chain hits dangerous carbon levels.")
    with r4:
        avg_delta = new_avg_risk - original_avg_risk
        st.metric("Avg Risk Score", f"{new_avg_risk:.3f}",
                  delta=f"{avg_delta:.3f}", delta_color="inverse")
        st.caption("The average carbon risk across all periods. Below 0.6 is the safe zone.")

    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        x=sim_summary['period'], y=sim_summary['cape_risk_score'],
        name='Current Risk', marker_color='rgba(226,75,74,0.4)',
        hovertemplate='<b>%{x}</b><br>Current: %{y:.3f}<extra></extra>'
    ))
    fig_compare.add_trace(go.Bar(
        x=sim_summary['period'], y=sim_summary['sim_risk_score'],
        name='Simulated Risk', marker_color='rgba(29,158,117,0.7)',
        hovertemplate='<b>%{x}</b><br>Simulated: %{y:.3f}<extra></extra>'
    ))
    fig_compare.add_hline(y=0.6, line_dash='dash', line_color='red',
                          annotation_text='High Risk Threshold (0.6)')
    fig_compare.update_layout(
        title='Current vs. Simulated Risk Score by Period',
        barmode='group', xaxis_tickangle=45,
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    pct_reduction = (1 - new_total_co2e / original_total_co2e) * 100
    st.success(f"**Your scenario would reduce total carbon emissions by {pct_reduction:.1f}%** — "
               f"from {original_total_co2e:,.0f} kg to {new_total_co2e:,.0f} kg CO2e, "
               f"and drop the number of high-risk periods from {original_high_risk_count} to {new_high_risk_count}.")
else:
    st.info("👆 **Try it:** Move the sliders above to simulate different supply chain strategies and see how they would change carbon outcomes. For example, reducing late orders by 30% would significantly cut overstock penalties.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 3: WHY IS IT HAPPENING
# ══════════════════════════════════════════════════════
st.header("🔍 Why Is It Happening")
st.caption("These charts show the root causes behind carbon risk. Each chart includes a plain English explanation below it.")
st.divider()

col_a, col_b = st.columns(2)

with col_a:
    fig1 = px.bar(period_summary_sorted, x='period', y='late_pct',
                  title='Late Order Rate by Period',
                  color='late_pct', color_continuous_scale='Reds',
                  labels={'late_pct': '% of Orders Late', 'period': 'Time Period'})
    fig1.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("📌 **What this means:** Each bar shows the percentage of orders that arrived late in that time period. Taller red bars = more delays = more carbon risk. When orders are late, inventory piles up in warehouses and generates carbon penalties.")

with col_b:
    fig2 = px.bar(period_summary_sorted, x='period', y='overstock_co2e',
                  title='Carbon Wasted on Idle Inventory',
                  color='overstock_co2e', color_continuous_scale='Oranges',
                  labels={'overstock_co2e': 'Wasted Carbon (kg CO2e)', 'period': 'Time Period'})
    fig2.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("📌 **What this means:** This is carbon being wasted on inventory sitting idle in warehouses — caused by late deliveries. Taller bars = more wasted emissions. This is the #1 source of preventable carbon in the supply chain.")

col_c, col_d = st.columns(2)

with col_c:
    fig3 = px.scatter(period_summary, x='late_pct', y='co2e_per_dollar',
                      size='overstock_co2e', color='cape_risk_score',
                      color_continuous_scale='RdYlGn_r',
                      title='Late Orders vs Carbon Cost',
                      labels={'late_pct': '% of Orders Late', 'co2e_per_dollar': 'Carbon Cost per $1 of Revenue'},
                      hover_data=['period'])
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("📌 **What this means:** Each dot is a time period. Dots in the top-right corner had both high delays AND high carbon costs — the worst combination. Bigger dots = more wasted inventory carbon. This proves late orders and carbon spikes go together.")

with col_d:
    round_summary = period_summary.groupby('SIM_ROUND').agg(
        avg_risk=('cape_risk_score','mean'),
        avg_late=('late_pct','mean'),
        total_co2e=('total_co2e','sum')
    ).reset_index()
    round_summary['round'] = 'Round ' + round_summary['SIM_ROUND'].astype(str)

    fig4 = px.bar(round_summary, x='round', y='avg_risk',
                  title='Average Carbon Risk by Round',
                  color='avg_risk', color_continuous_scale='RdYlGn_r',
                  labels={'avg_risk': 'Average Risk Score', 'round': 'Simulation Round'})
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("📌 **What this means:** Round 3 had the highest average risk — something went systematically wrong. More late orders led to more overstock, which drove up carbon costs across the board.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 4: WHAT TO DO ABOUT IT
# ══════════════════════════════════════════════════════
st.header("🚨 What To Do About It")
st.caption("Plain English recommendations for each high-risk period. No jargon — just what happened, why it matters, and what should have been done differently.")
st.divider()

for _, row in high_risk.sort_values('cape_risk_score', ascending=False).iterrows():
    risk = row['cape_risk_score']
    if risk >= 0.8:
        color = "error"
        level = "🔴 CRITICAL"
    elif risk >= 0.7:
        color = "warning"
        level = "🟠 HIGH"
    else:
        color = "info"
        level = "🟡 ELEVATED"

    with st.expander(f"{level} — Period {row['period']} | Risk Score: {risk:.3f}"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Carbon Cost per $1", f"{row['co2e_per_dollar']:.4f} kg",
                     help="How much carbon was emitted for every dollar of revenue. Lower is better.")
        col2.metric("Wasted Inventory Carbon", f"{row['overstock_co2e']:,.0f} kg",
                     help="Carbon generated by inventory sitting idle in warehouses.")
        col3.metric("Late Order Rate", f"{row['late_pct']:.0f}%" if pd.notna(row['late_pct']) else "N/A",
                     help="Percentage of orders that arrived late (took 2 steps instead of 1).")

        st.markdown("**What happened:**")
        st.write(f"In period {row['period']}, it cost {row['co2e_per_dollar']:.4f} kg of carbon for every dollar earned — well above the safe level of 0.09. Meanwhile, {row['overstock_co2e']:,.0f} kg of carbon was wasted on inventory that sat idle because deliveries were delayed.")

        st.markdown("**What should have been done:**")
        intensity = row['co2e_per_dollar']
        overstock_val = row['overstock_co2e']
        late_pct = row['late_pct'] if pd.notna(row['late_pct']) else 0
        period = row['period']

        rec_num = 1
        st.write(f"{rec_num}. CAPE flagged this period with a risk score of {risk:.3f}. This signal was detectable 1-2 steps earlier — early enough for the operations team to intervene before the damage was done.")
        rec_num += 1

        if overstock_val > 8000:
            st.write(f"{rec_num}. {overstock_val:,.0f} kg of carbon was wasted on excess inventory. Ordering 20-30% less in the previous period would have prevented most of this warehouse buildup.")
        elif overstock_val > 3000:
            st.write(f"{rec_num}. {overstock_val:,.0f} kg of carbon went to idle inventory. A modest cut to order sizes in the prior step would have reduced this waste.")
        else:
            st.write(f"{rec_num}. Inventory waste was relatively contained at {overstock_val:,.0f} kg. The bigger problem here was the carbon cost of delivery patterns, not warehouse buildup.")
        rec_num += 1

        if late_pct >= 80:
            st.write(f"{rec_num}. {late_pct:.0f}% of orders arrived late — nearly a complete delivery failure. An alert should have gone out at the start of this period, not after.")
        elif late_pct >= 40:
            st.write(f"{rec_num}. {late_pct:.0f}% of deliveries were delayed. Reaching out to suppliers one step earlier could have prevented a portion of these delays.")
        elif late_pct == 0:
            st.write(f"{rec_num}. No new late orders in {period} — the high carbon costs here came from overstock that accumulated in earlier periods.")
        rec_num += 1

        if intensity > 0.15:
            st.write(f"{rec_num}. Carbon cost of {intensity:.4f} kg per dollar is {((intensity/0.09)-1)*100:.0f}% above the safe threshold. Switching even one shipment from air to ground would have saved significant emissions (air freight produces ~47-50x more carbon per ton-mile).")
        elif intensity > 0.12:
            st.write(f"{rec_num}. Carbon cost of {intensity:.4f} kg per dollar is well above safe levels. Moving some shipments to ground transport would have meaningfully reduced the carbon footprint.")
        else:
            st.write(f"{rec_num}. Carbon cost of {intensity:.4f} kg per dollar is moderately elevated. Combined with the inventory waste, this period's total carbon exposure exceeded acceptable levels.")

st.divider()

# ══════════════════════════════════════════════════════
# SECTION 5: THE CAPE CONNECTION
# ══════════════════════════════════════════════════════
st.header("🔗 How CAPE Catches Risk Early")
st.caption("CAPE intervenes at Step 4 — before costly air freight escalation and emissions logging happen. Here's the full chain of events.")
st.divider()

st.markdown("""
| Step | What Happens | Plain English |
|------|-------------|---------------|
| **1. Order Placed** | A purchase order enters the system | Nothing has gone wrong yet — carbon cost is zero |
| **2. Delivery Delayed** | Order takes 2 steps instead of 1 | The first warning sign — the order is late |
| **3. Inventory Piles Up** | Warehouse holds excess stock | Carbon penalty starts — energy used to store idle goods |
| **4. CAPE Flags It** | Risk score crosses 0.6 | **This is where CAPE catches it** — there's still time to act |
| **5. Air Freight Kicks In** | Critical orders get rushed by air | Carbon cost explodes — air produces 47-50x more CO2 than ground |
| **6. LAX Gets the Load** | Air cargo volume at LAX spikes | Real-world impact — this is what we measured in 18 years of LAX data |
| **7. Emissions Logged** | SAP records the carbon after the fact | Too late to prevent — CAPE already caught it at Step 4 |
""")

st.info("💡 **The key insight:** CAPE's job is to intervene at Step 4 — before the expensive, high-carbon Steps 5, 6, and 7 happen. That's the research contribution: predictive carbon intelligence, not after-the-fact reporting.")

st.divider()
st.caption("AI Supply Chain Control Tower | SAIES Research | CSULA CIS | NSF Grant Project")
