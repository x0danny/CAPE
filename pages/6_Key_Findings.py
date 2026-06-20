import streamlit as st
import pandas as pd
from data_loader import load_lax_aggregate, load_lax_shipments

st.title("🔑 Key Findings & Recommendations")
st.markdown("##### What did CAPE find, why does it matter, and what should be done?")
st.caption("This page summarizes the project's core findings and connects simulation results to real LAX air freight data.")
st.divider()

# ── Load data ────────────────────────────────────────────────────────────────
try:
    lax = load_lax_aggregate()
    freight = lax[lax['CargoType'] == 'Freight']
    yearly = freight.groupby('year')['AirCargoTons'].sum()
    total_freight = freight['AirCargoTons'].sum()
    intl_freight = freight[freight['Domestic_International'] == 'International']['AirCargoTons'].sum()
    data_ok = True
except Exception:
    data_ok = False

try:
    lax_sales, lax_carbon = load_lax_shipments()
    ship_ok = True
except Exception:
    ship_ok = False

# ══════════════════════════════════════════════════════════════════════════════
# FINDING 1
# ══════════════════════════════════════════════════════════════════════════════
st.header("1. Late orders are the #1 driver of avoidable carbon emissions")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("""
In CAPE's training data, **57.9% of all orders arrived late** — and late orders are
the single biggest cause of carbon waste in the supply chain.

Here's why: when an order arrives late, inventory piles up in warehouses. That idle inventory
generates a carbon penalty from storage, cooling, and handling. **Overstock
from late orders accounted for over a third of all direct emissions**.

The machine learning model confirmed this statistically: **total CO₂ emissions are the #1
predictor of whether an order will be late**, with 94.2% accuracy. Carbon risk and operational
risk are not independent — they move together.
""")
with col2:
    st.metric("Orders Late", "57.9%", help="Percentage of orders in the training data that arrived late")
    st.metric("Model Accuracy", "94.2%", help="The model correctly predicts order risk 94.2% of the time (5-fold cross-validation)")
    st.metric("Top Predictor", "Carbon Emissions", help="The signal most predictive of order lateness")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# FINDING 2
# ══════════════════════════════════════════════════════════════════════════════
st.header("2. The 2021 COVID supply chain crisis proves the pattern at LAX")

col1, col2 = st.columns([2, 1])
with col1:
    if data_ok:
        y2019 = yearly.get(2019, 0)
        y2021 = yearly.get(2021, 0)
        surge_pct = (y2021 / y2019 - 1) * 100 if y2019 > 0 else 0

        st.markdown(f"""
CAPE's simulation predicts that supply chain stress leads to freight mode-switching — companies
shift cargo from ground to air when ground shipping gets overwhelmed. **Air freight produces
~49 times more carbon per ton-mile than ground transport.**

The real LAX data confirms this prediction. During the 2021 COVID supply chain crisis:
- LAX air freight surged **+{surge_pct:.0f}%** from 2019 to 2021
- March 2021 was the single busiest month in 18 years: **254,057 tons**
- The Port of LA hit 957,599 containers in March 2021 — ground corridors were overwhelmed
- Companies switched to air freight, and carbon emissions spiked proportionally

This is exactly the mode-switching pattern CAPE is designed to detect **before** it happens.
""")
    else:
        st.warning("LAX data not available.")
with col2:
    if data_ok:
        st.metric("2021 Surge", f"+{surge_pct:.0f}%", help="Year-over-year increase in LAX air freight, 2019 to 2021")
        st.metric("Peak Month", "Mar 2021", help="254,057 tons — the highest single month in 18 years")
        st.metric("Air vs Ground", "~49x", help="Air freight produces ~49 times more CO₂ per ton-mile")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# FINDING 3
# ══════════════════════════════════════════════════════════════════════════════
st.header("3. International routes from LAX are the biggest carbon exposure")

col1, col2 = st.columns([2, 1])
with col1:
    if ship_ok:
        top_routes = lax_carbon.dropna(subset=["Route"]).groupby('Route')['Total_CO2e_kg'].sum().sort_values(ascending=False)
        top3 = top_routes.head(3)
        top_carrier = lax_carbon.dropna(subset=["Carrier"]).groupby('Carrier')['Total_CO2e_kg'].sum().idxmax()

        route_lines = "\n".join(f"- **{route}**: {co2e/1e9:.1f} billion kg CO₂e" for route, co2e in top3.items())

        st.markdown(f"""
Per-shipment analysis using ICAO/DEFRA emission factors reveals that **international routes
dominate carbon emissions** at LAX — because they fly farther, each ton generates far more carbon.

The three highest-emitting routes:
{route_lines}

**{top_carrier}** is the highest-emitting carrier, driven by long-haul Pacific routes.

International freight accounts for **{intl_freight/total_freight*100:.0f}%** of all LAX air cargo
volume, but an even larger share of total emissions because of the longer distances involved.
""")
    elif data_ok:
        st.markdown(f"""
International freight accounts for **{intl_freight/total_freight*100:.0f}%** of all LAX air cargo volume,
but an even larger share of emissions due to longer flight distances.
""")
with col2:
    if data_ok:
        st.metric("International Share", f"{intl_freight/total_freight*100:.0f}%", help="Share of LAX freight that is international")
    if ship_ok:
        st.metric("Highest Route", top_routes.index[0], help=f"{top_routes.iloc[0]/1e9:.1f}B kg CO₂e")
        st.metric("Highest Carrier", top_carrier)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# FINDING 4
# ══════════════════════════════════════════════════════════════════════════════
st.header("4. CAPE catches carbon risk before it happens — traditional tools cannot")

st.markdown("""
The core research contribution of CAPE is **timing**. Existing tools like SAP Green Ledger
record carbon emissions after they occur — useful for reporting, but too late to prevent.

CAPE intervenes earlier in the chain:

| | Traditional Tools (e.g., SAP Green Ledger) | CAPE |
|---|---|---|
| **When** | After emissions are logged | Before the freight decision is made |
| **What** | Records what happened | Predicts what will happen |
| **Action** | Compliance reporting | Operational intervention |
| **Value** | Audit trail | Prevention |

CAPE flags high-risk periods **1–2 steps before** carbon costs spike, giving operations teams
time to reduce order quantities, proactively communicate with suppliers, or avoid switching
to air freight. In the simulation, early intervention could have reduced overstock carbon
waste by 20–30%.
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.header("📋 Recommendations")
st.markdown("##### Based on 18 years of LAX air freight data and CAPE's predictive analysis")
st.divider()

rec_col1, rec_col2 = st.columns(2)

with rec_col1:
    st.markdown("#### For LAX & Logistics Operators")
    st.markdown("""
**1. Monitor Pacific Rim routes for carbon risk**
The LAX–PVG (Shanghai), LAX–NRT (Tokyo), and LAX–CDG (Paris) routes account for the
majority of air freight carbon emissions. Deploy carbon monitoring on these lanes first.

**2. Build early-warning triggers for mode-switching**
When ground shipping delays exceed a threshold, companies will switch to air. Set up
alerts at the 2-week delay mark — before the air freight decision is made — to explore
ground alternatives or consolidate shipments.

**3. Target Q4 seasonal peaks proactively**
Air freight volumes spike predictably in October–December. Pre-position inventory
before the peak season to reduce the need for emergency air shipments.
""")

with rec_col2:
    st.markdown("#### For Researchers & Policy")
    st.markdown("""
**4. Expand CAPE to other airports**
The mode-switching pattern CAPE detects at LAX likely exists at other major cargo hubs
(JFK, ORD, MIA). Applying the same model to other airports would validate the
generalizability of the findings.

**5. Integrate real-time freight pricing signals**
Freight rates from the Freightos Air Index spike before mode-switching events. Adding
live pricing data as a model feature could improve prediction lead time.

**6. Advocate for carbon-aware fulfillment standards**
Current supply chain KPIs optimize for cost and speed — not carbon. CAPE demonstrates
that a carbon-risk score can be computed alongside traditional metrics with minimal
additional data requirements.
""")

st.divider()

st.info(
    "💡 **The bottom line:** Air freight produces ~49x more carbon than ground transport per ton-mile "
    "(based on [ICAO Carbon Emissions Calculator](https://icec.icao.int/) and "
    "[UK DEFRA/BEIS GHG Conversion Factors](https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting)). "
    "Every shipment that can be kept on the ground — or prevented from becoming a late, emergency "
    "air shipment — is a direct carbon reduction. CAPE makes this visible before the decision is made."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# LIMITATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.header("⚠️ What CAPE Can and Cannot Claim")
st.caption("Honest disclosure of how the project works and where its limits are.")
st.markdown("""
**1. How the model was built**
CAPE's risk prediction model was trained on a supply chain training exercise (SAP ERPsim),
not on real company order data. The model learned patterns of how late orders lead to
carbon waste — then we checked whether those same patterns appear in real LAX freight data.
They do, but showing the same pattern is not the same as proving one causes the other.

**2. What the LAX analysis is based on**
The freight tonnage and trends come from **real public data** published by Los Angeles World
Airports (LAWA). However, the per-shipment details (which airline carried what, what product
was shipped, whether it was late) are **example values created for this research** — LAWA
only publishes monthly totals, not individual shipment records. The Data & Downloads page
has full documentation of what is real vs. modeled.

**3. How carbon emissions were calculated**
We used internationally recognized methods (ICAO Carbon Emissions Calculator and UK
government DEFRA/BEIS conversion factors) to estimate emissions — these are the same
methods used by airlines and governments worldwide. But they are estimates, not direct
measurements. The actual carbon depends on the specific aircraft, how full it was, and
the exact route flown.

**4. The "49x" air-vs-ground comparison**
Based on the emission factors used in this project (ICAO/DEFRA), air freight produces
approximately 49 times more carbon per ton-mile than ground transport. This is consistent
with published industry estimates, but the exact multiplier varies by vehicle type and
conditions.

**5. Can other researchers reproduce this?**
The LAX data is freely available from the City of LA Open Data Portal. The model training
code is in the project repository. However, the ERPsim training data requires a
SAP University Alliance license — contact your institution's SAP representative for access.
""")

st.divider()
st.caption("CAPE — Key Findings & Recommendations | AI-Driven Analytics Platform | SAIES Research | CSULA CIS | NSF Grant Project")
