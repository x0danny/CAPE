import streamlit as st

st.set_page_config(page_title="CAPE Platform", page_icon="🌿", layout="wide")

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**Predictive Analytics on Carbon-Awareness of LAX Logistics**")
st.markdown("Dr. Ming Wang · Brian Ta · Daniel Ramirez | CSULA CIS | SAIES Research | NSF Grant Project")
st.divider()

st.markdown("""
CAPE is a predictive carbon intelligence platform built on SAP ERPsim simulation data.
Most enterprise carbon tools tell you what you already emitted — like a bill after you spent the money.
**CAPE tells you what you are about to emit before the decision is made.**

Using a Random Forest model trained on ERPsim order and emissions data, CAPE achieves **94.2% cross-validation accuracy**
predicting which fulfillment periods will generate elevated carbon exposure.
The key finding: **total CO2e emissions are the #1 predictor of order lateness** — carbon and operational risk are statistically linked.

The platform is validated against **20 years of LAX air freight data** and **Port of LA container volume** from the 2021 supply chain surge,
grounding the simulation findings in the real-world logistics corridor most relevant to this research.
""")

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.success("""### 🌿 CAPE Carbon
Carbon risk scores and overstock penalties across 38 simulation periods.
Validated against 20 years of LAX air freight data.
**Start here.**""")
with col2:
    st.info("""### ⚡ Control Tower
Period-by-period breakdown of what drove carbon risk, why it happened,
and what should have been done differently.
Plain English — no jargon.""")
with col3:
    st.warning("""### 📊 Sales & Carbon Intelligence
Which products and regions generate the most revenue per kg of CO2e.
Revenue growth and carbon risk do not move together — this page shows why.""")

st.divider()

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Total CO2e Analyzed", "421,694 kg")
    st.caption("Across 38 simulation periods, Scopes 1, 2, and 3")
with col_b:
    st.metric("ML Model Accuracy", "94.2% ±3.3%")
    st.caption("Random Forest, 5-fold cross-validation on ERPsim data")
with col_c:
    st.metric("LAX Freight Data", "20 Years")
    st.caption("2006–2023 monthly air cargo tonnage, City of LA Open Data")

st.divider()
st.caption("Use the sidebar to navigate between modules | cape-dashboard.streamlit.app | github.com/x0danny/CAPE")